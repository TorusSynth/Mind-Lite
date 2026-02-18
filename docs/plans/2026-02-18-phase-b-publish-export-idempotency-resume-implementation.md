# Phase B Publish Export Idempotency Resume Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete idempotency replay behavior for publish export so duplicate export requests with the same `event_id` return a stable cached response.

**Architecture:** Extend the existing replay-ledger pattern in `ApiService` to `export_for_gom`, mirroring `ask`, `links_apply`, `mark_for_gom`, and `confirm_gom`. Persist replay cache in file-backed mode using a dedicated `publish_export_replay` key, then verify behavior in service-level and HTTP-level restart tests.

**Tech Stack:** Python 3 standard library, `unittest`, `http.server`

---

### Task 1: Define failing service tests for export idempotency

**Files:**
- Modify: `tests/api/test_api_service.py`

**Step 1: Write failing test for duplicate replay**

Add a test that:
- queues one draft with `mark_for_gom`
- calls `export_for_gom` with `event_id="evt_export_001"`
- calls `export_for_gom` again with same `event_id` but different payload values
- asserts second response has `idempotency.duplicate == True` and preserves first artifact/result

**Step 2: Write failing state persistence test**

Add a test in the existing state-file block that:
- creates service with state file
- queues draft
- exports with `event_id`
- creates a second service with same state file
- replays same `event_id`
- asserts duplicate replay and same export artifact

**Step 3: Run targeted tests to verify red**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_export_for_gom_replays_same_response_for_duplicate_event_id tests.api.test_api_service.ApiServiceStatePersistenceTests.test_persists_publish_export_idempotency_replay_cache_to_state_file -q`
Expected: FAIL due missing export idempotency behavior.

---

### Task 2: Implement export replay in ApiService

**Files:**
- Modify: `src/mind_lite/api/service.py`

**Step 1: Add replay state fields in constructor**

Add:
- `self._publish_export_replay_ledger = RunReplayLedger()`
- `self._publish_export_response_by_event: dict[str, dict] = {}`

**Step 2: Add duplicate replay branch in `export_for_gom`**

Implement:
- optional `event_id` validation/normalization
- replay ledger check using namespace `publish_export`
- duplicate return from cached response with idempotency metadata

**Step 3: Add idempotency metadata to successful export responses**

Set:
- `event_id`
- `duplicate` (`False` on first call)
- `reason` (`accepted` when event provided, else `not_provided`)

Cache response by `event_id` and persist state when applicable.

**Step 4: Persist and reload export replay cache**

Update:
- `_load_state_if_present()` to import `publish_export_replay`
- `_persist_state()` to include `publish_export_replay`

Rebuild replay ledger from loaded keys in sorted order (same pattern as other replay caches).

**Step 5: Run targeted service tests to verify green**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_export_for_gom_replays_same_response_for_duplicate_event_id tests.api.test_api_service.ApiServiceStatePersistenceTests.test_persists_publish_export_idempotency_replay_cache_to_state_file -q`
Expected: PASS.

---

### Task 3: Define failing HTTP server tests for export replay

**Files:**
- Modify: `tests/api/test_http_server.py`

**Step 1: Add duplicate event replay endpoint test**

Add a test that:
- enqueues a draft through `/publish/mark-for-gom`
- calls `/publish/export-for-gom` with `event_id="evt_export_001"`
- repeats call with same `event_id` and changed payload data
- asserts second response returns `duplicate == true` and original export payload

**Step 2: Add state-file restart persistence endpoint test**

Add a restart test in the existing persistence section that:
- starts server with `MIND_LITE_STATE_FILE`
- exports with `event_id`
- restarts server with same state file
- replays same `event_id`
- asserts replayed duplicate response

**Step 3: Run targeted HTTP tests to verify red/green path**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_http_server.HttpServerTests.test_export_for_gom_endpoint_replays_duplicate_event_id tests.api.test_http_server.HttpServerTests.test_persists_publish_export_idempotency_replay_across_server_restarts -q`
Expected: PASS after service implementation is complete.

---

### Task 4: Update implementation status docs

**Files:**
- Modify: `API.md`
- Modify: `ARCHITECTURE.md`

**Step 1: Add status bullets for export idempotency replay**

Update Phase A/implementation status entries to include:
- publish export idempotency replay behavior implementation location
- publish export replay persistence implementation location

**Step 2: Verify full suite**

Run: `PYTHONPATH=src python3 -m unittest discover -q`
Expected: PASS.

---

### Task 5: Prepare commit sequence (do not execute unless requested)

**Files:**
- Stage from prior tasks only

**Step 1: Tests commit plan**

```bash
git add tests/api/test_api_service.py tests/api/test_http_server.py
git commit -m "test: define failing publish export idempotency workflow"
```

**Step 2: Implementation commit plan**

```bash
git add src/mind_lite/api/service.py
git commit -m "feat: add publish export idempotency replay handling"
```

**Step 3: Docs commit plan**

```bash
git add API.md ARCHITECTURE.md
git commit -m "docs: record publish export idempotency status"
```

---

## Guardrails

- Keep endpoint contracts backward-compatible.
- Do not change export format semantics.
- Follow existing replay behavior conventions for response shape and reasons.
- Keep changes scoped to export idempotency and associated docs/tests.
