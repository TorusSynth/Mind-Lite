# Phase B Batch Checkpoint Snapshots Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add batch checkpoint tracking so each applied batch in a multi-folder run has a snapshot_id, enabling per-batch rollback granularity.

**Architecture:** Extend batch entries to include `snapshot_id` (null initially) and parent runs to track `applied_batch_ids`. Add a helper method to update batch checkpoint after child run apply. Reuse existing `SnapshotStore` and `apply_batch` contracts.

**Tech Stack:** Python 3, standard library `unittest`, existing snapshot contracts

---

### Task 1: Add failing service tests for batch checkpoint behavior

**Files:**
- Modify: `tests/api/test_api_service.py`

**Step 1: Write failing test for batch entry snapshot_id field**

Add test:
- `test_batch_entry_has_snapshot_id_field_initially_null`
- Create parent run via analyze_folders
- Assert each batch entry has `snapshot_id: None`

```python
def test_batch_entry_has_snapshot_id_field_initially_null(self):
    # ... create parent run with batches
    for batch in parent["batches"]:
        self.assertIsNone(batch.get("snapshot_id"))
```

**Step 2: Write failing test for batch checkpoint after child apply**

Add test:
- `test_batch_checkpoint_updated_after_child_apply`
- Create parent run with batches
- Approve and apply one child run
- Assert batch entry has `snapshot_id` matching child snapshot
- Assert parent has `applied_batch_ids` containing child run_id

**Step 3: Write failing test for multiple batch checkpoints**

Add test:
- `test_multiple_batch_checkpoints_tracked_correctly`
- Create parent with 2 batches
- Apply both children
- Assert each batch has correct snapshot_id
- Assert `applied_batch_ids` contains both run_ids

**Step 4: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_batch_entry_has_snapshot_id_field_initially_null tests.api.test_api_service.ApiServiceTests.test_batch_checkpoint_updated_after_child_apply tests.api.test_api_service.ApiServiceTests.test_multiple_batch_checkpoints_tracked_correctly -q`
Expected: FAIL before implementation.

---

### Task 2: Extend batch entry and parent run data model

**Files:**
- Modify: `src/mind_lite/api/service.py`

**Step 1: Add snapshot_id to batch entries in analyze_folders**

In `analyze_folders`, update batch_summary to include `"snapshot_id": None`:

```python
batch_summary = {
    "batch_id": batch_id,
    "folder_path": folder_path,
    "run_id": child_run_id,
    "state": child_run.get("state"),
    "proposal_count": proposal_count,
    "diagnostics_count": child_diagnostics_count,
    "snapshot_id": None,
}
```

**Step 2: Add applied_batch_ids to parent run**

In `analyze_folders`, add to parent run initialization:

```python
run = {
    "run_id": run_id,
    "state": RunState.QUEUED.value,
    "batch_total": len(folder_paths),
    "batch_completed": 0,
    "batches": [],
    "diagnostics": [],
    "applied_batch_ids": [],
}
```

**Step 3: Update test expectations to include new fields**

Update existing batch tests to expect `snapshot_id` and `applied_batch_ids` in assertions.

**Step 4: Run existing batch tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service -q`
Expected: Some tests may fail due to new fields - fix test assertions.

---

### Task 3: Implement batch checkpoint update helper

**Files:**
- Modify: `src/mind_lite/api/service.py`

**Step 1: Add _update_batch_checkpoint helper method**

```python
def _update_batch_checkpoint(self, parent_run_id: str, child_run_id: str, snapshot_id: str) -> None:
    if parent_run_id not in self._runs:
        return
    parent = self._runs[parent_run_id]
    for batch in parent.get("batches", []):
        if batch.get("run_id") == child_run_id:
            batch["snapshot_id"] = snapshot_id
            break
    if child_run_id not in parent.get("applied_batch_ids", []):
        parent.setdefault("applied_batch_ids", []).append(child_run_id)
    self._persist_state()
```

**Step 2: Add helper to find parent run for a child run**

```python
def _find_parent_run_for_child(self, child_run_id: str) -> str | None:
    for run_id, run in self._runs.items():
        for batch in run.get("batches", []):
            if batch.get("run_id") == child_run_id:
                return run_id
    return None
```

**Step 3: Integrate with apply_run**

After snapshot is created in `apply_run`, check if run is a child of a batch parent and update checkpoint:

```python
# After snapshot is created
parent_run_id = self._find_parent_run_for_child(run_id)
if parent_run_id:
    self._update_batch_checkpoint(parent_run_id, run_id, snapshot.snapshot_id)
```

**Step 4: Run targeted tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_batch_checkpoint_updated_after_child_apply tests.api.test_api_service.ApiServiceTests.test_multiple_batch_checkpoints_tracked_correctly -q`
Expected: PASS.

---

### Task 4: Add integration test for full batch checkpoint flow

**Files:**
- Modify: `tests/api/test_api_service.py`

**Step 1: Write integration test**

Add test:
- `test_full_batch_checkpoint_flow_from_analyze_to_apply`
- Create real folders with notes
- Call analyze_folders
- Approve and apply child runs
- Verify batch checkpoints are correct
- Verify rollback works on child run

**Step 2: Run integration test**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_full_batch_checkpoint_flow_from_analyze_to_apply -q`
Expected: PASS.

---

### Task 5: Update docs and run full verification

**Files:**
- Modify: `API.md`
- Modify: `ARCHITECTURE.md`

**Step 1: Add implementation status bullets**

Document:
- Batch checkpoint snapshot_id tracking in batch entries
- Parent run applied_batch_ids tracking
- Integration with apply_run for automatic checkpoint updates

**Step 2: Update endpoint documentation**

In API.md, update `POST /onboarding/analyze-folders` response to show `snapshot_id` and `applied_batch_ids` fields.

**Step 3: Run full suite**

Run: `PYTHONPATH=src python3 -m unittest discover -q`
Expected: PASS.

**Step 4: Commit sequence**

```bash
git add tests/api/test_api_service.py
git commit -m "test: define batch checkpoint snapshot behavior"
git add src/mind_lite/api/service.py
git commit -m "feat: add batch checkpoint snapshot tracking"
git add API.md ARCHITECTURE.md
git commit -m "docs: record batch checkpoint implementation status"
```

---

## Guardrails

- Keep existing rollback validation contract unchanged
- Single-folder runs should not be affected
- Batch checkpoints are optional metadata - don't break if missing
- Parent-batch relationship is determined by run_id matching
