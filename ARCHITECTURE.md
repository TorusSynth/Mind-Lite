# Mind Lite - Technical Architecture v2.0

**Status:** Implementation Active  
**Last Updated:** 2026-02-19

---

## Architecture Goal

Deliver a trustworthy second brain workflow for Obsidian vaults by combining safe automation, human review, local-first AI, and quality-gated publishing.

---

## Purpose

This document defines the system boundaries and major engines for Mind Lite v1. It translates roadmap capabilities into component responsibilities.

---

## Implementation Status (Phases A-F)

Canonical endpoint-level implementation status is maintained in `API.md`.

Architecture-level milestones completed:

- Core policy contracts implemented and covered (action tiering, lifecycle, routing, budget, rollback, idempotency)
- Runnable HTTP API with file-backed state persistence implemented
- Onboarding read-only analysis extended with note-level profiles and LLM proposal normalization
- Onboarding staged run outcomes implemented (`ready_safe_auto`, `awaiting_review`, `failed_needs_attention`)
- Analyze-folders batch onboarding endpoint/service implemented with parent run orchestration
- Analyze-folders parent batch summary counters and aggregate state transitions implemented (`batch_total`, `batch_completed`, `batches`, final `state`)
- Batch checkpoint snapshot tracking per applied child run (`snapshot_id`, `applied_batch_ids`) implemented
- Lifecycle-validated state transitions enforced for analyze/approve/apply paths
- Full `PYTHONPATH=src python3 -m unittest discover -q` verification passed after staged onboarding transitions
- **Phase C: LLM Integration for Organization and Links**
  - PARA classification LLM module (`organize/classify_llm.py`) with prompt building and response parsing
  - Link scoring LLM module (`links/propose_llm.py`) with anti-spam controls
  - Graceful degradation on LLM failure with safe defaults
- **Phase E: Obsidian UX and review workflow**
  - Obsidian plugin command surface implemented for analyze, review, apply, rollback, links, triage, deep review, and publish flows
  - Review and run operations implemented with dedicated modals (`ReviewModal`, `RunHistoryModal`, `RollbackModal`, publish gate modals)
  - Daily triage and weekly deep review workflows implemented on top of onboarding/run history endpoints
  - Plugin API client currently targets local API only at `http://localhost:8000`
- **Phase F: Editorial gate hardening**
  - Editorial gate checks hardened for publish readiness (metadata, sanitization, sensitivity/grounding hard-fails, stage thresholds)
  - Revision queue and publish queue separation enforced in gate outcomes and plugin publish-review flow
  - Revision queue status surfaced as an explicit "needs revision" path before publish eligibility
- **RAG: Full Architecture Implementation**
  - Configuration module with environment-backed defaults (`src/mind_lite/rag/config.py`)
  - Deterministic chunking with stable IDs from path + index + content hash (`src/mind_lite/rag/chunking.py`)
  - SQLite provenance store for documents, chunks, and ingestion runs (`src/mind_lite/rag/sqlite_store.py`)
  - Local embedding adapter wrapping sentence-transformers (`src/mind_lite/rag/embeddings.py`)
  - Qdrant vector index adapter for collection management and search (`src/mind_lite/rag/vector_index.py`)
  - Ingestion service coordinating chunking, embeddings, and vector storage (`src/mind_lite/rag/indexing.py`)
  - Retrieval service with citation assembly from SQLite + Qdrant (`src/mind_lite/rag/retrieval.py`)
  - `/ask` endpoint integrated with retrieval-backed citations and graceful degradation

---

## Scope

### In Scope

- Component-level responsibilities and interfaces
- Run lifecycle and failure states
- Routing, privacy, and editorial gate behavior at system level

### Out of Scope

- Endpoint request/response contracts (see `API.md`)
- Phase sequencing details (see `ROADMAP.md`)
- Step-by-step build tasks (see `docs/plans/`)

---

## Terminology Contract

- **Hybrid automation** = low-risk auto + medium-risk suggest + high-risk manual
- **Local-first routing** = LM Studio default for model execution
- **Cloud fallback gate** = OpenAI fallback only when policy triggers are met
- **Editorial gate** = quality and safety checks before GOM publication

---

## System Overview

```
Obsidian Plugin (Primary UX)
    -> API Layer (FastAPI)
        -> Onboarding and Organization Engine
        -> Linking and Retrieval Engine
        -> Routing and Privacy Engine
        -> Publishing and Editorial Gate Engine
        -> Safety and Audit Engine
            -> Storage Layer (notes, proposals, run logs, snapshots, vectors)
```

---

## Core Components

## 1) Obsidian UX Layer

Provides command-first operations:

- Analyze Current Folder
- Run Safe Auto Pass
- Review Structural Suggestions
- Apply Approved Changes
- Roll Back Last Batch
- Daily Triage
- Weekly Deep Review
- Prepare GOM Draft
- Publish to GOM (After Gate)

UI includes grouped review by change type, diff previews, run states, and diagnostics.

---

## 2) Onboarding and Organization Engine

Responsibilities:

- Folder-based onboarding runs
- Note profiling and confidence scoring
- PARA assignment (primary + secondary)
- Action tiering:
  - low-risk auto (`>=0.80`)
  - medium-risk suggest (`>=0.70`)
  - high-risk manual

Design requirement: no destructive operations during onboarding.

---

## 3) Linking and Retrieval Engine

Responsibilities:

- Generate link proposals for graph improvement
- Prevent link spam via limits and relevance thresholds
- Serve retrieval and RAG-based answering with citations

Graph quality is evaluated via orphan reduction, acceptance rate, and false-link rate.

---

## 4) Routing and Privacy Engine

### Model Routing

- Default provider: LM Studio (local)
- Fallback provider (v1): OpenAI
- Fallback triggers: low confidence, timeout, or grounding failure

### Privacy Gate

Hybrid sensitive detector checks:

- Frontmatter flags
- Tags
- Path rules
- Regex patterns

If blocked, request stays local-only.

### Cost Guardrails

- Monthly cloud cap: $30
- Warnings at 70% and 90%
- Hard stop at 100% with local-only continuation

---

## 5) Publishing and Editorial Gate Engine

Responsibilities:

- Manage publish queue and revision queue
- Score drafts with weighted rubric
- Apply hard-fail checks (sensitivity, grounding, metadata)
- Enforce stage thresholds (`seed`, `sprout`, `tree`)

Nothing reaches GOM without passing gate checks.

---

## 6) Safety and Audit Engine

Responsibilities:

- Snapshot before apply
- Rollback last batch
- Idempotency guards
- Run lifecycle tracking and audit logs

Run states:

`queued -> analyzing -> ready_safe_auto -> awaiting_review -> approved -> applied -> verified`

Failure states:

`auto_safe_mode`, `rolled_back`, `failed_needs_attention`

---

## Data Objects

- **Note** - markdown content + metadata
- **Change Proposal** - action, risk tier, confidence, rationale, status
- **Run Record** - run ID, scope, provider decisions, diagnostics
- **Snapshot** - rollback checkpoint for applied batch
- **Query Result** - answer + citations + provider trace
- **Publish Artifact** - gated content + stage + export status

---

## Reliability Rules

- Obsidian compatibility is non-negotiable
- Re-runs must be idempotent
- Repeated quality failures trigger auto-safe mode
- Structural changes require human approval

---

## Out of Scope (V1)

- Multi-device sync
- Multi-user auth and collaboration
- Autonomous unattended agents
- Multi-cloud provider orchestration
- Full GOM hosting automation

---

## Build Path

Implementation follows capability phases defined in `ROADMAP.md`.

Coding started after documentation approval and now proceeds by capability phase.

---

## Read Next

1. `API.md` for endpoint-level behavior contracts
2. `ROADMAP.md` for capability sequencing and exit criteria
3. `docs/specs/threat-model-v1.md` for policy-level risk controls
