# Aurora — Architecture & Flow Diagrams (v2)

> Complete system overview — AI-Powered Obsidian Assistant

---

## 1. System Architecture Diagram

```mermaid
graph TD
    subgraph Ingestion ["Ingestion Layer — Multi-Channel Input"]
        Email["📧 Email\nIMAP Polling"]
        WhatsApp["💬 WhatsApp\nText & Voice Notes"]
        Meetings["🎙️ Meeting Audio\nOnline Loopback · IRL Mic"]
        Diarization["Speaker Diarization\n& Voiceprint Registry"]
        IngestionPipeline["Ingestion Pipeline\nCapture · Transcribe · Normalize"]
    end

    subgraph Frontend ["Frontend — Next.js"]
        Pages["Pages\nDashboard · Chat · Vault · Settings · Analytics"]
        Components["Components\nChat UI · Vault Browser · Knowledge Graph\nNote Editor · Feedback · Privacy Rules"]
        Stores["State Management — Zustand"]
        APIClient["REST Client"]
        WSClient["WebSocket Client"]
    end

    subgraph Gateway ["API Gateway — FastAPI"]
        Auth["Authentication & Rate Limiting"]
        REST["REST API\nChat · Vault · Settings · Analytics"]
        WS["WebSocket — Real-time Streaming"]
    end

    subgraph Core ["Core Services"]
        VaultMgr["Vault Manager\nIndexing · CRUD · Caching"]
        Privacy["Privacy Sanitizer\nPII Detection · Tokenization · Audit"]
        SessionMgr["Session Manager"]
        ContextBld["Context Builder\nBudget-aware Assembly"]
        LinkEngine["Link Resolver · Backlink Index"]
        VaultGraph["Knowledge Graph"]
        Feedback["Feedback Engine"]
        PluginMgr["Plugin Manager\nHot-reload · Config Watcher"]
    end

    subgraph AI ["AI Orchestration — LangGraph"]
        Orchestrator["Orchestrator — State Machine\nSanitize → Context → Route → Execute → Format"]
        SkillRouter["Skill Router\nSlash Commands → Heuristics → LLM Fallback"]
        SkillRegistry["Skill Registry"]
        Skills["Skills\nNote Creator · Note Finder · Summarizer\nLinker · Daily Briefing · Tag Manager\nTemplate Filler · Vault Analyst · Custom Skills"]
        LLMClient["LLM Client + Fallback"]
        EmbedMgr["Embedding Manager"]
    end

    subgraph LLMs ["LLM Providers"]
        OpenAI["OpenAI"]
        Gemini["Gemini"]
        Claude["Claude"]
        Ollama["Ollama (Local)"]
    end

    subgraph Data ["Data Layer"]
        SQLite[("SQLite\nSessions · Messages · Audit · Settings")]
        ChromaDB[("ChromaDB\nVector Embeddings")]
        VaultFS[("Obsidian Vault\nMarkdown Files")]
    end

    subgraph Infra ["Infrastructure"]
        FileWatcher["File Watcher"]
        Logger["Structured Logger"]
        MDParser["Markdown Parser"]
        Docker["Docker & CI/CD"]
    end

    %% Ingestion Layer
    Email --> IngestionPipeline
    WhatsApp --> IngestionPipeline
    Meetings --> Diarization
    Diarization --> IngestionPipeline
    IngestionPipeline --> Privacy
    IngestionPipeline --> VaultMgr

    %% Frontend
    Pages --> Stores
    Components --> Pages
    Stores --> APIClient
    Stores --> WSClient

    %% Frontend → Gateway
    APIClient -- "HTTP" --> Auth
    WSClient -- "WebSocket" --> WS
    Auth --> REST

    %% Gateway → Services
    REST --> SessionMgr
    REST --> Orchestrator
    WS --> Orchestrator

    %% Orchestrator pipeline
    Orchestrator --> Privacy
    Orchestrator --> ContextBld
    Orchestrator --> SkillRouter
    Orchestrator --> Feedback
    SkillRouter --> SkillRegistry
    SkillRegistry --> Skills
    Skills --> LLMClient
    Skills --> VaultMgr

    %% Context
    ContextBld --> VaultMgr
    ContextBld --> ChromaDB
    ContextBld --> EmbedMgr
    ContextBld --> LinkEngine
    LinkEngine --> VaultGraph
    EmbedMgr --> LLMs

    %% LLM
    LLMClient --> OpenAI
    LLMClient --> Gemini
    LLMClient --> Claude
    LLMClient --> Ollama

    %% Data
    VaultMgr --> VaultFS
    VaultMgr --> MDParser
    SessionMgr --> SQLite
    Privacy --> SQLite
    PluginMgr --> SkillRegistry

    %% Infra
    FileWatcher --> VaultMgr
```

---

## 2. Use Case Diagram

```mermaid
flowchart LR
    User(["👤 User"])

    subgraph Chat ["Chat & AI"]
        UC_Chat(["💬 Chat with AI Assistant"])
        UC_Create(["📝 Create Notes"])
        UC_Search(["🔍 Find & Search Notes"])
        UC_Summarize(["📋 Summarize Content"])
        UC_Link(["🔗 Discover Connections"])
        UC_Daily(["☀️ Daily Briefing"])
        UC_Tag(["🏷️ Manage Tags"])
        UC_Template(["📄 Fill Templates"])
        UC_Analyst(["📈 Vault Analytics"])
        UC_Feedback(["👍 Rate Responses"])
    end

    subgraph Vault ["Vault Management"]
        UC_Browse(["📂 Browse & View Notes"])
        UC_Edit(["✏️ Edit Notes"])
        UC_Graph(["🕸️ Knowledge Graph"])
        UC_Reindex(["🔄 Re-index Vault"])
    end

    subgraph System ["System Configuration"]
        UC_Dashboard(["📊 Dashboard & Metrics"])
        UC_Settings(["⚙️ Configure LLM & Privacy"])
        UC_Skills(["🔌 Manage Skills"])
        UC_Security(["🔐 Security & PIN Lock"])
        UC_Theme(["🌙 Theme Toggle"])
    end

    subgraph Ingestion ["Multi-Channel Ingestion"]
        UC_Email(["📧 Email Ingestion"])
        UC_WhatsApp(["💬 WhatsApp Capture"])
        UC_Meeting(["🎙️ Meeting Recording & Transcription"])
        UC_Voiceprint(["🗣️ Speaker Identification"])
    end

    subgraph Auto ["Automatic Processes"]
        Sys_PII(["🔒 PII Detection & Tokenization"])
        Sys_Context(["🧠 Context Assembly"])
        Sys_Route(["🔀 Skill Routing"])
        Sys_Stream(["⚡ Response Streaming"])
        Sys_Detok(["🔓 PII Detokenization"])
        Sys_Watch(["👁️ File Change Monitoring"])
        Sys_Graph(["🕸️ Graph Computation"])
        Sys_Proactive(["🔔 Proactive Recall & Reminders"])
    end

    User --> UC_Chat
    User --> UC_Browse
    User --> UC_Dashboard
    User --> UC_Settings
    User --> UC_Theme

    UC_Chat --> UC_Create
    UC_Chat --> UC_Search
    UC_Chat --> UC_Summarize
    UC_Chat --> UC_Link
    UC_Chat --> UC_Daily
    UC_Chat --> UC_Tag
    UC_Chat --> UC_Template
    UC_Chat --> UC_Analyst
    UC_Chat --> UC_Feedback

    UC_Browse --> UC_Edit
    UC_Browse --> UC_Graph
    UC_Browse --> UC_Reindex

    UC_Settings --> UC_Skills
    UC_Settings --> UC_Security

    %% Ingestion connections
    UC_Meeting --> UC_Voiceprint
    UC_Email -. "includes" .-> Sys_PII
    UC_WhatsApp -. "includes" .-> Sys_PII
    UC_Meeting -. "includes" .-> Sys_PII

    UC_Chat -. "includes" .-> Sys_PII
    UC_Chat -. "includes" .-> Sys_Context
    UC_Chat -. "includes" .-> Sys_Route
    UC_Chat -. "includes" .-> Sys_Stream
    UC_Chat -. "includes" .-> Sys_Detok
    Sys_Context -. "includes" .-> Sys_Graph
```

---

## 3. Data Flow Diagram

```mermaid
flowchart LR
    User(["👤 User"])
    UI["Frontend\nNext.js + Zustand"]
    AUTH["Authentication"]
    GW["API Gateway"]
    SM["Session Manager"]
    PII["Privacy Sanitizer\nDetect → Tokenize PII"]
    CB["Context Builder\nVault + Graph + Embeddings"]
    SR["Skill Router\nSlash → Heuristic → LLM"]
    SKILL["Skill Execution\n8 Built-in + Custom Skills"]
    LLM(["LLM Provider"])
    DETOK["Detokenizer\nRestore PII"]
    FB["Feedback Engine"]

    %% Ingestion sources
    EmailSrc(["📧 Email"])
    WhatsAppSrc(["💬 WhatsApp"])
    MeetingSrc(["🎙️ Meetings"])
    Ingest["Ingestion Pipeline\nCapture · Transcribe · Normalize"]

    SQLite[("SQLite")]
    Chroma[("ChromaDB")]
    Vault[("Obsidian Vault")]
    Graph[("Knowledge Graph")]

    %% Ingestion flow
    EmailSrc --> Ingest
    WhatsAppSrc --> Ingest
    MeetingSrc --> Ingest
    Ingest -- "Sanitize" --> PII
    Ingest -- "Store notes" --> Vault

    %% Main user flow
    User -- "1. Query" --> UI
    UI -- "2. Request" --> AUTH
    AUTH -- "3. Verified" --> GW
    GW -- "4. Session" --> SM
    SM <--> SQLite
    GW -- "5. Raw message" --> PII
    PII -- "Audit" --> SQLite
    PII -- "6. Sanitized query" --> CB
    CB -- "7a. Embed" --> Chroma
    Chroma -- "7b. Relevant chunks" --> CB
    CB -- "7c. Notes" --> Vault
    Vault -- "7d. Content" --> CB
    CB -- "7e. Links" --> Graph
    Graph -- "7f. Connections" --> CB
    CB -- "8. Enriched context" --> SR
    SR -- "9. Matched skill" --> SKILL
    SKILL -- "10a. Vault ops" --> Vault
    SKILL -- "10b. Prompt" --> LLM
    LLM -- "11. Response" --> SKILL
    SR -- "9 alt. Direct chat" --> LLM
    LLM -- "11 alt." --> DETOK
    SKILL -- "12. Output" --> DETOK
    DETOK -- "13. Clean response" --> GW
    GW -- "14. Persist" --> SQLite
    GW -- "15. Stream" --> UI
    UI -- "16. Display" --> User
    User -- "17. Feedback" --> UI
    UI -- "18. Rating" --> FB
    FB -- "19. Tune" --> LLM
```

---

## 4. Process Flow Diagram

```mermaid
sequenceDiagram
    actor U as User
    participant F as Frontend
    participant API as API Gateway
    participant SM as SessionManager
    participant DB as SQLite
    participant PS as Privacy Sanitizer
    participant CB as Context Builder
    participant VDB as ChromaDB
    participant VM as Vault Manager
    participant KG as Knowledge Graph
    participant SR as Skill Router
    participant SK as Skill Engine
    participant LLM as LLM Provider
    participant FB as Feedback Engine

    U->>F: Send message
    F->>API: WebSocket request
    API->>SM: Load / create session
    SM->>DB: Read / write session
    DB-->>SM: Session data
    SM-->>API: Session ready

    Note over API: ═══ AI Pipeline Start ═══

    rect rgb(255, 240, 240)
        Note over PS: Step 1 — Sanitize Input
        API->>PS: Raw message
        PS->>PS: Detect PII (regex + NER)
        PS->>PS: Apply content filter rules
        PS->>PS: Tokenize PII (email → EMAIL_1)
        PS->>DB: Audit log
        PS-->>API: Sanitized message
    end

    rect rgb(240, 255, 240)
        Note over CB: Step 2 — Build Context
        API->>CB: Sanitized query
        CB->>VDB: Semantic vector search
        VDB-->>CB: Relevant note chunks
        CB->>VM: Recent & active notes
        VM-->>CB: Note content
        CB->>KG: Query link graph & backlinks
        KG-->>CB: Related connections
        CB->>CB: Trim to token budget
        CB-->>API: Context payload
    end

    rect rgb(240, 240, 255)
        Note over SR: Step 3 — Route to Skill
        API->>SR: Input + skill list
        alt Slash command (/create, /find, /summarize, etc.)
            SR-->>API: Exact match
        else Heuristic confidence > threshold
            SR-->>API: Best match
        else Ambiguous
            SR->>LLM: Classify input
            LLM-->>SR: Selected skill
            SR-->>API: Routed skill
        end
    end

    rect rgb(255, 255, 230)
        Note over SK: Step 4 — Execute
        alt Skill matched
            API->>SK: Run skill
            SK->>VM: Vault read/write/search
            VM-->>SK: Data
            SK->>LLM: Skill prompt + context
            LLM-->>SK: Generated content
            SK-->>API: Result
        else Direct chat
            API->>LLM: System prompt + context
            LLM-->>API: Response
        end
    end

    rect rgb(245, 240, 255)
        Note over PS: Step 5 — Format Response
        API->>PS: Raw LLM output
        PS->>PS: Detokenize (EMAIL_1 → email)
        PS-->>API: Final response
    end

    Note over API: ═══ AI Pipeline Complete ═══

    API->>DB: Persist message

    loop Token streaming
        API-->>F: Stream tokens
        F-->>U: Render live markdown
    end
    API-->>F: Stream complete

    U-->>F: Rate response (👍/👎)
    F-->>FB: Submit feedback
    FB-->>DB: Store rating
```
