# Aurora — Comprehensive File Structure and Workflow Explanation

This document provides a rigorous, exhaustive breakdown of every module in the Aurora project and how data moves through the system from the frontend to the backend AI orchestrator and back.

---

## 1. Complete File Structure & Component Roles

### Backend (`aurora-backend/`)
The backend is a FastAPI Python application responsible for AI orchestration, data privacy, and Obsidian vault indexing.

*   **Entry Points & Configuration:**
    *   `main.py`: The FastAPI application entry point. Handles the startup/shutdown lifecycle, mounts all API routers, and initializes singletons (like database connections and the skill registry).
    *   `config.py`: Loads and parses `aurora.yaml` and `.env` files. Recursively interpolates environment variables and provides a typed `AuroraConfig` object used across the system.
    *   `aurora.yaml`: The master configuration registry controlling which LLM is active, enabled skills, privacy rules, and port configurations.

*   **API Layer (`api/`) - *External Communication & Security***
    *   `api/routes/chat.py`, `vault.py`, `settings.py`: The REST endpoints for standard operations (creating sessions, reading vault stats, updating LLM providers).
    *   `api/websocket/chat_ws.py`: The WebSocket server using `ConnectionManager`. It broadcasts streaming events (token, start, end, error) to the client.
    *   `api/middleware/cors.py`: Defines Cross-Origin Resource Sharing rules allowing the Next.js frontend to talk to FastAPI.
    *   `api/middleware/rate_limit.py`: Implements a sliding-window IP rate limiter to protect the API from spam (e.g., max 60 requests per minute).

*   **Core Services (`core/`) - *The Business Logic***
    *   `core/vault_manager.py`: Handles local filesystem I/O. It discovers `.md` files, manages an in-memory `Note` cache, and executes CRUD operations on the Obsidian vault.
    *   `core/privacy_sanitizer.py`: The security engine. Coordinates four sub-components: `PIIDetector` (Regex + spaCy NER), `ContentFilterEngine` (tag/folder blocking), `TokenMapper` (bidirectional placeholder mapping), and audit logging.
    *   `core/context_builder.py`: Prepares the payload for the LLM. It calculates string token budgets (using a 4-chars/token heuristic) and trims retrieved vault notes to fit within the LLM's context window.
    *   `core/session_manager.py`: Manages the lifecycle of chat threads, persisting user and assistant messages via `SQLiteStore`.

*   **AI Orchestration (`ai/`) - *The AI Brain***
    *   `ai/orchestrator.py`: Implements the **LangGraph State Machine**. Defines the 5-node pipeline (`sanitize_input` -> `build_context` -> `route_to_skill` -> `execute_skill` -> `format_response`) and handles state propagation.
    *   `ai/llm_client.py`: The router for LLM execution. It dynamically loads the correct adapter based on `aurora.yaml` and handles automatic fallback if a provider fails.
    *   `ai/adapters/*` (`openai_adapter.py`, `gemini_adapter.py`, etc.): Concrete implementations adhering to the abstract `BaseAdapter`. They handle provider-specific API quirks.
    *   `ai/embeddings.py`: Generates mathematical vectors from text. Features a SHA-256 cache to avoid re-embedding identical text, saving API costs.
    *   `ai/prompts/`: Contains `system.py`, `templates.py`, and `skill_prompts.py`. These files define the exact persona, injection templates, and rule constraints the LLM must follow.

*   **Skills Framework (`skills/`) - *Agentic Capabilities***
    *   `skills/base_skill.py`: The abstract base class containing required hooks (`can_handle`, `execute`, `get_system_prompt`).
    *   `skills/registry.py`: Scans the built-in and custom folders on startup, dynamically loading only the skills marked `enabled: true` in `aurora.yaml`.
    *   `skills/router.py`: The decision engine. Uses a 3-stage heuristic: (1) strict Slash Commands (`/find`), (2) keyword confidence scoring, (3) LLM-based fallback classification.
    *   `skills/builtin/*`: Implementations of actual behaviors (`note_creator.py`, `note_finder.py`, `summarizer.py`).

*   **Data Layer (`data/`) - *Persistence & Memory***
    *   `data/models.py`: Exhaustive Pydantic definitions for every object in the system (Notes, Messages, Audits, Routing Results). Enforces strict typing boundaries.
    *   `data/sqlite_store.py`: Uses `aiosqlite` for asynchronous interaction with `aurora.db` (storing chat history, settings, and sanitization audit logs).
    *   `data/chroma_store.py`: Connects to local `chromadb.PersistentClient`. Handles insertion, chunking updates, and Cosine Similarity semantic search.
    *   `data/migrations/`: Tracks database schema versions (e.g., `001_initial.py`).

*   **Utilities (`utils/`) - *Helper Modules***
    *   `utils/markdown_parser.py`: Extracts YAML frontmatter, standardizes Obsidian `[[wiki-links]]`, and identifies `![[embeds]]`.
    *   `utils/file_watcher.py`: A daemon utilizing `watchdog`. Implements a 1.0-second debounce to batch rapid filesystem saves before triggering a re-index.
    *   `utils/logger.py`: Provides structured JSON logging and console color-coding, utilizing thread-local Correlation IDs to trace requests.
    *   `utils/validators.py`: Security checks against Path Traversal vulnerabilities, message length limits, and filename sanitization.

---

### Frontend (`aurora-frontend/`)
A Next.js 14 App Router application handling UI, state, and real-time streaming.

*   **Pages & Routing (`app/`)**
    *   `app/layout.tsx` & `globals.css`: The root layout applying the CSS design tokens (variables) for dark/light mode themes.
    *   `app/chat/page.tsx`: The primary chat interface. Handles typing indicators, auto-scrolling, and Markdown rendering.
    *   `app/vault/page.tsx`: A dual-pane browser rendering the vault structure as a hierarchical tree and providing note previews.
    *   `app/settings/page.tsx`: Controls for swapping LLM providers and adjusting privacy strictness.
    *   `app/page.tsx`: The dashboard overview displaying metrics (indexed notes, active sessions).

*   **State & Networking (`lib/`)**
    *   `lib/store.ts`: Uses Zustand for isolated, fast global state (`useChatStore`, `useVaultStore`, `useSettingsStore`).
    *   `lib/websocket.ts`: Robust WebSocket client. Uses exponential backoff (`Math.min(1000 * 2^attempts, 30000)`) to auto-reconnect without crashing the UI.
    *   `lib/api.ts`: A standardized REST fetch wrapper for cleanly interacting with backend endpoints (`chatApi`, `vaultApi`, `settingsApi`).
    *   `lib/types.ts`: TypeScript definitions mapping directly to the backend's Pydantic models.

*   **Components (`components/`)**
    *   `components/chat/StreamingResponse.tsx`: Combines `react-markdown` and `remark-gfm` to securely render Markdown incrementally.
    *   `components/shared/Layout.tsx` & `Sidebar.tsx`: The core UI shell and navigation.
    *   `components/shared/ThemeToggle.tsx`: Interacts with `localStorage` and `data-theme` attributes to toggle styles dynamically.
    *   `components/shared/LoadingStates.tsx`: Skeleton loaders and bounce-dot typing indicators.

*   **Configuration**
    *   `next.config.js`: Critically important for development—contains the reverse-proxy rewrites pointing `/api/*` and `/ws/*` to the FastAPI backend at `localhost:8000`.

---

## 2. Exhaustive Step-by-Step System Workflow

When a user submits a query (e.g., *"Summarize my recent thoughts on AI architecture"*), here is the rigorous, step-by-step path the data takes across the system:

1. **User Input & Networking:** 
   The user submits the form in `app/chat/page.tsx`. `lib/websocket.ts` serializes the payload `{"message": "...", "session_id": "..."}` and sends it over the WebSocket connection.
2. **Backend Gateway & Middleware:**
   FastAPI receives the frame at `api/websocket/chat_ws.py`. It establishes a connection via `ConnectionManager`. Concurrently, `api/middleware/rate_limit.py` verifies the IP hasn't exceeded the 60req/min limit.
3. **Session Resolution:**
   The `SessionManager` (`core/session_manager.py`) validates the `session_id`. If it's a new chat, it generates a UUID and persists a new record via `data/sqlite_store.py`. The raw message is logged to the database.
4. **LangGraph Start (Node 1: Sanitization):**
   `ai/orchestrator.py` initiates the state machine. The state passes to `core/privacy_sanitizer.py`.
   *   *Regex:* Fast pass strips emails/phones.
   *   *NER:* spaCy analyzes sentence structure to identify personal names.
   *   *Filter:* Checks if the query references a blocked tag (e.g., `#private`).
   *   *Audit:* The mappings (e.g., "John" -> `<PERSON_1>`) are saved in RAM and an audit log is written to SQLite.
5. **Context Assembly (Node 2: Build Context):**
   The sanitized text goes to `core/context_builder.py`.
   *   It sends the text to `ai/embeddings.py` (which checks the SHA-256 cache first).
   *   The embedding vector is passed to `data/chroma_store.py` to execute a Cosine Similarity search against the Obsidian vault chunks.
   *   The builder takes the top *N* chunks, measures their token length, trims them to the configured budget, and attaches them to the LangGraph state.
6. **Intent Routing (Node 3: Route to Skill):**
   The state is passed to `skills/router.py`.
   *   If the user typed `/summarize`, confidence is `1.0`.
   *   If heuristics fail, `LLMClient` is invoked to ask the LLM to classify the intent.
   *   The router selects the active skill (in this case, `skills/builtin/summarizer.py`).
7. **Execution (Node 4: Execute Skill):**
   `summarizer.py` takes control. It fetches the specific `SUMMARIZATION_PROMPT` from `ai/prompts/templates.py`. It combines the prompt, the context chunks, and the user's sanitized message.
   It passes this payload to `ai/llm_client.py`, which validates the configuration and hands it off to `ai/adapters/openai_adapter.py` (or whichever provider is active).
8. **Generation & Stream (Node 5: Format Response):**
   The LLM generates text. As each token yields back to the Orchestrator, it passes through `core/privacy_sanitizer.py`'s detokenization method. If `<PERSON_1>` is detected in the stream, it is instantly replaced with "John".
9. **Delivery to Client:**
   `chat_ws.py` emits the text chunk as a JSON payload (`{"type": "token", "content": "..."}`).
10. **Frontend Rendering:**
    `lib/websocket.ts` receives the event and updates the Zustand store (`lib/store.ts`). `components/chat/StreamingResponse.tsx` forces a re-render, safely parsing the incoming Markdown via `react-markdown`.
11. **Persistence:**
    Once the LLM finishes, a `{"type": "end"}` event is sent. The `SessionManager` updates the SQLite database with the final, complete assistant message, along with metrics (skill used, tokens consumed).
12. **Vault Sync (Background):**
    If the AI (or the user directly) saves a note, `utils/file_watcher.py` detects the filesystem change. After a 1-second debounce, it alerts `core/vault_manager.py` to re-read the file with `utils/markdown_parser.py`, which then updates the vector embeddings in `chroma_store.py`, keeping the assistant's memory perfectly synchronized.
