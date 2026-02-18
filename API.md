# Mind Lite - API Specification v2.0 (Planning)

**Status:** Initial Implementation In Progress  
**Last Updated:** 2026-02-18  
**Base URL (target):** `http://localhost:8000`

---

## Purpose

This API spec defines planned behavior for Mind Lite v1, aligned with the approved architecture and roadmap.

Implementation has started with a runnable local HTTP bootstrap and contract-backed onboarding analysis.

---

## Phase A Implementation Status

- Action-tiering contract implemented in `src/mind_lite/contracts/action_tiering.py`
- Contract tests implemented in `tests/contracts/test_action_tiering_policy.py`
- Read-only onboarding analysis contract implemented in `src/mind_lite/onboarding/analyze_readonly.py`
- Contract tests implemented in `tests/onboarding/test_analyze_readonly.py`
- Run lifecycle transition contract implemented in `src/mind_lite/contracts/run_lifecycle.py`
- Contract tests implemented in `tests/contracts/test_run_lifecycle_policy.py`
- Sensitivity gate cloud-eligibility contract implemented in `src/mind_lite/contracts/sensitivity_gate.py`
- Contract tests implemented in `tests/contracts/test_sensitivity_gate_policy.py`
- Budget guardrails contract implemented in `src/mind_lite/contracts/budget_guardrails.py`
- Contract tests implemented in `tests/contracts/test_budget_guardrails_policy.py`
- Snapshot rollback contract implemented in `src/mind_lite/contracts/snapshot_rollback.py`
- Contract tests implemented in `tests/contracts/test_snapshot_rollback_policy.py`
- Provider routing fallback contract implemented in `src/mind_lite/contracts/provider_routing.py`
- Contract tests implemented in `tests/contracts/test_provider_routing_policy.py`
- Idempotency replay contract implemented in `src/mind_lite/contracts/idempotency_replay.py`
- Contract tests implemented in `tests/contracts/test_idempotency_replay_policy.py`
- Rollback validation invariants contract implemented in `src/mind_lite/contracts/rollback_validation.py`
- Contract tests implemented in `tests/contracts/test_rollback_validation_policy.py`
- Runnable HTTP bootstrap implemented in `src/mind_lite/api/http_server.py`
- API service core implemented in `src/mind_lite/api/service.py`
- Run proposal listing and apply workflow implemented in `src/mind_lite/api/service.py`
- Run proposal approval workflow implemented in `src/mind_lite/api/service.py`
- Run rollback workflow implemented in `src/mind_lite/api/service.py`
- Run history listing implemented in `src/mind_lite/api/service.py`
- Sensitivity cloud-eligibility check endpoint implemented in `src/mind_lite/api/service.py`
- Sensitivity policy summary endpoint implemented in `src/mind_lite/api/service.py`
- Routing policy summary endpoint implemented in `src/mind_lite/api/service.py`
- Ask endpoint with policy-gated provider routing implemented in `src/mind_lite/api/service.py`
- Readiness endpoint implemented in `src/mind_lite/api/service.py`
- Prometheus-style metrics endpoint implemented in `src/mind_lite/api/service.py`
- Publish preparation endpoint implemented in `src/mind_lite/api/service.py`
- Publish scoring endpoint implemented in `src/mind_lite/api/service.py`
- Publish queue enqueue endpoint implemented in `src/mind_lite/api/service.py`
- Publish queue listing endpoint implemented in `src/mind_lite/api/service.py`
- Publish export endpoint implemented in `src/mind_lite/api/service.py`
- Publish confirmation endpoint implemented in `src/mind_lite/api/service.py`
- Published listing endpoint implemented in `src/mind_lite/api/service.py`
- Organize classify endpoint implemented in `src/mind_lite/api/service.py`
- Links propose endpoint implemented in `src/mind_lite/api/service.py`
- Links apply endpoint implemented in `src/mind_lite/api/service.py`
- Organize propose-structure endpoint implemented in `src/mind_lite/api/service.py`
- Optional file-backed API state persistence implemented in `src/mind_lite/api/service.py`
- HTTP server state-file wiring implemented in `src/mind_lite/api/http_server.py`

---

## Runnable Endpoints (Current)

- `GET /health`
- `GET /health/ready`
- `GET /metrics`
- `GET /runs`
- `GET /policy/sensitivity`
- `GET /policy/routing`
- `GET /publish/gom-queue`
- `GET /publish/published`
- `POST /onboarding/analyze-folder`
- `POST /organize/classify`
- `POST /organize/propose-structure`
- `POST /links/propose`
- `POST /links/apply`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/proposals`
- `POST /runs/{run_id}/approve`
- `POST /runs/{run_id}/apply`
- `POST /runs/{run_id}/rollback`
- `POST /policy/sensitivity/check`
- `POST /ask`
- `POST /publish/prepare`
- `POST /publish/score`
- `POST /publish/mark-for-gom`
- `POST /publish/export-for-gom`
- `POST /publish/confirm-gom`

Run locally with:

`PYTHONPATH=src python3 -m mind_lite.api`

Persist state across restarts with:

`MIND_LITE_STATE_FILE=.mind_lite/state.json PYTHONPATH=src python3 -m mind_lite.api`

---

## Scope

### In Scope

- Endpoint behavior contracts for v1 planning baseline
- Run lifecycle and proposal workflow operations
- Local-first routing, cloud fallback gate, and editorial gate surfaces

### Out of Scope

- Internal implementation details (see `ARCHITECTURE.md`)
- Capability sequencing and delivery order (see `ROADMAP.md`)
- Future provider expansions beyond v1 fallback policy

---

## Core Design Rules

- Local-first provider routing
- Explicit human review for structural actions
- Policy-gated cloud fallback (OpenAI only in v1)
- Batch-safe operations with rollback support
- Obsidian compatibility preservation

Terminology alignment:

- **Hybrid automation** uses risk-tiered action modes (`auto`, `suggest`, `manual`)
- **Cloud fallback gate** allows non-local provider use only when triggers pass policy
- **Editorial gate** blocks publication until quality and safety requirements pass

---

## Common Enums

### Risk Tier
- `low`
- `medium`
- `high`

### Action Mode
- `auto`
- `suggest`
- `manual`

### Provider
- `local`
- `openai`

### Run State
- `queued`
- `analyzing`
- `ready_safe_auto`
- `awaiting_review`
- `approved`
- `applied`
- `verified`
- `auto_safe_mode`
- `rolled_back`
- `failed_needs_attention`

---

## Health and System

### GET `/health`
Service health status.

### GET `/health/ready`
Readiness checks for dependencies.

### GET `/metrics`
Prometheus-compatible metrics.

---

## Onboarding and Run Management

### POST `/onboarding/analyze-folder`
Analyze folder in read-only mode.

Request:
```json
{
  "folder_path": "Projects/Atlas",
  "mode": "analyze",
  "batch_size": 50
}
```

Response:
```json
{
  "run_id": "run_abc123",
  "state": "analyzing",
  "profile": {
    "note_count": 46,
    "orphan_notes": 19,
    "link_density": 0.24
  }
}
```

### GET `/runs/{run_id}`
Get run state, diagnostics, and proposal counts.

### GET `/runs/{run_id}/proposals`
List change proposals for this run.

Filters:
- `risk_tier`
- `action_mode`
- `status`

### POST `/runs/{run_id}/approve`
Approve proposals by change type.

Request:
```json
{
  "change_types": ["tag_enrichment", "link_add"],
  "scope": "all_visible"
}
```

### POST `/runs/{run_id}/apply`
Apply approved proposals and create snapshot.

### POST `/runs/{run_id}/rollback`
Rollback last applied batch for run.

---

## Organization and PARA

### POST `/organize/classify`
Classify notes with primary and secondary PARA labels.

Request:
```json
{
  "note_ids": ["note_1", "note_2"]
}
```

Response:
```json
{
  "results": [
    {
      "note_id": "note_1",
      "primary_para": "project",
      "secondary_para": ["resource"],
      "confidence": 0.83,
      "action_mode": "auto"
    }
  ]
}
```

### POST `/organize/propose-structure`
Generate move/retitle/merge suggestions (never auto-applied in v1).

---

## Linking and Retrieval

### POST `/links/propose`
Generate link suggestions with confidence scores.

### POST `/links/apply`
Apply approved link proposals.

### POST `/ask`
Ask a question with provider-aware routing.

Request:
```json
{
  "query": "What should I work on next?",
  "provider": "local",
  "allow_fallback": true,
  "top_k": 5
}
```

Response:
```json
{
  "answer": {
    "text": "Focus on Project Atlas onboarding tasks...",
    "citations": [
      {
        "note_id": "note_32",
        "excerpt": "..."
      }
    ],
    "confidence": 0.79
  },
  "provider_trace": {
    "initial": "local",
    "fallback_used": true,
    "fallback_provider": "openai",
    "fallback_reason": "low_confidence"
  }
}
```

---

## Privacy and Routing Policy

### GET `/policy/routing`
Return active routing thresholds and budget state.

### GET `/policy/sensitivity`
Return active sensitivity rules summary.

### POST `/policy/sensitivity/check`
Check whether payload is cloud-eligible.

---

## Publishing (Mind Lite -> GOM)

### POST `/publish/prepare`
Prepare draft for GOM scoring and sanitization.

### POST `/publish/score`
Run editorial rubric scoring.

### POST `/publish/mark-for-gom`
Mark draft as publish candidate.

### GET `/publish/gom-queue`
List queued publish candidates.

### GET `/publish/published`
List published drafts with final URLs.

### POST `/publish/export-for-gom`
Export markdown/html/json after gate pass.

### POST `/publish/confirm-gom`
Confirm publication status and URL.

---

## Error Format

```json
{
  "error": {
    "type": "ValidationError",
    "message": "Human-readable message",
    "details": {
      "field": "value"
    }
  }
}
```

---

## Notes on Implementation Status

- This contract is intentionally more focused than v1.0 docs.
- Endpoints may be expanded during build, but core policy behavior is considered locked.
- Any contract-breaking changes require documentation review before coding.

---

## Read Next

1. `ARCHITECTURE.md` for component boundaries behind these endpoints
2. `ROADMAP.md` for capability phase progression
3. `docs/specs/provenance-lineage-contract.md` for source and traceability guarantees
