# Corrected Use Case Diagram

The original use case diagram had several fundamental UML and logical errors regarding how actors interact with the system. Here is a corrected version using Mermaid, followed by an explanation of the exact fixes made.

## Fixed Use Case Diagram

```mermaid
flowchart LR
    %% Actors
    User(["👤 User (General / Power / Admin)"])
    Daemon(["⚙️ Background System (Daemon)"])
    LLM(["🤖 External LLM Provider"])

    %% Vault & Knowledge Management
    subgraph Vault ["Vault & Knowledge Management"]
        direction TB
        UC_Browse(["Browse Vault"])
        UC_Search(["Search Notes"])
        UC_Create(["Create / Edit Note"])
        UC_Tags(["Manage Tags & Links"])
    end

    %% AI Assistant & RAG
    subgraph AI ["AI Assistant & RAG"]
        direction TB
        UC_Ask(["💬 Ask Aurora (Query)"])
        UC_Brief(["☀️ Daily Briefing"])
        UC_Context(["🧠 Retrieve Relevant Context"])
        UC_Gen(["🤖 Generate Context-Aware Response"])
    end

    %% Privacy & Security
    subgraph Privacy ["Privacy & Security"]
        direction TB
        UC_Rules(["🛡️ Manage Privacy Rules"])
        UC_Audit(["📜 View Audit Logs"])
        UC_Sanitize(["🔒 Detect & Sanitize PII"])
        UC_Restore(["🔓 Restore PII (Detokenize)"])
    end

    %% Configuration
    subgraph Config ["Configuration & Admin"]
        direction TB
        UC_LLMConf(["⚙️ Configure LLM Provider"])
        UC_Skills(["🔌 Manage Skills"])
    end

    %% Synchronization
    subgraph Sync ["Synchronization"]
        direction TB
        UC_Watch(["👁️ Monitor Vault Changes"])
        UC_Index(["🔄 Incremental Re-indexing"])
    end

    %% User Associations
    User --> UC_Browse
    User --> UC_Search
    User --> UC_Create
    User --> UC_Tags

    User --> UC_Ask
    User --> UC_Brief

    User --> UC_Rules
    User --> UC_Audit
    User --> UC_LLMConf
    User --> UC_Skills

    %% System Daemon Associations
    Daemon --> UC_Watch
    UC_Watch -. "<<include>>" .-> UC_Index

    %% Includes & Flow for 'Ask Aurora'
    UC_Ask -. "<<include>>" .-> UC_Sanitize
    UC_Ask -. "<<include>>" .-> UC_Context
    UC_Ask -. "<<include>>" .-> UC_Gen
    UC_Gen -. "<<include>>" .-> UC_Restore

    %% External LLM Provider Associations
    UC_Gen --- LLM
    UC_Brief --- LLM
```

---

## What was wrong with the original diagram?

1. **Incorrect Actor Connections for Privacy:** 
   In your original diagram, the "Power User" directly initiated "Detect Sensitive Data" and "Sanitize PII". **Fix:** Users do not manually click a button to sanitize data. Sanitization is a background process that happens automatically when they chat. Therefore, "Detect & Sanitize PII" should be an `<<include>>` dependency stemming from the "Ask Aurora" use case.
2. **Incorrect Actor for Synchronization:**
   The "Administrator" was shown initiating "Monitor Vault Changes". **Fix:** A human administrator does not manually monitor the vault for file changes. This is done by the `watchdog` background service. I introduced a "Background System (Daemon)" actor to handle this automatic trigger, which then `<<include>>`s "Incremental Re-indexing".
3. **LLM Provider connected to Configuration:**
   The external "LLM Provider" (OpenAI/Gemini) was connected to "Select LLM Provider" and "Configure aurora.yaml". **Fix:** The LLM provider does not configure your app! It only receives prompts and generates responses. I disconnected the LLM Provider from the Config section and attached it purely to "Generate Context-Aware Response" and "Daily Briefing".
4. **"Used in AI Processing" is not a Use Case:**
   Use cases must be verbs/actions (e.g., "Retrieve Context", "Generate Response"). "Used in AI processing" is a vague state, not an action. **Fix:** I mapped the flow correctly so that "Ask Aurora" explicitly `<<include>>`s Context Retrieval, Sanitization, and Response Generation.
