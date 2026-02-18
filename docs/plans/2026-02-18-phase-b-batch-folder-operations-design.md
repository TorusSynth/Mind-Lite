# Phase B Batch Folder Operations Design

**Date:** 2026-02-18  
**Status:** Approved to implement

---

## Purpose

Complete the remaining Phase B onboarding scope by allowing one onboarding request to analyze multiple folders and report per-folder batch progress in a single parent run.

---

## Scope

### In Scope

- Add batch onboarding endpoint for multiple folders.
- Reuse existing single-folder analyze behavior per folder.
- Persist one parent run with per-folder child batch summaries.
- Aggregate parent run state from child outcomes.
- Add service + HTTP tests for batch success, partial failure, and validation.

### Out of Scope

- Async queue orchestration.
- New apply/approve semantics per batch.
- Rollback checkpoints implementation (next slice).

---

## Architecture

Keep `analyze_folder` unchanged for backward compatibility. Add new `analyze_folders` orchestration path:

1. `ApiService.analyze_folders(payload)` validates `folder_paths` list.
2. Parent run is created and transitioned (`queued -> analyzing`).
3. Each folder is analyzed using existing note/profile/proposal logic.
4. Child batch result is recorded under parent run.
5. Parent run terminal state is computed from child states and diagnostics.

HTTP layer adds `POST /onboarding/analyze-folders` mapped to `service.analyze_folders(...)`.

---

## Parent Run Data Model

Add parent run fields:

- `batch_total: int`
- `batch_completed: int`
- `batches: list[dict]`

Each batch entry:

- `batch_id: str`
- `folder_path: str`
- `run_id: str` (child run id)
- `state: str`
- `proposal_count: int`
- `diagnostics_count: int`

Parent run retains existing fields (`run_id`, `state`, `diagnostics`).

---

## State Aggregation Rules

After processing all folders:

- `failed_needs_attention` if all child runs failed.
- `ready_safe_auto` if at least one child is `ready_safe_auto` and not all failed.
- `awaiting_review` otherwise (successful non-auto or mixed non-failing outcomes).

State transitions remain lifecycle-validated.

---

## Data Flow

1. Client sends `POST /onboarding/analyze-folders` with `folder_paths`.
2. Service creates parent run and iterates folders.
3. For each folder:
   - run single-folder analysis
   - collect child run summary
4. Service computes parent terminal state + aggregate counters.
5. Service persists and returns parent run summary.

---

## Error Handling

- Invalid payload (`folder_paths` missing/empty/non-string items) -> `400`.
- Per-folder failures are captured in batch entry and parent diagnostics; processing continues.
- Unknown/unreadable folders are treated as failed child batches, not global hard abort.

---

## Testing Strategy

- Service tests:
  - batch analyze success with 2 folders
  - partial child failure with parent still returned
  - all-child failure -> parent `failed_needs_attention`
  - payload validation for `folder_paths`
- HTTP tests:
  - `/onboarding/analyze-folders` success response shape
  - partial failure behavior and status code
  - invalid payload returns 400
- Full suite verification after integration.

---

## Success Criteria

- One request can analyze multiple folders.
- Parent run exposes per-folder batch status and aggregate counts.
- Parent state is deterministic from child outcomes.
- Existing single-folder onboarding behavior remains unchanged.
