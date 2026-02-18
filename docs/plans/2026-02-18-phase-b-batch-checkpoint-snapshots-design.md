# Phase B Batch Checkpoint Snapshots Design

**Date:** 2026-02-18  
**Status:** Approved to implement

---

## Purpose

Complete the final Phase B exit criterion by creating explicit checkpoint records for each applied batch in a multi-folder onboarding run, enabling per-batch rollback granularity.

---

## Scope

### In Scope

- Extend batch entry schema to track `snapshot_id` after child run apply
- Add parent run `applied_batch_ids` tracking
- Update batch entry when child run is applied
- Add service method to update batch checkpoint after apply
- Add tests for batch checkpoint behavior

### Out of Scope

- New snapshot storage model
- Changes to existing rollback validation contract
- Parent-level aggregate rollback UI

---

## Architecture

Leverage existing `SnapshotStore` and `apply_batch` contracts. The change is purely in how batch entries and parent runs track applied state.

1. Batch entries gain a `snapshot_id` field (null initially, populated after apply)
2. Parent runs gain an `applied_batch_ids` list
3. When a child run is applied:
   - Existing `apply_run` creates a snapshot
   - New helper updates the parent's batch entry with the snapshot_id
   - Parent's `applied_batch_ids` is updated

---

## Data Model

### Parent Run Extensions

```python
{
    "applied_batch_ids": list[str],  # child run_ids that have been applied
}
```

### Batch Entry Extensions

```python
{
    "snapshot_id": str | None,  # null until child run is applied
}
```

Existing fields remain unchanged: `batch_id`, `folder_path`, `run_id`, `state`, `proposal_count`, `diagnostics_count`

---

## Data Flow

1. `POST /onboarding/analyze-folders` creates parent run with batches (existing behavior)
2. Batches initially have `snapshot_id: null`
3. For each child run:
   - `POST /runs/{child_run_id}/approve` approves proposals
   - `POST /runs/{child_run_id}/apply` creates snapshot and updates child run state
   - New: batch entry in parent is updated with `snapshot_id`
   - New: parent `applied_batch_ids` is updated
4. `GET /runs/{parent_run_id}` shows which batches are applied and their snapshots
5. `POST /runs/{child_run_id}/rollback` rolls back specific child (existing behavior)

---

## Service Changes

### New Helper Method

```python
def _update_batch_checkpoint(self, parent_run_id: str, child_run_id: str, snapshot_id: str) -> None:
    # Find batch entry by child_run_id and update snapshot_id
    # Add child_run_id to applied_batch_ids if not present
    # Persist state
```

### Integration Points

- After `apply_run` creates a snapshot, call `_update_batch_checkpoint` if the run is a child of a batch parent
- Determine parent relationship by checking if `run_id` appears in any parent run's `batches[].run_id`

---

## Error Handling

- Child run apply fails -> snapshot not created, batch entry remains `snapshot_id: null`
- Rollback on non-applied batch -> existing rollback validation returns error
- Parent queries always show current `snapshot_id` (or null)

---

## Testing Strategy

- Service tests:
  - batch entry starts with null snapshot_id
  - after child apply, batch entry has snapshot_id
  - parent applied_batch_ids updated correctly
  - multiple child applies tracked correctly
- Integration tests:
  - full flow: analyze_folders -> approve child -> apply child -> verify batch checkpoint
- Full suite verification after changes

---

## Success Criteria

- Each applied batch has a snapshot_id in parent run
- Parent run tracks which batches have been applied
- Existing rollback behavior unchanged for single-folder runs
- Phase B exit criterion "Rollback checkpoints created per batch" satisfied
