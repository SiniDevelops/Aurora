# Aurora — AI-Powered Obsidian Assistant

> Privacy-first, AI-powered personal knowledge assistant that integrates deeply with Obsidian vaults.

## Features

- 🔒 **Privacy-First**: PII detection and sanitization — sensitive data never reaches LLMs
- 🧠 **Context-Aware**: Deep understanding of your knowledge graph via semantic + full-text search
- 🔌 **Multi-LLM**: Swap between OpenAI, Gemini, Claude, and local Ollama — one YAML change
- 🛠️ **Skill System**: Pluggable skills for note creation, search, summarization, and more
- ⚡ **Real-Time**: WebSocket streaming for instant AI responses
- 🌙 **Dark/Light Mode**: Beautiful UI with design tokens

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- An Obsidian vault
- At least one LLM provider (OpenAI API key, or local Ollama)

### Setup

```bash
# 1. Clone and enter the project
cd e:\AI-assistent

# 2. Set up environment variables
copy .env.example .env
# Edit .env with your API keys and vault path

# 3. Backend setup
cd aurora-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 4. Start the backend
uvicorn main:app --reload --port 8000

# 5. Frontend setup (new terminal)
cd aurora-frontend
npm install
npm run dev
```

### Configuration

All configuration is in `aurora.yaml` at the project root.

**Switch LLM Provider:**
```yaml
llm:
  active_provider: "ollama"  # Change to: openai, gemini, claude, ollama
```

**Enable/Disable Skills:**
```yaml
skills:
  builtin:
    summarizer:
      enabled: true   # Toggle to false to disable
```

**Add Privacy Rules:**
```yaml
privacy:
  content_rules:
    - id: "my-rule"
      name: "Block Work Notes"
      rule_type: "folder_block"
      config:
        folders: ["Work/Confidential"]
      enabled: true
```

## Architecture

```
Frontend (Next.js + TypeScript + Vanilla CSS)
    │ REST + WebSocket
Backend (Python + FastAPI + LangGraph)
    ├── API Gateway (routes, middleware)
    ├── Core Services (vault, privacy, sessions, context)
    ├── AI Orchestration (LangGraph state machine)
    │   └── LLM Adapters (OpenAI, Gemini, Claude, Ollama)
    ├── Skills System (registry, router, built-in + custom)
    └── Data Layer (SQLite + ChromaDB)
```

## Project Structure

```
aurora.yaml              # Master configuration
aurora-backend/          # Python/FastAPI backend
├── main.py              # App entry point
├── config.py            # YAML config loader
├── api/                 # REST + WebSocket endpoints
├── core/                # Core services
├── ai/                  # LLM adapters + orchestrator
├── skills/              # Skill system
├── data/                # Data models + stores
└── utils/               # Utilities
aurora-frontend/         # Next.js frontend
├── app/                 # Pages (App Router)
├── components/          # React components
├── lib/                 # API client, store, types
└── styles/              # CSS design tokens
```

## License

Private — Personal Use
