# Mind Lite Manual Testing Guide

This guide walks through testing Mind Lite end-to-end with real services.

## Prerequisites

- Docker installed
- Python 3.12+ installed
- Obsidian installed
- Optional: LM Studio for local LLM
- Optional: OpenRouter API key for cloud LLM

---

## Step 1: Start Qdrant

```bash
# Create data directory
mkdir -p .mind_lite/qdrant_data

# Run Qdrant container
docker run -d \
  --name mind-lite-qdrant \
  -p 6333:6333 \
  -v $(pwd)/.mind_lite/qdrant_data:/qdrant/storage \
  --restart unless-stopped \
  qdrant/qdrant:latest

# Verify Qdrant is running
curl http://localhost:6333/health
```

Expected response:
```json
{"title":"qdrant - vector search engine","version":"..."}
```

---

## Step 2: Start the API

```bash
# Set environment
export MIND_LITE_QDRANT_URL=http://localhost:6333
export MIND_LITE_STATE_FILE=.mind_lite/state.json
export MIND_LITE_RAG_SQLITE_PATH=.mind_lite/rag.db

# Run the API
PYTHONPATH=src python3 -m mind_lite.api
```

Expected output:
```
Mind Lite API listening on http://127.0.0.1:8000
```

Verify:
```bash
curl http://localhost:8000/health
```

---

## Step 3: Configure LLM

### Option A: OpenRouter (Cloud, Free tier available)

1. Get API key at https://openrouter.ai/keys

2. Set the API key:
```bash
curl -X POST http://localhost:8000/llm/config/api-key \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-or-..."}'
```

3. Select a model:
```bash
curl -X POST http://localhost:8000/llm/config \
  -H "Content-Type: application/json" \
  -d '{"provider": "openrouter", "model": "deepseek/deepseek-r1-0528:free"}'
```

### Option B: LM Studio (Local, no API key)

1. Start LM Studio
2. Load a model
3. Enable server on port 1234
4. Configure:
```bash
curl -X POST http://localhost:8000/llm/config \
  -H "Content-Type: application/json" \
  -d '{"provider": "lmstudio", "model": "lmstudio:local"}'
```

Verify configuration:
```bash
curl http://localhost:8000/llm/config
```

---

## Step 4: Index Your Vault

Replace `/path/to/your/vault` with your Obsidian vault path:

```bash
curl -X POST http://localhost:8000/rag/index-vault \
  -H "Content-Type: application/json" \
  -d '{"vault_path": "/path/to/your/vault"}'
```

Expected response:
```json
{
  "files_indexed": 42,
  "chunks_created": 150
}
```

Check status:
```bash
curl http://localhost:8000/rag/status
```

---

## Step 5: Test /ask

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What projects am I working on?"}'
```

Expected response includes:
- `answer.text` - Generated answer
- `citations` - List of source notes
- `llm_trace` - LLM provider info

---

## Step 6: Test Retrieval Directly

```bash
curl -X POST http://localhost:8000/rag/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "project notes", "top_k": 5}'
```

Expected response:
```json
{
  "citations": [
    {
      "note_id": "notes/project.md",
      "path": "notes/project.md",
      "excerpt": "...",
      "chunk_id": "...",
      "score": 0.92
    }
  ]
}
```

---

## Step 7: Test Model Switching

List available models:
```bash
curl http://localhost:8000/llm/models
```

Switch to a different model:
```bash
curl -X POST http://localhost:8000/llm/config \
  -H "Content-Type: application/json" \
  -d '{"provider": "openrouter", "model": "google/gemini-2.0-flash-exp:free"}'
```

Ask again to use new model:
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize my recent work"}'
```

---

## Step 8: Install Obsidian Plugin

```bash
cd obsidian-plugin
npm install
npm run build

# Copy to your vault
cp main.js manifest.json styles.css /path/to/vault/.obsidian/plugins/mind-lite/
```

Enable in Obsidian:
1. Settings → Community Plugins
2. Enable "Mind Lite"

---

## Step 9: Test Plugin Commands

In Obsidian command palette (Ctrl/Cmd + P):

1. **Mind Lite: Switch Model**
   - Opens model picker with Free/Local/Smart tabs
   - Select model, optionally enter API key

2. **Mind Lite: Analyze Folder**
   - Enter folder path
   - Returns run ID and state

3. **Mind Lite: Review Proposals**
   - Shows proposals from last run

4. **Mind Lite: Apply Approved**
   - Applies safe changes

5. **Mind Lite: Daily Triage**
   - Quick analysis of current folder

6. **Mind Lite: Publish to GOM**
   - Draft content through editorial gate

---

## Step 10: Test Integration Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Ensure services are running
export MIND_LITE_QDRANT_URL=http://localhost:6333
export OPENROUTER_API_KEY=sk-or-...

# Run integration tests
pytest -m integration tests/integration/ -v
```

---

## Troubleshooting

### Qdrant not starting
```bash
docker logs mind-lite-qdrant
```

### API not responding
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill existing process
kill -9 <PID>
```

### LLM errors
- For OpenRouter: Verify API key is valid
- For LM Studio: Ensure server is running on port 1234

### Embedding errors
First run downloads ~500MB model. Wait for completion.

### No citations in /ask
- Ensure vault is indexed first
- Check Qdrant is running

---

## Cleanup

```bash
# Stop containers
docker stop mind-lite-qdrant

# Remove data
rm -rf .mind_lite/

# Remove containers
docker rm mind-lite-qdrant
```
