# Aurora — Task Tracker
> **Last updated**: 2026-08-28  
> **Status**: Phase 1 — Code created, verification in progress
> **Files created**: 80

---

## Phase 1 — Foundation & Privacy-First MVP

### 1.1 Project Scaffolding & Configuration
- [x] Create root `aurora.yaml` master configuration file
- [x] Create `.env.example` with all required environment variables
- [x] Create `.gitignore` (Python, Node.js, `.env`, `data/`, `logs/`)
- [x] Create root `README.md` with project overview and setup instructions

### 1.2 Backend — Project Setup
- [x] Initialize `aurora-backend/` directory structure
- [x] Create `requirements.txt` with all Python dependencies
- [x] Create `pyproject.toml` with project metadata
- [x] Create `main.py` — FastAPI app with lifespan events (startup/shutdown)
- [x] Create `config.py` — YAML config loader with `${ENV_VAR}` interpolation
- [ ] Verify: `uvicorn main:app` starts successfully on port 8000

### 1.3 Backend — Data Layer
- [x] Create `data/models.py` — All Pydantic models
- [x] Create `data/sqlite_store.py` — SQLite operations
- [x] Create `data/chroma_store.py` — ChromaDB wrapper
- [x] Create `data/migrations/001_initial.py` — Initial database schema
- [ ] Verify: SQLite database creates on first run
- [ ] Verify: ChromaDB collection initializes

### 1.4 Backend — Utilities
- [x] Create `utils/markdown_parser.py` — Parse Obsidian markdown
- [x] Create `utils/file_watcher.py` — Watchdog-based vault watcher
- [x] Create `utils/logger.py` — Structured JSON logging
- [x] Create `utils/validators.py` — Input validation helpers
- [ ] Write unit tests for `markdown_parser.py`

### 1.5 Backend — Core Services
- [x] Create `core/vault_manager.py` — Vault file operations
- [x] Create `core/session_manager.py` — Chat session handling
- [x] Create `core/context_builder.py` — Context assembly
- [x] Create `core/privacy_sanitizer.py` — Full PII pipeline (regex + spaCy NER + content filter + tokenizer + de-tokenizer + audit)
- [ ] Write unit tests for privacy sanitizer — 50+ test cases

### 1.6 Backend — AI Layer (LLM Adapters)
- [x] Create `ai/adapters/base.py` — Abstract `LLMAdapter` interface
- [x] Create `ai/adapters/openai_adapter.py` — OpenAI implementation
- [x] Create `ai/adapters/gemini_adapter.py` — Google Gemini implementation
- [x] Create `ai/adapters/claude_adapter.py` — Anthropic Claude implementation
- [x] Create `ai/adapters/ollama_adapter.py` — Local Ollama implementation
- [x] Create `ai/llm_client.py` — Provider-agnostic client
- [x] Create `ai/embeddings.py` — Embedding generation with caching
- [ ] Verify: Swap `active_provider` in YAML, confirm correct adapter loads
- [ ] Write unit tests for adapter loading

### 1.7 Backend — AI Orchestration (LangGraph)
- [x] Create `ai/orchestrator.py` — LangGraph state machine (sanitize → context → route → execute → format)
- [x] Create `ai/prompts/system.py` — System prompts
- [x] Create `ai/prompts/templates.py` — Prompt templates
- [x] Create `ai/prompts/skill_prompts.py` — Per-skill prompts
- [ ] Verify: Full pipeline works end-to-end

### 1.8 Backend — Skills System
- [x] Create `skills/base_skill.py` — Abstract `BaseSkill`
- [x] Create `skills/registry.py` — Skill registry with YAML-driven loading
- [x] Create `skills/router.py` — Multi-stage skill routing
- [x] Create `skills/builtin/note_creator.py` — Note Creator skill
- [x] Create `skills/builtin/note_finder.py` — Note Finder skill
- [x] Create `skills/builtin/summarizer.py` — Summarizer skill
- [x] Create `skills/custom/README.md` — Custom skill guide
- [ ] Write integration tests for skill routing

### 1.9 Backend — API Routes
- [x] Create `api/routes/chat.py` — Chat endpoints (POST /message, GET /history, DELETE /session, GET /sessions)
- [x] Create `api/routes/vault.py` — Vault endpoints (tree, note CRUD, search, reindex, stats)
- [x] Create `api/routes/settings.py` — Settings endpoints
- [x] Create `api/websocket/chat_ws.py` — WebSocket handler for streaming
- [x] Create `api/middleware/cors.py` — CORS configuration
- [x] Create `api/middleware/rate_limit.py` — Rate limiter
- [ ] Verify: All endpoints return correct status codes

### 1.10 Frontend — Project Setup
- [x] Initialize Next.js 14+ project with App Router and TypeScript
- [x] Configure `next.config.js` (API proxy to backend)
- [x] Create CSS design system (`app/globals.css` — design tokens for light/dark)
- [x] Create `lib/types.ts` — TypeScript interfaces
- [x] Create `lib/api.ts` — Fetch wrapper
- [x] Create `lib/websocket.ts` — WebSocket client with reconnection
- [x] Create `lib/store.ts` — Zustand stores

### 1.11 Frontend — Shared Components
- [x] Create `components/shared/Layout.tsx` — App shell
- [x] Create `components/shared/Sidebar.tsx` — Navigation sidebar
- [x] Create `components/shared/ThemeToggle.tsx` — Dark/light mode toggle
- [x] Create `components/shared/LoadingStates.tsx` — Skeleton loaders, spinner

### 1.12 Frontend — Chat Interface
- [x] Create `app/chat/page.tsx` — Chat page with WebSocket streaming, markdown rendering
- [x] Create `styles/chat.css` — Chat styles with animations

### 1.13 Frontend — Vault Browser
- [x] Create `app/vault/page.tsx` — Vault browser with file tree + note preview
- [x] Create `styles/vault.css` — Vault styles

### 1.14 Frontend — Dashboard
- [x] Create `app/page.tsx` — Dashboard with stats, activity, quick actions
- [x] Create `styles/dashboard.css` — Dashboard styles

### 1.15 Frontend — Settings
- [x] Create `app/settings/page.tsx` — Settings with LLM provider, privacy toggles
- [x] Create `styles/settings.css` — Settings styles

### 1.16 Phase 1 — Integration & Verification
- [ ] Install Python dependencies (pip install -r requirements.txt)
- [ ] Install spaCy model (python -m spacy download en_core_web_sm)
- [ ] Install frontend dependencies (npm install)
- [ ] Fix import issues and verify backend starts
- [ ] Fix frontend build issues and verify it compiles
- [ ] End-to-end test: Send chat message → receive AI response
- [ ] End-to-end test: Swap LLM provider in YAML
- [ ] End-to-end test: Privacy sanitizer redacts PII
- [ ] End-to-end test: Vault tree loads and displays notes
- [ ] End-to-end test: WebSocket streaming
- [ ] Run all KPI benchmarks

---

## Phase 2 — Vault Intelligence & Remaining Skills
*(Not started — awaiting Phase 1 completion)*

### 2.1 Backend — Link Resolution & Graph
- [ ] Create `core/link_resolver.py`
- [ ] Create `core/backlink_index.py`
- [ ] Create `core/vault_graph.py`
- [ ] Modify `core/vault_manager.py` — incremental indexing
- [ ] Modify `core/context_builder.py` — link-graph-aware context
- [ ] Modify `data/chroma_store.py` — heading-based chunking

### 2.2 Backend — Remaining 5 Skills
- [ ] Create `skills/builtin/linker.py`
- [ ] Create `skills/builtin/daily_briefing.py`
- [ ] Create `skills/builtin/tag_manager.py`
- [ ] Create `skills/builtin/template_filler.py`
- [ ] Create `skills/builtin/vault_analyst.py`

### 2.3 Frontend — Graph & Advanced Vault
- [ ] Create `components/vault/GraphView.tsx` (Cytoscape.js)
- [ ] Create `components/vault/SearchBar.tsx`
- [ ] Create `components/vault/NoteEditor.tsx`
- [ ] Create `app/vault/[note]/page.tsx`

---

## Phase 3–5
*(See implementation_plan.md for full details)*
- [ ] Phase 3: Feedback Loop, Analytics & UX Polish
- [ ] Phase 4: Security, Custom Skills & Extensibility
- [ ] Phase 5: Production Hardening & Docker
