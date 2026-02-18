# Phase B Staged Onboarding Run States Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement deterministic staged onboarding run transitions so analyze/approve/apply operations enforce lifecycle state rules.

**Architecture:** Add a small transition helper in `ApiService` that validates and applies state changes using `run_lifecycle` contract rules. Route onboarding run state mutations through this helper, then update tests to verify staged outcomes and invalid-transition failures.

**Tech Stack:** Python 3, standard library `unittest`, existing lifecycle contracts

---

### Task 1: Add failing service tests for staged analyze outcomes

**Files:**
- Modify: `tests/api/test_api_service.py`

**Step 1: Write failing test for `ready_safe_auto` analyze result**

Add a test asserting analyze returns `ready_safe_auto` when auto-mode proposals are present.

```python
def test_analyze_folder_sets_ready_safe_auto_when_auto_proposals_exist(self):
    run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
    self.assertEqual(run["state"], "ready_safe_auto")
```

**Step 2: Write failing test for `awaiting_review` analyze result**

Add a test that stubs proposal generation so only `suggest`/`manual` actions exist and asserts run ends in `awaiting_review`.

**Step 3: Run targeted red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_analyze_folder_sets_ready_safe_auto_when_auto_proposals_exist tests.api.test_api_service.ApiServiceTests.test_analyze_folder_sets_awaiting_review_when_no_auto_proposals -q`
Expected: FAIL before implementation.

---

### Task 2: Implement transition helper and analyze staged states

**Files:**
- Modify: `src/mind_lite/api/service.py`

**Step 1: Add transition helper using lifecycle contract**

Implement a private helper such as:

```python
def _transition_run_state(self, run: dict, target: str) -> None:
    current = RunState(run["state"])
    target_state = RunState(target)
    if not validate_transition(current, target_state):
        raise ValueError(f"invalid run state transition: {current.value} -> {target_state.value}")
    run["state"] = target_state.value
```

**Step 2: Update `analyze_folder` staged state progression**

Apply transitions in sequence:
- initialize as `queued`
- transition to `analyzing`
- final success state:
  - `ready_safe_auto` if any proposal has `action_mode == "auto"`
  - else `awaiting_review`
- retain `failed_needs_attention` for all-fail diagnostics path

**Step 3: Keep empty-folder behavior**

For `note_count == 0`, keep proposals empty and set `awaiting_review`.

**Step 4: Run targeted tests to green**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_analyze_folder_sets_ready_safe_auto_when_auto_proposals_exist tests.api.test_api_service.ApiServiceTests.test_analyze_folder_sets_awaiting_review_when_no_auto_proposals tests.api.test_api_service.ApiServiceTests.test_analyze_folder_empty_directory_returns_no_proposals -q`
Expected: PASS.

---

### Task 3: Enforce staged transitions in approve/apply with tests

**Files:**
- Modify: `tests/api/test_api_service.py`
- Modify: `src/mind_lite/api/service.py`

**Step 1: Write failing tests for invalid source states**

Add tests asserting:
- `approve_run` fails when run is not in `awaiting_review` or `ready_safe_auto`
- `apply_run` fails when run is not in `approved`

**Step 2: Write passing-path staged flow test**

Add test for valid progression: `analyze_folder -> approve_run -> apply_run`.

**Step 3: Run red/green targeted tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_approve_run_rejects_invalid_run_state tests.api.test_api_service.ApiServiceTests.test_apply_run_rejects_invalid_run_state tests.api.test_api_service.ApiServiceTests.test_staged_run_progression_analyze_approve_apply -q`
Expected: FAIL before changes, PASS after changes.

**Step 4: Implement minimal state checks**

In service:
- call `_transition_run_state` in `approve_run` (to `approved`)
- call `_transition_run_state` in `apply_run` (to `applied`)

---

### Task 4: Add HTTP-level transition behavior tests

**Files:**
- Modify: `tests/api/test_http_server.py`

**Step 1: Write failing tests for endpoint staged states**

Add tests that assert:
- `/onboarding/analyze-folder` returns `ready_safe_auto` or `awaiting_review` based on proposal actions
- `/runs/{id}/apply` returns `400` if called before approval

**Step 2: Run targeted HTTP tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_http_server.HttpServerTests.test_analyze_folder_endpoint_returns_staged_state tests.api.test_http_server.HttpServerTests.test_apply_endpoint_rejects_unapproved_run_state -q`
Expected: PASS after service changes.

---

### Task 5: Update docs and verify full suite

**Files:**
- Modify: `API.md`
- Modify: `ARCHITECTURE.md`

**Step 1: Document staged onboarding state behavior**

Add status bullets for:
- lifecycle-validated onboarding state transitions in service
- staged analyze outcomes (`ready_safe_auto`, `awaiting_review`, `failed_needs_attention`)

**Step 2: Run full verification**

Run: `PYTHONPATH=src python3 -m unittest discover -q`
Expected: PASS.

**Step 3: Commit plan (when asked)**

```bash
git add tests/api/test_api_service.py tests/api/test_http_server.py src/mind_lite/api/service.py API.md ARCHITECTURE.md
git commit -m "feat: enforce staged onboarding run state transitions"
```

---

## Guardrails

- Do not alter non-onboarding run flows.
- Keep rollback/global failure transitions contract-compatible.
- Preserve existing response shapes unless transition behavior requires state value changes.
