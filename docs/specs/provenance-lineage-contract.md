# Mind Lite - Provenance and Lineage Contract (V1)

**Status:** Approved for Prebuild Gate  
**Last Updated:** 2026-02-18

---

## Purpose

Ensure every meaningful transformation in Mind Lite is traceable, reviewable, and reversible when applicable.

---

## Mandatory Lineage Fields

Every non-trivial operation must include:

- `run_id`
- `event_id`
- `timestamp`
- `actor_type` (`user`, `system`, `policy`)
- `action_type`
- `risk_tier`
- `confidence`
- `source_note_ids`
- `provider` (`local`, `openai`, or `none`)
- `rationale`
- `input_content_hash` (hash of source snapshot)
- `output_content_hash` (hash after applied transformation)

---

## Canonical Event Types

- `analyzed`
- `proposed`
- `approved`
- `rejected`
- `applied`
- `rolled_back`
- `blocked_by_policy`
- `published`
- `publish_rejected`
- `exported`

---

## Event Schema Example

```json
{
  "run_id": "run_2026_02_18_001",
  "event_id": "evt_00123",
  "timestamp": "2026-02-18T17:24:18Z",
  "actor_type": "system",
  "action_type": "link_proposal",
  "risk_tier": "medium",
  "confidence": 0.74,
  "source_note_ids": ["note_122", "note_777"],
  "provider": "local",
  "rationale": "semantic_similarity_and_shared_tags",
  "event_type": "proposed"
}
```

---

## Publish Lineage Requirements

For every published artifact, record:

- source notes/chunks used
- gate score and stage (`seed/sprout/tree`)
- hard-fail checks performed
- publication confirmation record
- sanitizer/redaction actions applied
- final artifact hash and export target

---

## Reversibility Contract

- Every `applied` batch must reference a snapshot ID
- Every rollback must reference the target snapshot and affected events
- Non-reversible actions must be explicit and human-approved

### Diff and Replay Requirements

- Every `applied` event must include before/after diff reference
- Event replay for a run must reconstruct exact decision order
- If replay cannot reconstruct state, run is marked invalid for release evidence

---

## Retention Rules (V1)

- Keep run and lineage records for at least 180 days
- Keep publish lineage records indefinitely unless manually pruned

### Integrity and Tamper Rules

- Lineage records are append-only in normal operation
- Record edits require explicit `correction` events; never silent overwrite
- Integrity verification runs weekly on lineage store checksums

---

## Verification Checks (Required Before GO)

- Every `applied` event references a valid snapshot ID
- Every `published` event references source note lineage
- Replaying event chain for one run reproduces decision timeline
- No event write path omits mandatory fields
