# Phase B Batch Folder Operations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add batch onboarding analysis so one request can analyze multiple folders and return a parent run with per-folder batch progress.

**Architecture:** Introduce a parent-run orchestration method in `ApiService` that loops existing single-folder analysis behavior and records child summaries in `batches`. Keep `analyze_folder` endpoint and behavior unchanged, add a dedicated `analyze_folders` service/API path, and compute parent terminal state deterministically from child outcomes.

**Tech Stack:** Python 3, standard library `unittest`, existing HTTP server and service contracts

---

### Task 1: Define failing service tests for batch analyze behavior

**Files:**
- Modify: `tests/api/test_api_service.py`

**Step 1: Write failing success-path batch test**

Add test:
- `test_analyze_folders_creates_parent_run_with_batch_entries`
- payload includes two valid folders
- assert parent response contains `batch_total`, `batch_completed`, and `batches` entries

```python
def test_analyze_folders_creates_parent_run_with_batch_entries(self):
    result = service.analyze_folders({"folder_paths": [str(a), str(b)], "mode": "analyze"})
    self.assertEqual(result["batch_total"], 2)
```

**Step 2: Write failing partial/all-failure tests**

Add tests:
- `test_analyze_folders_handles_partial_child_failures`
- `test_analyze_folders_sets_failed_needs_attention_when_all_children_fail`

**Step 3: Write failing payload validation test**

Add test:
- `test_analyze_folders_rejects_invalid_folder_paths_payload`

**Step 4: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_analyze_folders_creates_parent_run_with_batch_entries tests.api.test_api_service.ApiServiceTests.test_analyze_folders_handles_partial_child_failures tests.api.test_api_service.ApiServiceTests.test_analyze_folders_sets_failed_needs_attention_when_all_children_fail tests.api.test_api_service.ApiServiceTests.test_analyze_folders_rejects_invalid_folder_paths_payload -q`
Expected: FAIL before implementation.

---

### Task 2: Implement batch orchestration in ApiService

**Files:**
- Modify: `src/mind_lite/api/service.py`

**Step 1: Add `analyze_folders(payload)` entrypoint**

Implement payload validation:
- require `folder_paths` as non-empty list[str]

Initialize parent run:
- parent `run_id`
- state `queued -> analyzing`
- `batch_total`, `batch_completed`, `batches`, `diagnostics`

**Step 2: Add child-batch execution helper**

Create private helper that runs existing single-folder analyze internals and returns summary:
- `folder_path`, `run_id`, `state`, `proposal_count`, `diagnostics_count`

Keep helper deterministic and reuse existing run/proposal generation logic.

**Step 3: Add parent state aggregation**

Aggregate child outcomes:
- all failed -> `failed_needs_attention`
- any `ready_safe_auto` and not all failed -> `ready_safe_auto`
- otherwise -> `awaiting_review`

Use existing lifecycle transition helper for transitions.

**Step 4: Persist parent run and return summary payload**

Ensure parent run is stored in `_runs` and queryable by `get_run`/`list_runs`.

**Step 5: Run targeted service tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service -q`
Expected: PASS.

---

### Task 3: Add HTTP endpoint and endpoint tests

**Files:**
- Modify: `src/mind_lite/api/http_server.py`
- Modify: `tests/api/test_http_server.py`

**Step 1: Write failing HTTP tests**

Add tests:
- `test_analyze_folders_endpoint_returns_parent_batch_summary`
- `test_analyze_folders_endpoint_handles_partial_failures`
- `test_analyze_folders_endpoint_rejects_invalid_payload`

**Step 2: Run red HTTP tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_http_server.HttpServerTests.test_analyze_folders_endpoint_returns_parent_batch_summary tests.api.test_http_server.HttpServerTests.test_analyze_folders_endpoint_handles_partial_failures tests.api.test_http_server.HttpServerTests.test_analyze_folders_endpoint_rejects_invalid_payload -q`
Expected: FAIL before route implementation.

**Step 3: Implement endpoint mapping**

In `http_server.py` add route:
- `POST /onboarding/analyze-folders` -> `service.analyze_folders(body)`
- return `400` on `ValueError`

**Step 4: Run HTTP module tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_http_server -q`
Expected: PASS.

---

### Task 4: Update API docs for batch endpoint

**Files:**
- Modify: `API.md`
- Modify: `ARCHITECTURE.md`

**Step 1: Add implementation status bullets**

Document:
- batch folder onboarding endpoint and service implementation location
- parent batch summary fields and staged state aggregation behavior

**Step 2: Add endpoint contract section**

In `API.md` add:
- `POST /onboarding/analyze-folders` request/response shape
- key fields: `batch_total`, `batch_completed`, `batches`, parent `state`

**Step 3: Verify docs consistency**

Run: `PYTHONPATH=src python3 -m unittest discover -q`
Expected: PASS.

---

### Task 5: Full verification and commit sequence

**Files:**
- Stage only files changed by this plan

**Step 1: Full test verification**

Run: `PYTHONPATH=src python3 -m unittest discover -q`
Expected: PASS.

**Step 2: Commit tests**

```bash
git add tests/api/test_api_service.py tests/api/test_http_server.py
git commit -m "test: define batch onboarding folder workflow"
```

**Step 3: Commit implementation**

```bash
git add src/mind_lite/api/service.py src/mind_lite/api/http_server.py
git commit -m "feat: add batch onboarding folder analysis"
```

**Step 4: Commit docs**

```bash
git add API.md ARCHITECTURE.md
git commit -m "docs: record batch onboarding operations status"
```

---

## Guardrails

- Keep single-folder endpoint behavior unchanged.
- Preserve lifecycle validation on all state transitions.
- Keep per-folder failures isolated; do not fail-fast entire batch.
- Avoid introducing async/queue complexity in this slice.
