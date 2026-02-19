# RAG Full Architecture Design

## Goal

Implement a full retrieval-augmented generation stack for Mind Lite: indexing, vector retrieval, provenance-backed citations, and `/ask` integration.

## Scope

- Qdrant vector storage for semantic retrieval
- SQLite metadata/chunk store for provenance and traceability
- Local embedding pipeline and chunking
- Retrieval endpoints and indexing endpoints
- `/ask` integration with real citations

Out of scope for this slice:

- Hybrid retrieval rerank models beyond simple scoring
- Multi-tenant or distributed deployment
- Advanced dashboard UI for retrieval analytics

---

## Architecture Overview

Mind Lite will use a split storage model:

- **SQLite** as source-of-truth for documents/chunks/provenance
- **Qdrant** for vector similarity search over chunk embeddings

Pipeline:

1. Vault content ingestion (full or folder-scoped)
2. Chunking (512-1024 token targets with overlap)
3. Embedding generation (`sentence-transformers` local)
4. Qdrant upsert + SQLite metadata persistence
5. Query retrieval for `/ask` and `/rag/retrieve`
6. Citation assembly from stored chunk metadata

---

## Data Model

### SQLite Tables

#### `documents`

- `doc_id` (primary key)
- `path`
- `title`
- `folder`
- `content_hash`
- `updated_at`

#### `chunks`

- `chunk_id` (primary key)
- `doc_id` (foreign key to documents)
- `chunk_index`
- `text`
- `token_count`
- `start_offset`
- `end_offset`
- `heading`
- `updated_at`

#### `ingestion_runs`

- `run_id`
- `scope` (`vault` or `folder`)
- `status`
- `indexed_docs`
- `indexed_chunks`
- `errors`
- `started_at`
- `finished_at`

### Qdrant Payload

- point id: `chunk_id`
- vector: embedding
- payload:
  - `doc_id`
  - `path`
  - `heading`
  - `chunk_index`
  - `content_hash`

Consistency strategy:

- Stable IDs derived from document path + chunk index
- Reindex compares hashes and removes stale chunks
- SQLite authoritative for source text and offsets

---

## API Changes

### New Endpoints

- `POST /rag/index-vault`
  - index all markdown content from configured vault path
- `POST /rag/index-folder`
  - index one folder path incrementally
- `GET /rag/status`
  - counts, last ingestion status, provider readiness
- `POST /rag/retrieve`
  - retrieve top-k chunks for a query with provenance

### Updated Endpoint

- `POST /ask`
  - retrieval-first answer generation
  - returns real citations from retrieved chunks
  - retains existing routing/sensitivity/budget traces

Failure mode contract:

- If retrieval index unavailable, return explicit retrieval error/degraded response
- Never fabricate citations

---

## Retrieval and Answering Flow

1. Accept query (`/ask`)
2. Embed query locally
3. Query Qdrant for top-k candidate chunks
4. Hydrate full chunk text and metadata from SQLite
5. Build grounded context window
6. Generate answer through existing provider routing policy
7. Return:
   - answer text
   - citations (`note_id/path/excerpt/chunk_id/score`)
   - provider trace
   - retrieval trace (`top_k`, latency, candidate count)

---

## Reliability and Safety

- Idempotent indexing behavior for repeated runs
- Deterministic stale-chunk cleanup on reindex
- Preserve existing run lifecycle and rollback architecture
- Keep routing policy gates active for answer generation

---

## Testing Strategy

### Unit

- chunking boundaries/overlap
- embedding adapter contract (shape, error handling)
- SQLite repository CRUD + dedupe/stale cleanup
- Qdrant adapter upsert/search/delete behavior (mock where needed)

### API

- `/rag/index-vault`, `/rag/index-folder`, `/rag/status`, `/rag/retrieve`
- `/ask` returns real citations after indexing
- degraded behavior when index not ready

### Integration

- tiny fixture vault -> index -> retrieve -> ask -> citations verified

---

## Acceptance Criteria

- End-to-end indexing succeeds for fixture vault
- `/rag/retrieve` returns ranked chunks with provenance
- `/ask` returns non-empty citations from indexed content
- Reindex updates changed files and removes stale chunks
- Existing policy tests remain green
