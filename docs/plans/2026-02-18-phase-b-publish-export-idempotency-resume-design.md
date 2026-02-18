# Phase B Publish Export Idempotency Resume Design

**Date:** 2026-02-18  
**Status:** Approved to execute

---

## Purpose

Resume interrupted Phase B work by completing idempotency replay behavior for `POST /publish/export-for-gom` with parity to existing `ask`, `links/apply`, `publish/mark-for-gom`, and `publish/confirm-gom` flows.

---

## Scope

### In Scope

- Add service-level idempotency replay support for `export_for_gom` using `event_id`
- Persist export replay cache in optional state file mode
- Add API service and HTTP server tests for duplicate replay behavior
- Update implementation status docs to record completion

### Out of Scope

- Changes to export artifact formats or content model
- New endpoints or auth/security model changes
- Queue model redesign

---

## Architecture

Use the existing replay pattern already implemented in `src/mind_lite/api/service.py`:

1. Validate optional `event_id` and normalize it.
2. On duplicate `event_id`, return cached response with `idempotency.duplicate = true`.
3. On first-seen `event_id`, execute normal export logic, include idempotency metadata with `duplicate = false`, then cache/persist response.

State persistence follows existing key-based replay caches (`ask_replay`, `links_apply_replay`, `publish_mark_replay`, `publish_confirm_replay`) by adding `publish_export_replay`.

---

## Data Flow

1. Client sends `POST /publish/export-for-gom` with `draft_id`, `format`, and optional `event_id`.
2. Service checks replay ledger for `publish_export` + `event_id`.
3. If duplicate:
   - Return cached export payload
   - Set idempotency fields (`event_id`, `duplicate=true`, reason from replay ledger)
4. If first-seen:
   - Resolve queued draft
   - Build export artifact for requested format
   - Attach idempotency fields (`duplicate=false`, `accepted` or `not_provided`)
   - Cache by `event_id` and persist state when configured

---

## Error Handling

- Keep existing validation/errors for:
  - missing/invalid `draft_id`
  - missing/invalid `format`
  - unsupported format
  - unknown draft
- Add validation parity for `event_id`: reject empty/non-string value when provided
- Keep replay safety invariant: duplicate without cache entry raises `ValueError`

---

## Testing Strategy

- Service tests (`tests/api/test_api_service.py`):
  - duplicate export event replays prior response
  - export replay cache persists across state-file reload
- HTTP tests (`tests/api/test_http_server.py`):
  - endpoint duplicate replay behavior
  - replay cache persistence across server restarts
- Verification:
  - targeted unittest modules first
  - full `unittest discover` pass last

---

## Success Criteria

- `export_for_gom` behavior is idempotent when `event_id` is supplied
- Duplicate requests return original artifact and identify replay
- Replay behavior survives restart in state-file mode
- Docs mention export idempotency implementation status explicitly
