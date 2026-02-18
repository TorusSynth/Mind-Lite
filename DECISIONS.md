# Mind Lite - Architecture Decisions v2.0

**Status:** Active  
**Last Updated:** 2026-02-18

---

## Purpose

This document records key architectural decisions and their rationale. Each decision follows the format:
- **Decision:** What was chosen
- **Context:** Why it matters
- **Rationale:** Why this option over alternatives
- **Consequences:** Tradeoffs and implications

---

## Scope

### In Scope

- Major v1 technical decisions and trade-offs
- Decision rationale and implications for implementation
- ADR log as the canonical reference for accepted choices

### Out of Scope

- Endpoint contract definitions (see `API.md`)
- Delivery sequencing (see `ROADMAP.md`)
- Low-level task implementation details

---

## ADR-001: FastAPI for API Framework

**Decision:** Use FastAPI as the web framework.

**Context:** Need a Python web framework that is fast to develop with, has good async support, and auto-generates documentation.

**Rationale:**
- Native async/await support (important for LLM calls)
- Automatic OpenAPI documentation
- Pydantic integration for validation
- High performance
- Large ecosystem and community

**Alternatives Considered:**
- Flask: Simpler but no native async
- Django: Too heavyweight for a focused API
- Starlette: FastAPI builds on this, adds convenience

**Consequences:**
- Requires Python 3.8+
- Learning curve for dependency injection system
- Well-suited for API-only projects

---

## ADR-002: Qdrant for Vector Storage

**Decision:** Use Qdrant as the vector database.

**Context:** Need efficient similarity search over document chunk embeddings.

**Rationale:**
- Simple to run (single Docker container)
- Good performance for small-to-medium datasets
- Clear API with good Python client
- Supports filtering and metadata
- Active development and community

**Alternatives Considered:**
- Chroma: Simpler but less mature
- Pinecone: Managed, but adds external dependency
- pgvector: Requires PostgreSQL, more setup
- Milvus: Overkill for single-user deployment

**Consequences:**
- Requires running Qdrant container
- Easy to swap later if needed (abstraction layer)
- Well-suited for local-first deployment

---

## ADR-003: SQLite for Document Storage

**Decision:** Use SQLite for document and chunk metadata.

**Context:** Need persistent storage for document records and chunk text.

**Rationale:**
- Zero configuration (single file)
- Sufficient for single-user workload
- Easy to backup (copy file)
- Good enough performance for expected data volume
- Can migrate to PostgreSQL in Phase 2 if needed

**Alternatives Considered:**
- PostgreSQL: More powerful, but adds operational complexity
- MongoDB: Document-oriented, but overkill for structured data

**Consequences:**
- Not suitable for concurrent writes (single-user is fine)
- Limited to single machine
- Easy to inspect with sqlite3 CLI

---

## ADR-004: Sentence-Transformers for Embeddings

**Decision:** Use sentence-transformers with all-MiniLM-L6-v2 as default embedding model.

**Context:** Need semantic embeddings for document chunks and queries.

**Rationale:**
- Runs locally (no API calls, no cost)
- Good quality for general text
- Fast inference (384 dimensions)
- Well-maintained library
- Easy to swap models later

**Alternatives Considered:**
- OpenAI embeddings: Higher quality, but costs and external dependency
- Cohere embeddings: Similar tradeoffs to OpenAI
- Instructor embeddings: More flexible but slower

**Consequences:**
- Requires ~500MB model download on first run
- Quality may be lower than large commercial models
- No network dependency for embeddings

---

## ADR-005: LM Studio as Default, OpenAI as Fallback

**Decision:** Use LM Studio as the default local LLM provider, with OpenAI as guarded fallback.

**Context:** Need an LLM for answer generation and extraction tasks.

**Rationale:**
- Local-first aligns with privacy and cost control goals
- Fast interactive tuning for onboarding and organization workflows
- OpenAI fallback covers hard cases and quality gaps
- Clear policy controls for sensitivity and budget

**Alternatives Considered:**
- OpenAI default: higher consistency, but weaker local-first posture
- Local-only with no fallback: lower cost, but lower resilience on hard tasks
- Multi-cloud failover in v1: stronger resiliency, but unnecessary complexity

**Consequences:**
- Requires local runtime setup (LM Studio)
- Requires OpenAI API key only for fallback paths
- Needs explicit routing policy, sensitivity gate, and budget controls
- Improves portfolio signal for provider orchestration and safety engineering

---

## ADR-006: Chunk Size of 512-1024 Tokens

**Decision:** Use 512-1024 token chunks with 10-20% overlap.

**Context:** Need to split documents into retrievable units.

**Rationale:**
- Balances retrieval precision and context preservation
- Fits within most embedding model context windows
- Overlap prevents losing context at boundaries
- Aligns with common RAG best practices

**Alternatives Considered:**
- Smaller chunks (256): More precise retrieval, but loses context
- Larger chunks (2048): More context, but less precise retrieval
- Semantic chunking: Better but more complex

**Consequences:**
- May miss cross-chunk context
- Works well for most document types
- Can be tuned per document type in Phase 2

---

## ADR-007: Docker Compose for Deployment

**Decision:** Use docker-compose for local development and deployment.

**Context:** Need reproducible deployment with multiple services (API, vector DB).

**Rationale:**
- Simple to set up (single command)
- Works locally and on single server
- Easy to add services incrementally
- Standard tooling, good documentation

**Alternatives Considered:**
- Kubernetes: Overkill for single-user deployment
- Bare metal: Harder to reproduce environment
- Systemd services: Less portable

**Consequences:**
- Requires Docker and docker-compose
- Limited to single host
- Can migrate to Kubernetes in Phase 2 if needed

---

## ADR-008: Structured JSON Logging

**Decision:** Use structured JSON logging for all application logs.

**Context:** Need observable, queryable logs for debugging and monitoring.

**Rationale:**
- Machine-readable format
- Easy to ingest into log aggregators
- Includes context (request_id, timestamps, etc.)
- Standard practice for production systems

**Alternatives Considered:**
- Plain text logging: Simpler but harder to query
- No structured logging: Acceptable for development only

**Consequences:**
- Requires log viewer that supports JSON
- Slightly more verbose output
- Easy to integrate with observability tools

---

## ADR-009: No Authentication in v1

**Decision:** Do not implement authentication or authorization in v1.

**Context:** Mind Lite is designed for single-user, local deployment.

**Rationale:**
- Reduces scope and complexity
- Single user = no multi-tenant concerns
- Can run behind reverse proxy with basic auth if needed
- Authentication is a Phase 2+ concern

**Alternatives Considered:**
- API key auth: Simple but adds configuration
- OAuth: Overkill for single user
- Basic auth: Reasonable, but still adds complexity

**Consequences:**
- Not safe to expose publicly without reverse proxy
- Assume trusted network environment
- Must add auth before any multi-user deployment

---

## ADR-010: Obsidian Plugin as Primary GUI

**Decision:** Build an Obsidian plugin as the primary user interface for Mind Lite.

**Context:** Users need a way to interact with Mind Lite's capabilities. An Obsidian plugin provides native integration with the knowledge base.

**Rationale:**
- You already use Obsidian for notes
- Native Markdown support (no format conversion)
- Plugin ecosystem is mature and well-documented
- Local-first (fits overall architecture)
- Direct vault access for ingestion and publishing
- Better UX than standalone web UI for note workflows

**Alternatives Considered:**
- Standalone web UI: Separate context, more to maintain
- CLI only: Powerful but less accessible
- API only: Requires users to build their own interface

**Consequences:**
- Requires TypeScript knowledge
- Plugin must be installed and configured
- Obsidian version compatibility matters
- Can still use API directly if needed

---

## ADR-011: GOM Publishing Pipeline in v1

**Decision:** Include a GOM publishing pipeline in Mind Lite v1.

**Context:** Users need to export curated content from private notes to GOM (digital garden website).

**Rationale:**
- GOM is the natural output of Mind Lite (private → public)
- GOM is core to the MIND vision (distillation before expression)
- Basic export is low complexity (Markdown/HTML generation)
- Workflow is clear: mark → review → sanitize → export → GOM
- Lays foundation for full GOM website integration in Phase 2

**Alternatives Considered:**
- No publishing in v1: Simpler but incomplete user story
- Full GOM website with static generator: Too complex for v1
- Manual export only: Defeats automation purpose

**Consequences:**
- Adds endpoints and plugin features for GOM
- Requires publication status tracking and privacy safeguards
- Export formats limited to Markdown/HTML in v1
- Full GOM deployment (static site + hosting) is Phase 2

---

## Decision Log

| ID | Date | Decision | Status |
|----|------|----------|--------|
| ADR-001 | 2026-02-17 | FastAPI for API | Accepted |
| ADR-002 | 2026-02-17 | Qdrant for vectors | Accepted |
| ADR-003 | 2026-02-17 | SQLite for storage | Accepted |
| ADR-004 | 2026-02-17 | Sentence-transformers for embeddings | Accepted |
| ADR-005 | 2026-02-18 | LM Studio default, OpenAI fallback | Accepted |
| ADR-006 | 2026-02-17 | 512-1024 token chunks | Accepted |
| ADR-007 | 2026-02-17 | Docker Compose for deployment | Accepted |
| ADR-008 | 2026-02-17 | Structured JSON logging | Accepted |
| ADR-009 | 2026-02-17 | No auth in v1 | Accepted |
| ADR-010 | 2026-02-17 | Obsidian plugin as primary GUI | Accepted |
| ADR-011 | 2026-02-17 | Basic publishing pipeline in v1 | Accepted |

---

## Read Next

1. `ARCHITECTURE.md` for component boundaries that realize these decisions
2. `ROADMAP.md` for phase ordering and capability gates
3. `API.md` for contract-level implications
