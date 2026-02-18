# Phase B Staged Onboarding Run States Design

**Date:** 2026-02-18  
**Status:** Approved to implement

---

## Purpose

Complete the remaining Phase B staged-flow gap by making onboarding runs transition through lifecycle states deterministically instead of remaining in `analyzing` for most paths.

---

## Scope

### In Scope

- Transition-aware state changes in onboarding run methods.
- State assignment during `analyze_folder` based on proposal outcomes.
- Transition validation for `approve_run` and `apply_run`.
- Tests for valid and invalid transition paths.
- API/architecture docs updates for staged state behavior.

### Out of Scope

- Multi-folder batch orchestration.
- New endpoint surfaces.
- Snapshot model redesign.

---

## Architecture

Use existing lifecycle contract definitions in `src/mind_lite/contracts/run_lifecycle.py` as the source of truth for legal transitions.

Add a small transition helper inside `ApiService` that:

1. Reads current run state.
2. Validates target state with lifecycle contract.
3. Applies state change or raises clear `ValueError`.

All onboarding state changes route through this helper to avoid ad hoc mutation.

---

## State Model

### Analyze Flow

- Run starts as `queued`.
- Transition to `analyzing` when analysis begins.
- Final state after proposal generation:
  - `ready_safe_auto` when proposals include at least one `action_mode == "auto"` and no hard failure.
  - `awaiting_review` when proposals exist but all are review/manual paths.
  - `failed_needs_attention` when all note candidate generation paths fail.

### Approval/Apply Flow

- `approve_run` transitions into `approved` from `awaiting_review` (and optionally `ready_safe_auto` if explicit approval still used).
- `apply_run` transitions into `applied` from `approved`.
- `rollback_run` remains a global failure transition to `rolled_back`.

---

## Data Flow

1. `POST /onboarding/analyze-folder` creates run and enters `queued` then `analyzing`.
2. Proposal generation runs; diagnostics collected if needed.
3. Service computes final staged state (`ready_safe_auto`, `awaiting_review`, or `failed_needs_attention`).
4. Later actions (`approve`, `apply`, `rollback`) enforce valid source-state requirements.

---

## Error Handling

- Invalid transition attempts return `ValueError` with message `invalid run state transition: <current> -> <target>`.
- Unknown run IDs and payload validation errors remain unchanged.
- Failure states continue as legal global exits where contract allows.

---

## Testing Strategy

- Service tests:
  - analyze returns `ready_safe_auto` when auto proposals present.
  - analyze returns `awaiting_review` when no auto proposals present.
  - approve/apply reject invalid source states.
  - approve/apply succeed on valid staged flow.
- HTTP tests:
  - analyze endpoint state response reflects staged outcomes.
  - invalid approve/apply states return `400`.
- Full suite verification after changes.

---

## Success Criteria

- Phase B onboarding runs no longer stall in `analyzing` for successful paths.
- Run state transitions are validated and deterministic.
- Invalid stage operations fail clearly.
- Tests and docs explicitly cover staged behavior.
