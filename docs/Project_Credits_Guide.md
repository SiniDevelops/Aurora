# Comprehensive Project Credit Distribution & Defense Guide

This guide extensively details the roles, responsibilities, technical contributions, and interview defense strategies for all three members of the Aurora project. By dividing the system into three distinct, highly technical domains, each team member can confidently claim ownership of a complex subsystem that demonstrates advanced software engineering and AI concepts.

---

## 1. Team Member 1: Privacy & Security Engineer
**Domain Ownership:** The Privacy Sanitizer Engine & Audit Layer
**Core Files:** `core/privacy_sanitizer.py`, `data/models.py` (Privacy Models)

### Comprehensive Pitch
> *"My primary responsibility was engineering the privacy and security boundary for the Aurora assistant. Because the application processes highly personal knowledge bases (Obsidian vaults) and interfaces with external cloud LLMs (like OpenAI or Gemini), we had to guarantee zero leakage of Personally Identifiable Information (PII). I architected a deterministic and probabilistic redaction pipeline. It intercepts outbound prompts, uses a combination of high-speed Regex for structured data and a local spaCy NLP model for unstructured entity recognition, and substitutes sensitive data with reversible placeholder tokens (e.g., `<PERSON_1>`). I also built the detokenization engine that intercepts the LLM's streaming response and seamlessly rehydrates the placeholders with the original data before it hits the UI, ensuring the user experience remains completely natural while maintaining strict data sovereignty."*

### Deep Technical Details
- **The Dual-Layer Detection Engine:**
  - **Layer 1 (Deterministic):** Uses heavily optimized, pre-compiled Regular Expressions to catch structured PII such as email addresses, phone numbers, credit card strings, IPv4/IPv6 addresses, and API keys. This runs in microseconds.
  - **Layer 2 (Probabilistic):** Uses `spaCy` (specifically the `en_core_web_sm` model) to perform Named Entity Recognition (NER). This catches context-dependent unstructured data like person names, organizations, and geographical locations.
- **The Token Mapper & Bijective Mapping:**
  - When PII is detected, it is stripped and stored in a session-scoped, in-memory dictionary (a bijective map).
  - The engine replaces the text with a semantic token (e.g., `<EMAIL_1>`, `<ORG_2>`). This semantic tagging is crucial because it allows the LLM to understand the *context* of the redacted entity (knowing it's a person vs. a company) without knowing the actual entity.
- **Content Filter Engine:**
  - Added support for folder-level and tag-level blocking (e.g., strictly omitting any notes tagged `#confidential` or residing in a `Journal/` folder).
- **Audit Logging:**
  - Every sanitization event is logged to the SQLite database (`audit_log` table) for transparency, allowing users to see exactly what was hidden from the AI.

### Advanced Defense / Interview Questions
**Q: NLP models like spaCy can introduce significant latency. How does your sanitizer affect the real-time feel of the chat application?**
*A: "It's a valid concern. To mitigate latency, the Regex engine runs first, stripping out the 'easy' structured data. The spaCy model only processes the remaining text. Because chat messages are typically short (a few sentences), the NER inference time is virtually negligible (usually under 50ms). We only run this pipeline on the user's prompt and the retrieved context chunks, not on the entire vault simultaneously."*

**Q: What happens if the LLM slightly modifies or hallucinates the token in its response (e.g., outputs `<PERSON-1>` instead of `<PERSON_1>`)?**
*A: "The detokenization engine uses a robust regex matcher to look for the token pattern `<[A-Z]+_\d+>` rather than doing strict string matching. However, if the LLM completely hallucinates a token that isn't in our session map, the system is designed to gracefully leave the token as-is rather than crashing, which alerts the user to the hallucination."*

---

## 2. Team Member 2: Semantic Retrieval & Data Engineer
**Domain Ownership:** The Data Ingestion Pipeline & ChromaDB Vector Search
**Core Files:** `utils/markdown_parser.py`, `data/chroma_store.py`, `ai/embeddings.py`

### Comprehensive Pitch
> *"I engineered the Retrieval-Augmented Generation (RAG) data pipeline, which is what gives the AI its 'memory' of the user's personal vault. First, I had to build a custom Markdown Parser because standard libraries fail on Obsidian's unique syntax (like YAML frontmatter and `[[wiki-links]]`). Once the data was parsed and cleaned, I integrated ChromaDB to handle vector storage and semantic search. I designed a pipeline that chunks the text, hashes it via SHA-256 to cache embeddings and avoid redundant API costs, and converts the text into high-dimensional vectors. When a user asks a question, my code calculates the Cosine Similarity between the question's vector and the vault's vectors, instantly surfacing the exact notes the AI needs to answer accurately."*

### Deep Technical Details
- **Custom Obsidian Markdown Parser:**
  - Extracts structural metadata from the `---` YAML block at the top of notes.
  - Cleans out Markdown syntax noise (like bolding, italics, blockquotes) that can skew embedding weights.
  - Specifically detects and maps relational graphs using Obsidian's `[[Link]]` syntax, making the data ready for future graph-based retrieval.
- **Intelligent Chunking & Hashing:**
  - Text isn't just split blindly by character count. It's chunked structurally (by paragraphs or headers) to preserve semantic meaning.
  - **SHA-256 Embedding Cache:** Before calling the embedding API (e.g., `text-embedding-3-small`), the chunk is hashed. If the hash exists in the local cache, the embedding is loaded instantly. This saves immense API costs and speeds up re-indexing when only a single typo in a note is fixed.
- **ChromaDB Semantic Search:**
  - Utilizes `chromadb.PersistentClient` for local, offline-capable vector storage.
  - Transforms user queries into vectors and executes a Top-K retrieval based on Cosine Similarity distance, filtering out irrelevant noise before passing it to the Context Builder.

### Advanced Defense / Interview Questions
**Q: Why use semantic vector search instead of traditional keyword indexing like ElasticSearch?**
*A: "Keyword search fails on synonyms and context. If a user asks, 'What are my goals for physical health?', a keyword search might miss a note titled '2026 Fitness Objectives' because none of the words overlap. By converting text to vector embeddings, we map sentences based on meaning. The distance between the vectors for 'physical health' and 'fitness objectives' is very small, allowing ChromaDB to retrieve the exact right note based on conceptual intent."*

**Q: How do you handle note updates? If I modify a file, doesn't your vector database end up with duplicate chunks?**
*A: "I designed the indexing pipeline to be idempotent. When the file watcher detects a modified file, my pipeline first queries ChromaDB to delete all existing chunks associated with that specific `file_path` or `note_id`. Then, it parses, chunks, and inserts the updated note. The SHA-256 cache ensures we only regenerate embeddings for the specific paragraphs that actually changed."*

---

## 3. You (Lead / Full-Stack AI Architect)
**Domain Ownership:** LangGraph Orchestration, App Architecture, API Gateway, Frontend
**Core Files:** `main.py`, `ai/orchestrator.py`, `skills/router.py`, `aurora-frontend/*`

### Comprehensive Pitch
> *"As the Lead Architect, my job was to design the overarching system architecture and build the connective tissue that turned isolated backend scripts into a real-time, user-facing product. On the backend, I engineered the LangGraph state machine, which orchestrates the complex flow of data—passing it through the privacy sanitizer, into the context builder, through a multi-stage skill router, and finally to the LLM adapters. I also built the FastAPI gateway, standardizing the LLM interface so we can seamlessly swap between OpenAI, Gemini, or local models. Finally, I built the entire frontend using Next.js 14 and Zustand, implementing WebSockets with exponential backoff to handle real-time streaming Markdown generation for a seamless ChatGPT-like user experience."*

### Deep Technical Details
- **LangGraph State Machine Orchestration:**
  - Modeled the chat request lifecycle as a Directed Acyclic Graph (DAG) with specific nodes: `sanitize_input` -> `build_context` -> `route_to_skill` -> `execute_skill` -> `format_response`.
  - This graph-based approach allows for highly predictable state management, conditional branching (e.g., skipping context retrieval if it's just a casual greeting), and robust error recovery boundaries.
- **Multi-Stage Skill Router:**
  - Implemented a 3-tier classification engine:
    1. **Slash Commands:** Exact deterministic routing (`/summarize`).
    2. **Heuristics:** Evaluates `can_handle()` functions inside skills for keyword triggers.
    3. **LLM Fallback:** Passes the skill descriptions to a lightweight LLM (like `gpt-4o-mini`) to classify the user's intent.
- **Provider-Agnostic LLM Adapters:**
  - Built an abstract interface allowing the system to hot-swap between OpenAI, Anthropic, Gemini, and Ollama purely via YAML configuration, meaning no code changes are required to change models.
- **Real-Time Next.js Frontend:**
  - Utilized `Zustand` for lightweight global state management (managing the chat session and vault trees).
  - Implemented custom CSS design tokens for a performant, dependency-free dark/light mode system.
  - Handled the complexities of streaming WebSockets, including progressive Markdown rendering via `react-markdown` and automatic auto-scrolling (`messagesEndRef`).

### Advanced Defense / Interview Questions
**Q: Why use LangGraph for orchestration instead of just writing a linear Python function?**
*A: "While a linear script works for simple wrappers, Aurora is a complex autonomous agent. We needed conditional logic (routing to different skills), cyclic correction (if an LLM fails a tool call, we want to loop back and retry), and strict state management. LangGraph treats the pipeline as a state machine where each node receives a typed `State` object. It makes the architecture vastly more debuggable, extensible, and fault-tolerant."*

**Q: WebSockets can be notoriously unstable. How did you ensure the frontend doesn't break if the FastAPI server restarts or drops the connection?**
*A: "I implemented a custom WebSocket client in the frontend that features automatic reconnection with exponential backoff. If the connection drops, it immediately tries to reconnect, but if it fails, it waits 1 second, then 2, then 4, up to a maximum of 30 seconds. This prevents 'thundering herd' problems where the frontend spams a recovering server, ensuring a resilient user experience."*
