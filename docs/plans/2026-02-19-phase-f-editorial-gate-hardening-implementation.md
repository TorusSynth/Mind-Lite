# Phase F Editorial Gate Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enforce stage-aware publish gating and route gate failures to a revision queue without breaking current publish/export flows.

**Architecture:** Extend publish scoring in `ApiService` with stage thresholds and hard-fail evaluation, then add revision-queue endpoints and persistence paths parallel to existing GOM queue handling. Update the Obsidian publish flow to submit stage, display gate diagnostics, and branch to mark-for-gom or mark-for-revision.

**Tech Stack:** Python (`unittest`), existing HTTP server routing, TypeScript Obsidian plugin tests, in-memory/file-backed state persistence.

---

### Task 1: Add failing service tests for stage thresholds

**Files:**
- Modify: `tests/api/test_api_service.py`

**Step 1: Write failing test**

```python
def test_publish_score_uses_stage_thresholds(self):
    service = ApiService()
    result = service.publish_score({"draft_id": "d1", "content": "good content", "stage": "tree"})
    self.assertIn("threshold", result)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_publish_score_uses_stage_thresholds -v`
Expected: FAIL because `stage`/`threshold` contract is not implemented.

**Step 3: Implement minimal service support**

Modify `publish_score` in `src/mind_lite/api/service.py` to require `stage`, validate enum, and include threshold in response.

**Step 4: Run test to verify pass**

Run: same command as Step 2
Expected: PASS.

**Step 5: Commit**

```bash
git add src/mind_lite/api/service.py tests/api/test_api_service.py
git commit -m "feat: enforce stage-aware publish score thresholds"
```

---

### Task 2: Add hard-fail checks and diagnostics in scoring

**Files:**
- Modify: `src/mind_lite/api/service.py`
- Modify: `tests/api/test_api_service.py`

**Step 1: Write failing tests for hard-fail precedence**

Add tests that verify `gate_passed` is false when:
- safety score floor violated
- TODO marker policy triggered
- required fields missing

and verify response includes:
- `hard_fail_reasons`
- `recommended_actions`

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_publish_score_blocks_on_hard_fails -v`
Expected: FAIL due missing fields/logic.

**Step 3: Implement minimal hard-fail evaluator**

In `publish_score`:
- compute `hard_fail_reasons: list[str]`
- compute `recommended_actions: list[str]`
- apply `gate_passed = overall >= threshold and not hard_fail_reasons`

**Step 4: Run tests to verify pass**

Run task-specific tests then full API service tests:
`PYTHONPATH=src python3 -m unittest tests.api.test_api_service -q`

**Step 5: Commit**

```bash
git add src/mind_lite/api/service.py tests/api/test_api_service.py
git commit -m "feat: add hard-fail diagnostics to editorial scoring"
```

---

### Task 3: Add revision queue service methods and state persistence

**Files:**
- Modify: `src/mind_lite/api/service.py`
- Modify: `tests/api/test_api_service.py`

**Step 1: Write failing tests for revision queue behavior**

Add tests for:
- `mark_for_revision` enqueues failed draft
- `list_revision_queue` returns `count` and `items`
- persistence reload includes revision queue data

**Step 2: Run tests to verify fail**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_mark_for_revision_enqueues_failed_draft -v`
Expected: FAIL because methods/state keys do not exist.

**Step 3: Implement minimal queue support**

In `ApiService`:
- add internal `_revision_queue`
- add `mark_for_revision(payload)`
- add `list_revision_queue()`
- include queue in save/load state shape

**Step 4: Run tests to verify pass**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service -q`

**Step 5: Commit**

```bash
git add src/mind_lite/api/service.py tests/api/test_api_service.py
git commit -m "feat: add revision queue persistence for failed drafts"
```

---

### Task 4: Add HTTP endpoints for revision queue

**Files:**
- Modify: `src/mind_lite/api/http_server.py`
- Modify: `tests/api/test_http_server.py`

**Step 1: Write failing endpoint tests**

Add tests for:
- `POST /publish/mark-for-revision`
- `GET /publish/revision-queue`

**Step 2: Run tests to verify fail**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_http_server.HttpServerTests.test_mark_for_revision_endpoint -v`
Expected: FAIL with 404/unhandled route.

**Step 3: Implement routes**

Wire server routes to new service methods.

**Step 4: Run tests to verify pass**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_http_server -q`

**Step 5: Commit**

```bash
git add src/mind_lite/api/http_server.py tests/api/test_http_server.py
git commit -m "feat: expose revision queue publish endpoints"
```

---

### Task 5: Update API docs for Phase F contracts

**Files:**
- Modify: `API.md`

**Step 1: Write doc assertions in tests (if existing docs checks present) or add a lightweight grep check command in plan**

**Step 2: Update endpoint and contract sections**

Document:
- stage-aware scoring fields
- hard-fail reasons/actions
- new revision queue endpoints

**Step 3: Verify references**

Run: `grep -n "mark-for-revision\|revision-queue\|hard_fail_reasons\|stage" API.md`
Expected: matching lines found.

**Step 4: Commit**

```bash
git add API.md
git commit -m "docs: document Phase F editorial gate and revision queue contracts"
```

---

### Task 6: Add failing plugin tests for stage-aware publish flow

**Files:**
- Modify: `obsidian-plugin/tests/publish-flow.test.ts`

**Step 1: Write failing plugin tests**

Cover:
- stage included in `/publish/score` payload
- gate-fail path calls `/publish/mark-for-revision`
- gate-pass path still calls `/publish/mark-for-gom`

**Step 2: Run tests to verify fail**

Run: `cd obsidian-plugin && npm run build && node tests/publish-flow.test.ts`
Expected: FAIL due missing stage/revision behavior.

**Step 3: Commit test-only change (optional if policy is strict TDD commit granularity)**

```bash
git add obsidian-plugin/tests/publish-flow.test.ts
git commit -m "test: define stage-aware publish flow expectations"
```

---

### Task 7: Implement plugin stage prompt and fail/pass branching

**Files:**
- Modify: `obsidian-plugin/src/features/publish/gom-flow.ts`
- Modify: `obsidian-plugin/src/features/publish/modals/PrepareModal.ts`
- Modify: `obsidian-plugin/src/features/publish/modals/GateResultsModal.ts`
- Modify: `obsidian-plugin/src/main.ts` (only if command wiring needs updates)

**Step 1: Implement minimal stage selection**

Add stage input with allowed values `seed|sprout|tree`, default `seed`.

**Step 2: Send stage in score payload and branch by gate result**

- On pass: existing mark-for-gom path
- On fail: call mark-for-revision and show reasons/actions

**Step 3: Run plugin test to verify pass**

Run: `cd obsidian-plugin && npm run build && node tests/publish-flow.test.ts`
Expected: PASS.

**Step 4: Run full plugin verify**

Run: `cd obsidian-plugin && npm run verify`
Expected: PASS.

**Step 5: Commit**

```bash
git add obsidian-plugin/src/features/publish/ obsidian-plugin/src/main.ts obsidian-plugin/tests/publish-flow.test.ts
git commit -m "feat: add stage-aware publish flow with revision routing"
```

---

### Task 8: End-to-end verification and docs sync

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `ROADMAP.md`

**Step 1: Update status docs for Phase F slice completion**

Record editorial gate hardening and revision queue delivery.

**Step 2: Run full verification**

Run:
`PYTHONPATH=src python3 -m unittest discover -q`

Run:
`cd obsidian-plugin && npm run verify`

Expected: all tests pass.

**Step 3: Commit**

```bash
git add ARCHITECTURE.md ROADMAP.md
git commit -m "docs: record Phase F editorial gate hardening status"
```

---

## Final Verification

Run both suites from clean working state:

```bash
PYTHONPATH=src python3 -m unittest discover -q
cd obsidian-plugin && npm run verify
```

Expected:
- Python suite passes
- Plugin suite/build passes
- No contract drift between plugin payloads and publish endpoints
