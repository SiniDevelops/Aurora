"""
Aurora Backend — FastAPI Application Entry Point

Initializes all services on startup and tears them down on shutdown.
Mounts API routes and WebSocket handlers.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_config
from utils.logger import get_logger, setup_logger

logger = get_logger("aurora.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan — startup and shutdown events.
    
    Startup:
        1. Load configuration
        2. Initialize data stores (SQLite, ChromaDB)
        3. Initialize vault manager and index vault
        4. Initialize privacy sanitizer
        5. Initialize LLM client and embedding manager
        6. Initialize skill registry and router
        7. Initialize orchestrator
        8. Start vault file watcher (if enabled)
    
    Shutdown:
        1. Stop file watcher
        2. Close database connections
        3. Cleanup resources
    """
    config = get_config()
    
    # Setup logging
    log_file = Path(config.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    setup_logger("aurora", str(log_file), config.log_level)
    
    logger.info(f"Starting {config.app_name} v{config.app_version}")
    logger.info(f"Debug mode: {config.debug}")
    logger.info(f"LLM Provider: {config.llm_active_provider}")
    
    # ─── Initialize Data Stores ──────────────────────
    from data.sqlite_store import SQLiteStore
    from data.chroma_store import ChromaStore
    
    # Ensure data directories exist
    Path(config.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    Path(config.chroma_path).mkdir(parents=True, exist_ok=True)
    
    sqlite_store = SQLiteStore(config.sqlite_path)
    await sqlite_store.initialize()
    logger.info("SQLite store initialized")
    
    chroma_store = ChromaStore(config.chroma_path, config.chroma_collection)
    chroma_store.initialize()
    logger.info("ChromaDB store initialized")
    
    # ─── Initialize AI Layer ─────────────────────────
    from ai.llm_client import LLMClient
    from ai.embeddings import EmbeddingManager
    
    llm_client = LLMClient(config.raw.get("llm", {}))
    logger.info(f"LLM client initialized (provider: {config.llm_active_provider})")
    
    embedding_manager = EmbeddingManager(config.raw.get("llm", {}).get("embedding", {}))
    logger.info("Embedding manager initialized")
    
    # ─── Initialize Core Services ────────────────────
    from core.vault_manager import VaultManager
    from core.privacy_sanitizer import PrivacySanitizer, PrivacyConfig as SanitizerConfig
    from core.session_manager import SessionManager
    from core.context_builder import ContextBuilder
    
    vault_manager = VaultManager(
        vault_path=config.vault_path,
        excluded_folders=config.vault_excluded_folders,
        supported_extensions=config.vault_supported_extensions,
    )
    
    # Index vault on startup if configured
    if config.vault_index_on_startup:
        try:
            await vault_manager.initialize()
            logger.info(f"Vault indexed: {config.vault_path}")
        except Exception as e:
            logger.warning(f"Vault indexing failed (vault may not exist yet): {e}")
    
    # ─── Initialize Knowledge Graph ─────────────────
    from core.link_resolver import LinkResolver
    from core.backlink_index import BacklinkIndex
    from core.vault_graph import VaultGraph
    
    link_resolver = LinkResolver(vault_manager.notes_cache)
    backlink_index = BacklinkIndex()
    backlink_index.rebuild_index(vault_manager.notes_cache)
    vault_graph = VaultGraph()
    vault_graph.build_graph(vault_manager.notes_cache, backlink_index)
    logger.info(f"Knowledge graph built: {len(vault_graph.nodes)} nodes, {len(vault_graph.directed_edges)} edges")
    
    # ─── Incremental Chunk Index ─────────────────────
    from core.indexer import VaultIndexer
    
    indexer = VaultIndexer(
        vault_manager,
        chroma_store=chroma_store,
        embedding_manager=embedding_manager,
        state_path=str(Path(config.chroma_path).parent / "index_state.json"),
    )
    try:
        idx_stats = await indexer.full_sync()
        logger.info(
            f"Chunk index: {idx_stats['chunks']} sections from {idx_stats['notes']} notes"
            + (
                f" | embedded {idx_stats['embedded']}, unchanged {idx_stats['unchanged']}, "
                f"removed {idx_stats['removed']}"
                if indexer.embeddings_available
                else " | semantic search off (no embedding provider)"
            )
        )
    except Exception as e:
        logger.error(f"Chunk indexing failed: {e}")
    
    # Privacy sanitizer — use the sanitizer's own config class
    privacy_cfg = config.privacy_config
    sanitizer_config = SanitizerConfig(
        enabled_categories=[
            c.upper() for c in privacy_cfg.get("enabled_categories", [])
        ],
        rules=privacy_cfg.get("content_rules", []),
    )
    sanitizer = PrivacySanitizer(sanitizer_config)
    logger.info("Privacy sanitizer initialized")
    
    session_manager = SessionManager(sqlite_store)
    context_builder = ContextBuilder(
        vault_manager,
        chroma_store,
        embedding_manager,
        indexer=indexer,
        graph_getter=lambda: getattr(app.state, "vault_graph", None),
    )
    
    # ─── Initialize Skills ───────────────────────────
    from skills.registry import SkillRegistry
    from skills.router import SkillRouter
    
    skill_registry = SkillRegistry(config.skills_config)
    await skill_registry.initialize(vault_manager, llm_client, logger)
    logger.info(f"Skills loaded: {[s.metadata.id for s in skill_registry.get_enabled_skills()]}")
    
    skill_router = SkillRouter(skill_registry, llm_client, config.skills_router_config)
    
    # ─── Initialize Orchestrator ─────────────────────
    from ai.orchestrator import AuroraOrchestrator
    
    orchestrator = AuroraOrchestrator(
        sanitizer=sanitizer,
        context_builder=context_builder,
        skill_registry=skill_registry,
        skill_router=skill_router,
        llm_client=llm_client,
    )
    logger.info("Orchestrator initialized")
    
    # ─── Start File Watcher ──────────────────────────
    watcher = None
    if config.vault_watch_changes:
        from utils.file_watcher import VaultWatcher
        
        async def on_vault_change(event):
            """Handle vault file changes — re-index the note and rebuild the graph."""
            import os as _os
            # Watchdog gives absolute OS paths; notes_cache is keyed by
            # vault-relative forward-slash paths (e.g. "Inbox/My Note.md")
            try:
                rel_path = _os.path.relpath(event.path, config.vault_path).replace("\\", "/")
            except ValueError:
                return  # different drive / outside vault
            if rel_path.startswith(".."):
                return

            logger.info(f"Vault change detected: {event.event_type} {rel_path}")
            try:
                if event.event_type == "deleted":
                    vault_manager.notes_cache.pop(rel_path, None)
                    changed = indexer.remove_note(rel_path)
                else:
                    await vault_manager.refresh_note(rel_path)
                    changed = await indexer.index_note(rel_path)
            except FileNotFoundError:
                vault_manager.notes_cache.pop(rel_path, None)
                changed = indexer.remove_note(rel_path)
            except Exception as e:
                logger.error(f"Failed to refresh note {rel_path}: {e}")
                return

            if not changed:
                # Duplicate watcher event or a save with identical content
                logger.debug(f"No content change in {rel_path}; skipping rebuild")
                return

            # Rebuild link structures so graph/backlinks/orphans stay current
            try:
                new_backlinks = BacklinkIndex()
                new_backlinks.rebuild_index(vault_manager.notes_cache)
                new_graph = VaultGraph()
                new_graph.build_graph(vault_manager.notes_cache, new_backlinks)
                app.state.backlink_index = new_backlinks
                app.state.vault_graph = new_graph
            except Exception as e:
                logger.error(f"Failed to rebuild knowledge graph: {e}")
        
        try:
            watcher = VaultWatcher(config.vault_path, on_vault_change)
            watcher.start()
            logger.info("Vault file watcher started")
        except Exception as e:
            logger.warning(f"File watcher failed to start: {e}")
    
    # ─── Store services on app state ─────────────────
    app.state.config = config
    app.state.sqlite_store = sqlite_store
    app.state.chroma_store = chroma_store
    app.state.llm_client = llm_client
    app.state.embedding_manager = embedding_manager
    app.state.vault_manager = vault_manager
    app.state.sanitizer = sanitizer
    app.state.session_manager = session_manager
    app.state.context_builder = context_builder
    app.state.skill_registry = skill_registry
    app.state.skill_router = skill_router
    app.state.orchestrator = orchestrator
    app.state.watcher = watcher
    app.state.link_resolver = link_resolver
    app.state.backlink_index = backlink_index
    app.state.vault_graph = vault_graph
    app.state.indexer = indexer
    
    logger.info(f"{config.app_name} is ready! Listening on {config.host}:{config.port}")
    
    yield  # ─── App is running ───
    
    # ─── Shutdown ────────────────────────────────────
    logger.info("Shutting down Aurora...")
    
    if watcher:
        watcher.stop()
        logger.info("File watcher stopped")
    
    logger.info("Aurora shutdown complete")


# ─── Create FastAPI App ──────────────────────────────

app = FastAPI(
    title="Aurora API",
    description="AI-Powered Obsidian Assistant — Privacy-first knowledge management",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS Middleware ─────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Mount API Routes ───────────────────────────────

from api.routes.chat import router as chat_router
from api.routes.vault import router as vault_router
from api.routes.settings import router as settings_router
from api.routes.dashboard import router as dashboard_router

app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(vault_router, prefix="/api/vault", tags=["Vault"])
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

# ─── WebSocket ───────────────────────────────────────

from api.websocket.chat_ws import router as ws_router
app.include_router(ws_router, tags=["WebSocket"])

# ─── Health Check ────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "aurora"}


@app.get("/api/ready", tags=["System"])
async def readiness_check():
    """Readiness probe — checks all services are initialized."""
    checks = {
        "config": app.state.config is not None,
        "sqlite": app.state.sqlite_store is not None,
        "chroma": app.state.chroma_store is not None,
        "llm": app.state.llm_client is not None,
        "vault": app.state.vault_manager is not None,
        "sanitizer": app.state.sanitizer is not None,
        "orchestrator": app.state.orchestrator is not None,
    }
    all_ready = all(checks.values())
    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
    }
