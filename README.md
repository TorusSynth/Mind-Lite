# Mind Lite

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)]()

**A local-first second brain engine for Obsidian** — organize notes, rebuild graph links, query your knowledge with RAG, and publish through quality gates.

---

## Features

### 🧠 RAG-Powered Q&A
Ask questions about your notes and get grounded answers with citations:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What projects am I working on?"}'
```

Returns answers with citations pointing to source notes — no hallucinations, full traceability.

### 🔗 Smart Link Suggestions
LLM-powered link proposals with anti-spam controls:
- Confidence scoring (0.0-1.0)
- Target saturation limits
- Automatic filtering of weak suggestions

### 📁 PARA Organization
Automatic classification into Projects, Areas, Resources, Archive:
- Primary + secondary labels
- Risk-tiered action modes (auto/suggest/manual)
- Safe auto-apply for high-confidence changes

### 📤 GOM Publishing Pipeline
Stage-aware editorial gates (seed → sprout → tree):
- Quality scoring with hard-fail checks
- Revision queue for failed drafts
- Export-ready content generation

### 🔄 Model Switching
Choose between **Free**, **Local**, and **Smart** LLM categories:

| Category | Provider | Examples |
|----------|----------|----------|
| **Free** | OpenRouter | DeepSeek R1, Gemini 2.0 Flash, Llama 3.3 70B |
| **Local** | LM Studio | Your local model, no API key needed |
| **Smart** | OpenRouter | Claude Opus 4.6, GPT-5.2, DeepSeek V3.2 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MIND LITE STACK                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Obsidian Plugin (TypeScript)                                  │
│   ├── Command palette integration                               │
│   ├── Review/apply modals                                       │
│   └── Model picker UI                                           │
│                                                                  │
│   ─────────────────────────────────────────────────────────────  │
│                                                                  │
│   Python API Server (port 8000)                                 │
│   ├── /ask — RAG-powered Q&A                                    │
│   ├── /rag/* — Indexing & retrieval                             │
│   ├── /llm/* — Model configuration                              │
│   ├── /organize/* — PARA classification                         │
│   ├── /links/* — Link proposals                                 │
│   └── /publish/* — GOM pipeline                                 │
│                                                                  │
│   ─────────────────────────────────────────────────────────────  │
│                                                                  │
│   Storage Layer                                                  │
│   ├── Qdrant — Vector search (Docker)                           │
│   ├── SQLite — Metadata & provenance                            │
│   └── sentence-transformers — Local embeddings                  │
│                                                                  │
│   ─────────────────────────────────────────────────────────────  │
│                                                                  │
│   LLM Providers                                                  │
│   ├── LM Studio — Local inference (http://localhost:1234)       │
│   └── OpenRouter — Cloud models (300+ including free tiers)     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+ (for Obsidian plugin)
- Docker (for Qdrant)
- LM Studio (optional, for local LLM)

### 1. Clone & Install

```bash
git clone https://github.com/TorusSynth/Mind-Lite.git
cd Mind-Lite
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Start Qdrant (Vector Database)

```bash
mkdir -p .mind_lite/qdrant_data

docker run -d \
  --name mind-lite-qdrant \
  -p 6333:6333 \
  -v $(pwd)/.mind_lite/qdrant_data:/qdrant/storage \
  --restart unless-stopped \
  qdrant/qdrant:latest

# Verify
curl http://localhost:6333/health
```

### 3. Start the API

```bash
export MIND_LITE_QDRANT_URL=http://localhost:6333
export MIND_LITE_STATE_FILE=.mind_lite/state.json
export MIND_LITE_RAG_SQLITE_PATH=.mind_lite/rag.db

PYTHONPATH=src python3 -m mind_lite.api
```

Expected output:
```
Mind Lite API listening on http://127.0.0.1:8000
```

### 4. Configure LLM

**Option A: OpenRouter (Free tier available)**

```bash
# Get your key at https://openrouter.ai/keys
curl -X POST http://localhost:8000/llm/config/api-key \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-or-..."}'

# Select a free model
curl -X POST http://localhost:8000/llm/config \
  -H "Content-Type: application/json" \
  -d '{"provider": "openrouter", "model": "deepseek/deepseek-r1-0528:free"}'
```

**Option B: LM Studio (Local, no API key)**

```bash
# Start LM Studio, load a model, enable server on port 1234
# Then configure:
curl -X POST http://localhost:8000/llm/config \
  -H "Content-Type: application/json" \
  -d '{"provider": "lmstudio", "model": "lmstudio:local"}'
```

### 5. Index Your Vault

```bash
curl -X POST http://localhost:8000/rag/index-vault \
  -H "Content-Type: application/json" \
  -d '{"vault_path": "/path/to/your/obsidian/vault"}'
```

### 6. Ask Questions

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What am I working on this week?"}'
```

### 7. Install Obsidian Plugin

```bash
cd obsidian-plugin
npm install
npm run build
```

Copy to your vault:
```bash
cp main.js manifest.json styles.css /path/to/vault/.obsidian/plugins/mind-lite/
```

Enable **Mind Lite** in Obsidian Community Plugins.

---

## Available Commands (Obsidian)

| Command | Description |
|---------|-------------|
| `Mind Lite: Switch Model` | Choose between Free/Local/Smart models |
| `Mind Lite: Analyze Folder` | Generate PARA classification proposals |
| `Mind Lite: Review Proposals` | Review pending changes by risk tier |
| `Mind Lite: Apply Approved` | Apply safe, approved changes |
| `Mind Lite: Rollback` | Undo last batch of changes |
| `Mind Lite: Propose Links` | Get link suggestions for a note |
| `Mind Lite: Apply Links` | Apply approved link proposals |
| `Mind Lite: Daily Triage` | Quick daily review workflow |
| `Mind Lite: Weekly Deep Review` | Comprehensive weekly review |
| `Mind Lite: Publish to GOM` | Gate-check and queue for publication |

---

## API Endpoints

### RAG
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/rag/index-vault` | Index entire vault |
| `POST` | `/rag/index-folder` | Index specific folder |
| `GET` | `/rag/status` | Get indexing statistics |
| `POST` | `/rag/retrieve` | Retrieve relevant chunks |

### LLM Configuration
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/llm/models` | List available models |
| `GET` | `/llm/config` | Get current configuration |
| `POST` | `/llm/config` | Set active model |
| `POST` | `/llm/config/api-key` | Set OpenRouter API key |
| `DELETE` | `/llm/config/api-key` | Clear API key |

### Q&A
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ask` | Ask question with RAG citations |

See [API.md](API.md) for complete documentation.

---

## Model Categories

### 🆓 Free (OpenRouter)
Zero-cost cloud models:

| Model | Context | Best For |
|-------|---------|----------|
| `openrouter/free` | 200K | Auto-select best free |
| `deepseek/deepseek-r1-0528:free` | 164K | Reasoning tasks |
| `google/gemini-2.0-flash-exp:free` | 1M | Long documents |
| `meta-llama/llama-3.3-70b-instruct:free` | 131K | General purpose |
| `qwen/qwen3-coder:free` | 262K | Code tasks |

### 💻 Local (LM Studio)
Your hardware, your privacy:
- No API key required
- No network dependency
- Full privacy for sensitive content

### 🧠 Smart (OpenRouter)
Premium models for complex tasks:

| Model | Context | Best For |
|-------|---------|----------|
| `anthropic/claude-opus-4.6` | 200K | Complex reasoning |
| `openai/gpt-5.2` | 400K | General excellence |
| `deepseek/deepseek-v3.2` | 164K | Value + quality |

---

## Environment Variables

Copy `.env.example` to `.env`:

```bash
# Qdrant
MIND_LITE_QDRANT_URL=http://localhost:6333
MIND_LITE_RAG_COLLECTION=mind_lite_chunks

# SQLite
MIND_LITE_RAG_SQLITE_PATH=.mind_lite/rag.db

# Embeddings
MIND_LITE_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2

# LLM
MIND_LITE_LMSTUDIO_URL=http://localhost:1234
OPENROUTER_API_KEY=sk-or-...

# API State
MIND_LITE_STATE_FILE=.mind_lite/state.json
```

---

## Testing

### Backend Unit Tests
```bash
PYTHONPATH=src python3 -m unittest discover -q
```

### Integration Tests (requires running services)
```bash
# Install dev dependencies
pip install -e ".[dev]"

# Start Qdrant
docker run -d --name mind-lite-qdrant -p 6333:6333 qdrant/qdrant:latest

# Run integration tests
export MIND_LITE_QDRANT_URL=http://localhost:6333
pytest -m integration tests/integration/ -v

# Or skip integration tests
SKIP_INTEGRATION=1 pytest tests/
```

### Obsidian Plugin
```bash
cd obsidian-plugin
npm run verify
```

---

## Docker Deployment

### Quick Start with Docker Compose

```bash
# One-command startup (Qdrant + API)
docker compose up -d

# With GOM preview (adds Nginx on port 8080)
docker compose --profile preview up -d

# View logs
docker compose logs -f api
```

Services:
- **qdrant** — Vector database on port 6333
- **api** — Mind Lite API on port 8000
- **gom-preview** — Nginx static server on port 8080 (optional)

### Manual Docker Build

Build and run with Docker:

```bash
# Build
docker build -t mind-lite-api .

# Run (requires Qdrant running)
docker run -d \
  --name mind-lite-api \
  -p 8000:8000 \
  -e MIND_LITE_QDRANT_URL=http://host.docker.internal:6333 \
  -v $(pwd)/.mind_lite:/data \
  --add-host=host.docker.internal:host-gateway \
  mind-lite-api
```

---

## Documentation

| File | Description |
|------|-------------|
| [API.md](API.md) | Complete endpoint documentation |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and components |
| [ROADMAP.md](ROADMAP.md) | Feature progression and phases |
| [DECISIONS.md](DECISIONS.md) | Architecture decision records |
| [docs/MANUAL_TESTING.md](docs/MANUAL_TESTING.md) | Step-by-step manual testing guide |

---

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| A | Contracts & Safety Foundations | ✅ Complete |
| B | Vault Onboarding Engine | ✅ Complete |
| C | Organization & Graph Reconstruction | ✅ Complete |
| D | Model Routing & Privacy Control | ✅ Complete |
| E | Obsidian UX & Review Workflow | ✅ Complete |
| F | GOM Publishing & Editorial Gate | ✅ Complete |
| RAG | Full Architecture | ✅ Complete |
| LLM | Model Switching (OpenRouter + LM Studio) | ✅ Complete |
| Tests | Integration Tests | ✅ Complete |
| Docker | Docker Compose & GOM Adapters | ✅ Complete |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Obsidian](https://obsidian.md/) — The best note-taking app
- [Qdrant](https://qdrant.tech/) — High-performance vector database
- [OpenRouter](https://openrouter.ai/) — Unified LLM API with free tiers
- [sentence-transformers](https://www.sbert.net/) — State-of-the-art embeddings
- [LM Studio](https://lmstudio.ai/) — Local LLM inference
