# Claude Active Memory — Aurora Project
> **Purpose**: Persistent context for Claude to avoid hallucination and maintain consistency across sessions.  
> **Last updated**: 2026-08-28  
> **Conversation ID**: e2ffb078-e0d3-4103-8249-0162b590f617

---

## 1. Project Identity

| Field | Value |
|-------|-------|
| **Project Name** | Aurora |
| **Description** | Privacy-first, AI-powered personal knowledge assistant for Obsidian vaults |
| **Workspace** | `e:\AI-assistent` |
| **User** | Single-user, personal use |
| **OS** | Windows |

---

## 2. User Preferences (Immutable)

These were explicitly chosen by the user and must not be changed:

| Preference | Choice |
|-----------|--------|
| CSS Framework | **Vanilla CSS** with design tokens — NO Tailwind, NO shadcn/ui |
| LLM Support | **Multi-provider**: OpenAI, Gemini, Claude, Ollama |
| Deployment | **Local development** — Docker optional |
| Auth | **Single-user** with optional PIN/password lock |
| Python Package Manager | **pip + requirements.txt** |
| Phase 1 MVP | **Privacy-first**: Core chat + vault indexing + privacy sanitizer + 3 skills |
| YAML Swappable | **Skills + LLM providers** (NOT data stores) |
| Graph Library | **Cytoscape.js** (I decided — purpose-built for knowledge graphs) |
| Daily Briefing | **On-demand only** — no auto-scheduling |
| Obsidian Sync | **Event-driven** via watchdog file watcher |

---

## 3. Architecture Overview

```
Frontend (Next.js 14+, Vanilla CSS, TypeScript, Zustand)
    │ REST + WebSocket
Backend (Python 3.11+, FastAPI, uvicorn)
    ├── API Gateway (routes, middleware, websocket)
    ├── Core Services (vault_manager, privacy_sanitizer, session_manager, context_builder)
    ├── AI Orchestration (LangGraph state machine)
    │   └── LLM Adapters (OpenAI, Gemini, Claude, Ollama) — selected via aurora.yaml
    ├── Skills System (registry, router, 8 built-in + custom)
    └── Data Layer (SQLite for metadata, ChromaDB for vectors, filesystem for vault)
```

---

## 4. Technology Stack (Exact)

### Backend
| Package | Purpose | Min Version |
|---------|---------|-------------|
| python | Runtime | 3.11+ |
| fastapi | Web framework | 0.100+ |
| uvicorn | ASGI server | 0.27+ |
| langgraph | AI orchestration | Latest |
| pydantic | Data models | 2.0+ |
| spacy | NER (PII detection) | 3.7+ |
| chromadb | Vector DB | 0.4+ |
| watchdog | File watcher | 4.0+ |
| openai | OpenAI client | 1.0+ |
| anthropic | Claude client | 0.25+ |
| google-generativeai | Gemini client | 0.5+ |
| httpx | HTTP (Ollama) | 0.27+ |
| pyyaml | Config parsing | 6.0+ |
| python-dotenv | Env vars | 1.0+ |
| websockets | WebSocket server | 12.0+ |
| aiosqlite | Async SQLite | 0.20+ |

### Frontend
| Package | Purpose | Min Version |
|---------|---------|-------------|
| next | Framework | 14+ |
| typescript | Types | 5.0+ |
| zustand | State mgmt | 4.0+ |
| cytoscape | Graph viz | 3.28+ (Phase 2) |
| socket.io-client | WebSocket | 4.7+ |

### spaCy Model
- Download: `python -m spacy download en_core_web_sm`
- Used for: Named Entity Recognition in Privacy Sanitizer

---

## 5. Key Design Patterns

### YAML Component Replacement
- `aurora.yaml` is the **single source of truth** for component wiring
- LLM providers: set `llm.active_provider` to switch (openai/gemini/claude/ollama)
- Skills: set `skills.builtin.<name>.enabled` to true/false
- Custom skills: drop `skill.yaml` + `skill.py` in `skills/custom/` — auto-discovered
- Secrets: use `${ENV_VAR}` syntax in YAML, resolved from `.env`

### LLM Adapter Pattern
```python
# Abstract base
class LLMAdapter(ABC):
    async def complete(messages, **kwargs) -> str
    async def stream(messages, **kwargs) -> AsyncIterator[str]
    def get_model_info() -> ModelInfo

# Concrete: OpenAIAdapter, GeminiAdapter, ClaudeAdapter, OllamaAdapter
# Selected at runtime by config.py reading aurora.yaml
```

### Privacy Pipeline (Mandatory — CANNOT be bypassed)
```
User Input → PII Detector (regex + spaCy) → Content Filter (user rules) → Token Mapper → [Sanitized to LLM]
LLM Response → De-tokenizer → [Clean response to user]
```

### Skill Routing (3-stage)
1. Command prefix check (`/create` → note_creator)
2. Each skill self-rates confidence (0.0–1.0)
3. LLM-based intent classification (fallback if no winner >0.7)

### LangGraph State Machine
```
START → sanitize_input → build_context → route_to_skill → execute_skill → format_response → END
```

---

## 6. File-to-Purpose Map (Critical Files)

| File | Purpose | Phase |
|------|---------|-------|
| `aurora.yaml` | Master config — LLM, skills, privacy, vault, all settings | 1 |
| `aurora-backend/config.py` | Load YAML, interpolate env vars, provide typed config | 1 |
| `aurora-backend/main.py` | FastAPI app, lifespan events, router mounting | 1 |
| `core/vault_manager.py` | Walk vault dir, read/write notes, index | 1 |
| `core/privacy_sanitizer.py` | PII detection, content filtering, tokenization, de-tokenization | 1 |
| `core/context_builder.py` | Assemble vault context within token budget | 1 |
| `core/session_manager.py` | Chat session CRUD, history | 1 |
| `core/link_resolver.py` | Resolve [[wiki links]], aliases, headings, blocks | 2 |
| `core/vault_graph.py` | Knowledge graph, community detection, orphans | 2 |
| `core/feedback_engine.py` | Collect and apply user feedback | 3 |
| `ai/orchestrator.py` | LangGraph state machine | 1 |
| `ai/llm_client.py` | Provider-agnostic LLM client | 1 |
| `ai/adapters/base.py` | Abstract LLM adapter interface | 1 |
| `skills/base_skill.py` | Abstract BaseSkill with hooks | 1 |
| `skills/registry.py` | Load/register skills from YAML | 1 |
| `skills/router.py` | 3-stage skill routing | 1 |
| `data/models.py` | All Pydantic models | 1 |
| `data/sqlite_store.py` | SQLite operations | 1 |
| `data/chroma_store.py` | ChromaDB vector operations | 1 |

---

## 7. Phase Status

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | ⏳ Awaiting approval | Foundation + Privacy MVP (3 skills) |
| **Phase 2** | 🔲 Not started | Vault Intelligence + 5 remaining skills |
| **Phase 3** | 🔲 Not started | Feedback + Analytics + UX polish |
| **Phase 4** | 🔲 Not started | Security + Custom Skill SDK |
| **Phase 5** | 🔲 Not started | Docker + Production hardening |

---

## 8. Skills Claude Needs to Build This Project

These are the capabilities I (Claude Opus 4.6) need to execute this project effectively:

### Core Coding Skills
| Skill | Proficiency Required | What For |
|-------|---------------------|----------|
| **Python 3.11+ async** | Expert | FastAPI routes, async file I/O, LLM calls, all core services |
| **FastAPI** | Expert | REST endpoints, WebSocket handlers, middleware, dependency injection, lifespan events |
| **Pydantic v2** | Expert | All data models, config validation, serialization/deserialization |
| **TypeScript** | Expert | All frontend code, strict typing, generics for API client |
| **React 18+ (Next.js App Router)** | Expert | Server/client components, layouts, dynamic routes, streaming SSR |
| **CSS (Vanilla, no framework)** | Expert | Design tokens, custom properties, responsive layouts, animations, dark mode, glassmorphism |
| **SQL (SQLite)** | Advanced | Schema design, migrations, FTS5 full-text search, async queries |

### AI/ML Skills
| Skill | Proficiency Required | What For |
|-------|---------------------|----------|
| **LangGraph** | Advanced | State machine design, conditional edges, node composition, error handling |
| **LLM API Integration** | Expert | OpenAI, Anthropic, Google Gemini, Ollama — streaming, function calling, embeddings |
| **Prompt Engineering** | Expert | System prompts, skill-specific prompts, routing prompts, template design |
| **Vector Databases (ChromaDB)** | Advanced | Embedding storage, similarity search, metadata filtering, collection management |
| **NLP (spaCy)** | Intermediate | Named Entity Recognition for PII detection, model loading, entity extraction |
| **RAG (Retrieval-Augmented Generation)** | Advanced | Context building, chunking strategies, hybrid search, relevance ranking |

### Architecture Skills
| Skill | Proficiency Required | What For |
|-------|---------------------|----------|
| **Adapter/Strategy Pattern** | Expert | LLM provider swapping, skill plug-in system |
| **Event-Driven Architecture** | Advanced | File watcher events, WebSocket events, real-time sync |
| **YAML Configuration Design** | Advanced | Component replacement system, schema design, env interpolation |
| **State Machine Design** | Advanced | LangGraph orchestration, multi-step AI pipelines |
| **Privacy Engineering** | Advanced | PII detection, reversible tokenization, content filtering, audit logging |
| **API Design (REST + WebSocket)** | Expert | Endpoint design, error responses, streaming, rate limiting |

### DevOps Skills
| Skill | Proficiency Required | What For |
|-------|---------------------|----------|
| **Docker** | Intermediate | Multi-stage builds, compose, volume management |
| **Testing (pytest + Jest)** | Advanced | Unit tests, integration tests, mocking, coverage |
| **CI/CD (GitHub Actions)** | Intermediate | Lint/test/build pipeline |

### Domain Knowledge
| Area | Required Understanding | What For |
|------|----------------------|----------|
| **Obsidian Markdown** | Deep | Wiki links, tags, frontmatter YAML, embeds, aliases, block references, canvas files |
| **Knowledge Graphs** | Intermediate | Link resolution, backlink computation, community detection, orphan finding |
| **Cytoscape.js** | Intermediate | Graph visualization, layouts, events, styling (Phase 2) |

---

## 9. Key Constraints & Non-Negotiables

1. **Privacy sanitizer is MANDATORY** — cannot be bypassed in the pipeline
2. **All LLM-bound content MUST pass through sanitizer** — no shortcuts
3. **YAML is the single source of truth** — no hardcoded provider/skill selections
4. **Vanilla CSS only** — no Tailwind, no CSS-in-JS, no component libraries
5. **Async-first** — all I/O operations must be async
6. **Pydantic at every boundary** — all API inputs/outputs, config, data models
7. **Obsidian compatibility** — must handle all Obsidian markdown features (wiki links, frontmatter, tags, embeds, aliases)
8. **Graceful degradation** — if LLM fails, show error; if vault disconnects, use cache
9. **Event-driven vault sync** — use watchdog with debounced events, emit WebSocket notifications

---

## 10. Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| spaCy NER misses PII | Privacy breach | Combine regex + NER; err on side of over-detection; user can allowlist |
| Large vault (10k+ notes) slows indexing | Poor UX | Incremental indexing with content hashing; background re-index |
| WebSocket disconnects | Broken streaming | Auto-reconnect with exponential backoff; fallback to polling |
| Ollama not installed | LLM adapter fails | Graceful error message; suggest installing or switching provider in YAML |
| ChromaDB embedded mode limits | Scaling | Sufficient for single-user; Docker mode available for larger vaults |
| YAML config errors | App won't start | Validate YAML schema on load; clear error messages pointing to exact line |

---

## 11. Context Documents Location

All original spec documents are at `e:\AI-assistent\context\`:
- `ARCHITECTURE.md.docx` — Full system architecture (already read and incorporated)
- `OBSIDIAN_VAULT_SCHEMA.md.docx` — Vault structure, note schema, indexing pipeline (already read)
- `PRIVACY_SANITIZER_SPEC.md.docx` — Sanitizer pipeline, PII detection, rules engine (already read)
- `SKILLS_SPECIFICATION.md.docx` — Skills system, base skill, 8 built-in skills, router, registry (already read)

---

## 12. Conversation History Summary

| Timestamp | Action |
|-----------|--------|
| 2026-08-28 00:46 | User asked for phased implementation plan with KPIs |
| 2026-08-28 00:47 | Read all 4 context documents (ARCHITECTURE, OBSIDIAN_VAULT_SCHEMA, PRIVACY_SANITIZER_SPEC, SKILLS_SPECIFICATION) |
| 2026-08-28 00:52 | Asked 7 clarifying questions, received answers |
| 2026-08-28 00:56 | Created implementation_plan.md (5 phases, KPIs, YAML system, project structure) |
| 2026-08-28 01:13 | Resolved open questions (Cytoscape.js, on-demand briefing, event-driven sync) |
| 2026-08-28 01:14 | Created task.md with 100+ granular tasks |
| 2026-08-28 01:14 | Created claude.md (this file) — active memory |

---

## 13. Next Actions

When user approves:
1. Start Phase 1.1 — Project scaffolding (`aurora.yaml`, `.env.example`, `.gitignore`, `README.md`)
2. Then Phase 1.2 — Backend setup (`requirements.txt`, `main.py`, `config.py`)
3. Follow task.md sequentially, marking tasks as complete

**DO NOT** skip ahead to later phases without completing Phase 1 verification.
