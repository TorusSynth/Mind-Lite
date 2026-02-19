# Phase F: Editorial Gate Hardening Design

## Goal

Implement stage-aware editorial gating for GOM publishing with strict threshold enforcement and hard-fail routing to a dedicated revision queue.

## Scope

This design covers Phase F slice 1:

- Stage-aware score thresholds (`seed`, `sprout`, `tree`)
- Hard-fail checks that override numeric scores
- Revision queue separation from publish queue
- Obsidian publish flow integration for gate pass/fail paths

Out of scope for this slice:

- Advanced rubric explainability
- Multi-reviewer workflows
- Full benchmark tuning for thresholds

---

## Stage Threshold Policy

Thresholds:

- `seed`: `0.70`
- `sprout`: `0.80`
- `tree`: `0.90`

Scoring decision rules:

1. Compute rubric subscores and `overall` score.
2. Resolve threshold from `stage`.
3. Evaluate hard-fail checks.
4. `gate_passed = (overall >= threshold) and (hard_fail_reasons is empty)`.

This guarantees stage strictness while still allowing hard safety checks to block publish regardless of score.

---

## Hard-Fail Rules

Hard-fails block publish immediately and must produce explicit reasons.

Initial hard-fail set:

- Missing required metadata/fields (`draft_id`, `stage`, `target`, non-empty content/prepared content)
- Explicit unsafe markers in content (starting with deterministic patterns, including TODO marker policy)
- Safety subscore below floor (`safety < 0.60`)

Response contract will include:

- `hard_fail_reasons: string[]`
- `recommended_actions: string[]`

`recommended_actions` are short remediation prompts (for example: remove TODO placeholders, add missing metadata, improve safety language).

---

## Queue Architecture

Current queue becomes the **publish queue** (only gate-passed drafts).

Add a **revision queue** for gate failures.

Revision item shape:

- `draft_id`
- `stage`
- `target`
- `scores`
- `hard_fail_reasons`
- `recommended_actions`
- `status` (`needs_revision`)

Flow:

1. `POST /publish/prepare`
2. `POST /publish/score` with `stage`
3. If pass: `POST /publish/mark-for-gom`
4. If fail: `POST /publish/mark-for-revision`

Endpoint addition:

- `GET /publish/revision-queue`

Existing export/confirm paths remain publish-queue-only.

---

## API Design Changes

### `POST /publish/score`

Request additions:

- `stage` required (`seed|sprout|tree`)

Response additions:

- `threshold`
- `hard_fail_reasons`
- `recommended_actions`

### `POST /publish/mark-for-revision`

New endpoint to enqueue failed drafts.

### `GET /publish/revision-queue`

Returns revision queue items and count.

Persistence should follow existing optional file-backed state patterns used by publish queue.

---

## Obsidian Plugin UX Changes

In publish wizard:

- Prompt for stage selection (`seed`, `sprout`, `tree`)
- Send stage to `/publish/score`
- If gate passes: keep current success path
- If gate fails: show failure modal with hard-fail reasons and recommended actions, then enqueue to revision queue

The plugin should clearly communicate:

- Why publish was blocked
- What to edit before retry

---

## Error Handling

- Invalid stage: return `400` with explicit allowed values
- Missing required fields: return validation error and include failing field name
- Queue operations on unknown draft IDs: explicit, deterministic error message
- Plugin must surface API errors in modal notices and keep user context

---

## Testing Strategy

### API Service Tests

- Stage thresholds enforced for seed/sprout/tree
- Hard-fail precedence over high overall score
- Revision queue enqueue/list behavior
- Publish queue unchanged for passing flow

### HTTP Endpoint Tests

- `/publish/score` requires stage and returns expanded contract
- `/publish/mark-for-revision` and `/publish/revision-queue` contract tests

### Plugin Tests

- Stage value sent in score payload
- Pass branch routes to GOM queue
- Fail branch routes to revision queue and displays reasons/actions

---

## Acceptance Criteria

Phase F slice 1 is complete when:

- Stage-aware thresholds enforced exactly (`0.70`, `0.80`, `0.90`)
- Hard-fail checks block publish regardless of overall score
- Failed drafts are routed to and visible in revision queue
- Plugin publish flow supports stage selection and displays gate diagnostics
- Existing tests plus new publish/revision tests pass
