# RAG Full Architecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a full RAG architecture with ingestion, chunking, embeddings, vector retrieval, and citation-backed `/ask` responses.

**Architecture:** Add a dedicated retrieval layer with SQLite metadata/chunk storage and Qdrant vector search, then connect it to new RAG endpoints and `/ask`. Keep policy/routing protections intact, and make retrieval provenance first-class so citations are always grounded in indexed chunks.

**Tech Stack:** Python (`unittest`, `sqlite3`), Qdrant (`qdrant-client`), sentence-transformers embeddings, existing `http.server` API, TypeScript plugin compatibility.

---

### Task 1: Add RAG configuration and dependency plumbing

**Files:**
- Modify: `pyproject.toml`
- Create: `src/mind_lite/rag/__init__.py`
- Create: `src/mind_lite/rag/config.py`
- Test: `tests/rag/test_config.py`

**Step 1: Write failing config tests**

```python
def test_default_rag_config_values():
    from mind_lite.rag.config import get_rag_config
    cfg = get_rag_config()
    assert cfg.qdrant_url
    assert cfg.collection_name
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_config -q`
Expected: FAIL with module import error.

**Step 3: Implement minimal config module**

Create `RagConfig` dataclass and env-backed defaults:
- `MIND_LITE_QDRANT_URL` (default `http://localhost:6333`)
- `MIND_LITE_RAG_COLLECTION` (default `mind_lite_chunks`)
- `MIND_LITE_RAG_SQLITE_PATH` (default `.mind_lite/rag.db`)
- `MIND_LITE_EMBED_MODEL` (default `sentence-transformers/all-MiniLM-L6-v2`)

**Step 4: Run test to verify pass**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_config -q`

**Step 5: Commit**

```bash
git add pyproject.toml src/mind_lite/rag/__init__.py src/mind_lite/rag/config.py tests/rag/test_config.py
git commit -m "feat: add RAG configuration module"
```

---

### Task 2: Implement chunking + stable IDs

**Files:**
- Create: `src/mind_lite/rag/chunking.py`
- Test: `tests/rag/test_chunking.py`

**Step 1: Write failing chunking tests**

Test for:
- chunk boundaries and overlap
- stable `chunk_id` derivation from path + index + content hash input
- deterministic output ordering

**Step 2: Run tests to verify fail**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_chunking -q`

**Step 3: Implement minimal chunker**

Include:
- token proxy splitter (word-based for v1)
- overlap support
- `ChunkRecord` dataclass with offsets

**Step 4: Run tests to verify pass**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_chunking -q`

**Step 5: Commit**

```bash
git add src/mind_lite/rag/chunking.py tests/rag/test_chunking.py
git commit -m "feat: add deterministic RAG chunking"
```

---

### Task 3: Add SQLite repositories for documents/chunks/ingestion runs

**Files:**
- Create: `src/mind_lite/rag/sqlite_store.py`
- Test: `tests/rag/test_sqlite_store.py`

**Step 1: Write failing storage tests**

Test:
- schema creation
- upsert document/chunks
- stale chunk deletion on reindex
- ingestion run state writes

**Step 2: Run test to verify fail**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_sqlite_store -q`

**Step 3: Implement SQLite repository**

Add methods:
- `init_schema()`
- `upsert_document(...)`
- `replace_chunks_for_document(...)`
- `record_ingestion_run(...)`
- `get_status_summary()`

**Step 4: Run tests to verify pass**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_sqlite_store -q`

**Step 5: Commit**

```bash
git add src/mind_lite/rag/sqlite_store.py tests/rag/test_sqlite_store.py
git commit -m "feat: add SQLite provenance store for RAG"
```

---

### Task 4: Add embedding adapter

**Files:**
- Create: `src/mind_lite/rag/embeddings.py`
- Test: `tests/rag/test_embeddings.py`

**Step 1: Write failing embedding tests**

Test:
- model loads lazily
- returns vectors with stable dimensions
- handles empty input list

**Step 2: Run tests to verify fail**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_embeddings -q`

**Step 3: Implement adapter**

Wrap sentence-transformers with:
- `embed_texts(list[str]) -> list[list[float]]`
- `embed_query(str) -> list[float]`

**Step 4: Run tests to verify pass**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_embeddings -q`

**Step 5: Commit**

```bash
git add src/mind_lite/rag/embeddings.py tests/rag/test_embeddings.py
git commit -m "feat: add local embedding adapter for RAG"
```

---

### Task 5: Add Qdrant vector index adapter

**Files:**
- Create: `src/mind_lite/rag/vector_index.py`
- Test: `tests/rag/test_vector_index.py`

**Step 1: Write failing vector index tests**

Test:
- collection ensure/create
- upsert points
- search top-k
- delete stale chunk ids

Use mocks/fakes for Qdrant client where possible.

**Step 2: Run tests to verify fail**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_vector_index -q`

**Step 3: Implement adapter**

Methods:
- `ensure_collection(vector_size)`
- `upsert_chunks(...)`
- `search(query_vector, top_k)`
- `delete_chunks(chunk_ids)`

**Step 4: Run tests to verify pass**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_vector_index -q`

**Step 5: Commit**

```bash
git add src/mind_lite/rag/vector_index.py tests/rag/test_vector_index.py
git commit -m "feat: add Qdrant vector index adapter"
```

---

### Task 6: Build ingestion service (vault/folder indexing)

**Files:**
- Create: `src/mind_lite/rag/indexing.py`
- Modify: `src/mind_lite/onboarding/analyze_readonly.py` (reuse file collection helpers if useful)
- Test: `tests/rag/test_indexing.py`

**Step 1: Write failing ingestion tests**

Test end-to-end indexing over fixture markdown files:
- documents/chunks persisted
- vectors upserted
- stale chunks removed after content change

**Step 2: Run tests to verify fail**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_indexing -q`

**Step 3: Implement indexer**

Add functions:
- `index_vault(vault_path)`
- `index_folder(folder_path)`

**Step 4: Run tests to verify pass**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_indexing -q`

**Step 5: Commit**

```bash
git add src/mind_lite/rag/indexing.py src/mind_lite/onboarding/analyze_readonly.py tests/rag/test_indexing.py
git commit -m "feat: add RAG indexing pipeline"
```

---

### Task 7: Build retrieval service and citation assembly

**Files:**
- Create: `src/mind_lite/rag/retrieval.py`
- Test: `tests/rag/test_retrieval.py`

**Step 1: Write failing retrieval tests**

Test:
- top-k retrieval ordering
- citation object includes `note_id`, `path`, `excerpt`, `chunk_id`, `score`
- empty result behavior

**Step 2: Run tests to verify fail**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_retrieval -q`

**Step 3: Implement retrieval service**

Add:
- `retrieve(query, top_k)`
- provenance hydration from SQLite chunks/documents

**Step 4: Run tests to verify pass**

Run: `PYTHONPATH=src python3 -m unittest tests.rag.test_retrieval -q`

**Step 5: Commit**

```bash
git add src/mind_lite/rag/retrieval.py tests/rag/test_retrieval.py
git commit -m "feat: add citation-backed retrieval service"
```

---

### Task 8: Expose RAG API endpoints

**Files:**
- Modify: `src/mind_lite/api/service.py`
- Modify: `src/mind_lite/api/http_server.py`
- Test: `tests/api/test_api_service.py`
- Test: `tests/api/test_http_server.py`

**Step 1: Write failing endpoint tests**

Add tests for:
- `POST /rag/index-vault`
- `POST /rag/index-folder`
- `GET /rag/status`
- `POST /rag/retrieve`

**Step 2: Run tests to verify fail**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_http_server -q`

**Step 3: Implement service + route handlers**

Wire new methods into `ApiService` and HTTP router.

**Step 4: Run tests to verify pass**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service tests.api.test_http_server -q`

**Step 5: Commit**

```bash
git add src/mind_lite/api/service.py src/mind_lite/api/http_server.py tests/api/test_api_service.py tests/api/test_http_server.py
git commit -m "feat: expose RAG indexing and retrieval endpoints"
```

---

### Task 9: Integrate `/ask` with retrieval-backed citations

**Files:**
- Modify: `src/mind_lite/api/service.py`
- Test: `tests/api/test_api_service.py`
- Test: `tests/api/test_http_server.py`

**Step 1: Write failing ask+citation tests**

Test:
- indexed query returns non-empty citations
- retrieval trace present
- degraded behavior when index unavailable does not fabricate citations

**Step 2: Run tests to verify fail**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_ask_returns_retrieval_citations -v`

**Step 3: Implement retrieval-aware ask flow**

Use retrieval results to build answer context and citation payload while preserving routing/sensitivity/budget traces.

**Step 4: Run tests to verify pass**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service tests.api.test_http_server -q`

**Step 5: Commit**

```bash
git add src/mind_lite/api/service.py tests/api/test_api_service.py tests/api/test_http_server.py
git commit -m "feat: integrate ask endpoint with grounded RAG citations"
```

---

### Task 10: Documentation and full verification

**Files:**
- Modify: `API.md`
- Modify: `ARCHITECTURE.md`
- Modify: `README.md`

**Step 1: Update docs with RAG runtime setup and endpoints**

Document:
- Qdrant dependency and env config
- new `/rag/*` endpoints
- `/ask` citation behavior

**Step 2: Run full test suites**

Run:
`PYTHONPATH=src python3 -m unittest discover -q`

Run:
`cd obsidian-plugin && npm run verify`

**Step 3: Commit**

```bash
git add API.md ARCHITECTURE.md README.md
git commit -m "docs: document full RAG architecture and grounded ask flow"
```

---

## Final Verification

```bash
PYTHONPATH=src python3 -m unittest discover -q
cd obsidian-plugin && npm run verify
```

Expected:
- Backend tests pass with new RAG coverage
- Plugin tests/build still pass
- `/ask` returns citation-backed answers after indexing
