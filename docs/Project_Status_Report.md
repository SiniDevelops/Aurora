# Algorithms

- **Cosine Similarity (Vector Search)** – Measures semantic similarity between the user's query embedding and stored note chunk embeddings in ChromaDB to retrieve the most contextually relevant vault content.

- **Named Entity Recognition (spaCy NER)** – Uses a pre-trained NLP model (`en_core_web_sm`) to detect semantic PII entities (person names, organizations, locations) that cannot be caught by deterministic regex patterns alone.

- **Regex-based Pattern Matching (PII Detection)** – Deterministic first-pass detection of structured PII (emails, phone numbers, credit cards, API keys, IP addresses) using compiled regular expressions for high-speed scanning.

- **Token Mapping & Bidirectional Substitution** – Anonymizes detected PII into reversible placeholder tokens (e.g., `alice@mail.com → <EMAIL_1>`) using a session-scoped bijective map, enabling lossless de-tokenization after LLM processing.

- **Budget-aware Context Trimming** – Estimates token count using a 4-characters-per-token heuristic and trims retrieved vault notes to fit within a configurable token budget (default 4000), prioritizing the most relevant content.

- **Multi-stage Classification (Skill Routing)** – A 3-stage cascading classifier that routes user input to the correct skill: (1) exact slash-command prefix matching (confidence 1.0), (2) heuristic keyword confidence scoring via `can_handle()` (threshold > 0.7), (3) LLM-based intent classification as fallback.

- **SHA-256 Content Hashing (Embedding Cache)** – Hashes input text with SHA-256 to create cache keys, avoiding redundant embedding API calls for previously seen content.

- **Sliding Window Rate Limiting** – Tracks per-IP request timestamps in a sliding time window (60 requests/minute) to throttle excessive API usage while allowing legitimate burst traffic.

- **Exponential Backoff (Reconnection)** – WebSocket client implements automatic reconnection with exponentially increasing delays (`min(1000 × 2^attempts, 30000)` ms) to avoid thundering-herd problems during server restarts.

- **Debounced Event Processing (File Watcher)** – Filesystem change events from Watchdog are debounced with a 1-second window to coalesce rapid successive file modifications into a single re-index operation.

- **Speaker Diarization & Voiceprint Matching (Planned)** – Pyannote 3.1 segments meeting audio into speaker turns, generates 512-dimensional voice embeddings, and matches against enrolled voiceprint profiles using cosine similarity (threshold ≥ 0.82).

- **Community Detection on Knowledge Graph (Planned)** – Identifies clusters of densely connected notes in the vault's link graph to surface thematic groupings and improve context retrieval relevance.

---

# Technologies & Frameworks

- **Next.js 14 (App Router) + TypeScript** – Frontend framework with server-side rendering, file-based routing, and Zustand for global state management using vanilla CSS design tokens.

- **FastAPI + Python** – High-performance async backend framework providing REST endpoints and WebSocket real-time streaming for the AI chat interface.

- **LangGraph (State Machine Orchestration)** – Orchestrates the AI pipeline as a directed acyclic graph with 5 sequential nodes: Sanitize → Build Context → Route Skill → Execute → Format Response.

- **Multi-Provider LLM Adapter Pattern** – Abstracts LLM providers (OpenAI, Gemini, Claude, Ollama) behind a common interface, enabling YAML-driven provider swapping with zero code changes and automatic fallback support.

- **spaCy NER + Regex PII Pipeline** – Privacy-first sanitization combining Named Entity Recognition with deterministic regex patterns for detecting and tokenizing personally identifiable information before any data reaches external LLMs.

- **ChromaDB (Vector Store) + SQLite** – Hybrid storage layer using ChromaDB with persistent client for semantic vector search on vault note embeddings, and SQLite for relational data (sessions, messages, audit logs, settings).

- **Multi-Channel Ingestion Pipeline** – Planned capture and transcription layer for Email (IMAP), WhatsApp (text & voice notes), and Meeting Audio (system loopback + IRL mic) with speaker diarization and voiceprint-based identification.

---

# Implementation Plan & Current Status

## COMPLETED

**1. Project Scaffolding & Configuration**

- Master `aurora.yaml` configuration file with YAML-driven component registry
- Environment variable interpolation (`${ENV_VAR}`) with `.env` support
- Root project structure with `.gitignore`, `README.md`, and `.env.example`

**2. Data Layer & Storage**

- Pydantic domain models for all entities (Notes, Chat, Privacy, Skills, Settings)
- SQLite async database operations (sessions, messages, audit log, settings, skill usage)
- ChromaDB vector store wrapper with persistent client
- Database migration framework (initial schema)

**3. Core Services**

- Vault Manager — file discovery, indexing, in-memory caching, CRUD operations
- Privacy Sanitizer — PII detection (regex + spaCy NER), content filtering (folder/tag block rules), token mapping, bidirectional de-tokenization, audit logging
- Session Manager — chat session lifecycle, message history persistence
- Context Builder — budget-aware context assembly with token estimation and trimming

**4. AI Orchestration & LLM Integration**

- Abstract LLM adapter interface with 4 provider implementations (OpenAI, Gemini, Claude, Ollama)
- Provider-agnostic LLM client with fallback adapter support
- Embedding Manager with SHA-256 in-memory caching
- LangGraph 5-node state machine orchestrator (sanitize → context → route → execute → format)
- System prompts, skill-specific prompts, and context injection templates

**5. Skills System**

- Abstract BaseSkill class with lifecycle hooks (validate, pre-execute, execute, post-execute)
- Skill Registry with YAML-driven dynamic discovery and loading
- 3-stage Skill Router (slash commands → heuristic confidence → LLM fallback classification)
- 3 built-in skills implemented: Note Creator, Note Finder, Summarizer

**6. API Layer & Middleware**

- REST endpoints: Chat (message, history, sessions), Vault (tree, CRUD, search, reindex, stats), Settings (config, privacy, LLM providers)
- WebSocket endpoint with ConnectionManager for real-time token streaming
- CORS middleware and sliding-window IP-based rate limiter (60 req/min)
- Health check and readiness probe endpoints

**7. Frontend Application**

- Next.js 14 App Router with 4 pages: Dashboard, Chat, Vault Browser, Settings
- CSS design system with 50+ design tokens (colors, spacing, typography, shadows) for light/dark themes
- Zustand stores: Chat, Vault, Settings, App state
- REST API client and WebSocket client with auto-reconnect and exponential backoff
- Shared components: Layout, Sidebar, Theme Toggle, Loading States (Spinner, Skeleton, Typing Indicator)

**8. Utilities & Infrastructure**

- Markdown parser (YAML frontmatter, wiki links, embeds, tags)
- Watchdog-based vault file watcher with debounce
- Structured logging (JSON file + colored console) with correlation IDs
- Input validators (path traversal prevention, filename sanitization, content validation)

---

## TO BE IMPLEMENTED

**9. Vault Intelligence & Knowledge Graph**

- Link Resolver — full Obsidian link resolution (wiki links, aliases, headings, block refs)
- Backlink Index — reverse link index with context extraction
- Vault Graph — knowledge graph data structure with community detection
- Incremental indexing with content hash diffing
- Heading-based chunking strategy for ChromaDB

**10. Remaining 5 Built-in Skills**

- Linker — connection discovery and link suggestions
- Daily Briefing — on-demand vault activity summary
- Tag Manager — tag operations (suggest, rename, organize)
- Template Filler — template-based note generation
- Vault Analyst — vault statistics and health insights

**11. Advanced Frontend Features**

- Interactive knowledge graph visualization (Cytoscape.js)
- Individual note view with backlinks
- Note editor with markdown preview
- Advanced search with filters (tags, folders, date ranges)

**12. Feedback Loop & Analytics**

- Feedback engine (thumbs up/down, corrections, prompt tuning)
- Analytics dashboard — usage charts, skill performance, privacy stats, vault health
- Sanitization preview panel (show what was redacted)
- Micro-animations, glassmorphism effects, responsive design polish

**13. Security & Extensibility**

- Optional PIN/password authentication with session token management
- Custom Skill SDK — development kit, dynamic loader, manifest validator
- Plugin Manager — hot-reload of custom skills on file change
- Config Watcher — live `aurora.yaml` reload without restart
- Privacy rules and skill management via frontend UI

**14. Multi-Channel Ingestion Layer**

- Email ingestion via IMAP polling
- WhatsApp text and voice note bridge
- Meeting audio capture (system loopback + IRL room mic)
- Speaker diarization (Pyannote 3.1) and voiceprint registry
- Proactive reminder daemon for surfacing unfulfilled commitments

**15. Production Hardening & Deployment**

- Docker multi-stage builds and docker-compose orchestration
- CI/CD pipeline (GitHub Actions — lint, test, build)
- Comprehensive test suite (unit + integration, >80% coverage)
- Performance optimization (connection pooling, response caching)
- PWA with service worker for offline support
