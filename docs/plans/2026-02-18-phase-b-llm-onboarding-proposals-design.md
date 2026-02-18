# Phase B LLM Onboarding Proposals Design

**Date:** 2026-02-18  
**Status:** Approved to implement

---

## Purpose

Complete the Phase B onboarding objective by replacing stub proposal generation with LLM-assisted, per-note proposals produced from real vault note content.

---

## Scope

### In Scope

- Extend onboarding profiling to include per-note metadata needed for proposal generation.
- Add an LLM proposal generator module for deterministic, validated JSON proposal output.
- Integrate proposal generation into `ApiService.analyze_folder`.
- Preserve existing safety and routing behavior via existing service policy contracts.
- Add tests for proposal generation, partial failure handling, and endpoint behavior.

### Out of Scope

- Obsidian plugin UX and interaction design.
- Model provider SDK integration beyond current routing simulation.
- Non-onboarding proposal flows.

---

## Architecture

The design adds one new onboarding component and extends two existing components:

1. **`analyze_readonly` enhancement**
   - Add note-level profiling output (`NoteProfile`) to `FolderProfile`.
   - Extract title, folder, tags, link count, and content excerpt per note.

2. **New `proposal_llm` module**
   - Create strict prompt template and JSON response contract.
   - Parse and validate LLM response into normalized proposal candidates.
   - Reject malformed or unsupported proposal payloads safely.

3. **`ApiService.analyze_folder` integration**
   - Build proposal candidates per note via LLM generator.
   - Map each candidate to service proposal schema.
   - Compute `action_mode` from `risk_tier` + `confidence` using existing action-tiering contract.
   - Persist run and proposals as before.

---

## Data Model

### `NoteProfile`

Add a new immutable dataclass in onboarding profiling:

- `note_id: str` (vault-relative path)
- `title: str`
- `folder: str`
- `tags: list[str]`
- `content_preview: str`
- `link_count: int`

### `FolderProfile` extension

Keep existing aggregate metrics and add:

- `notes: list[NoteProfile]`

### Proposal schema

LLM candidates normalize into proposal items containing:

- `change_type`
- `risk_tier`
- `confidence`
- `note_id`
- `details` (typed payload per proposal class)

Service-level proposals continue using:

- `proposal_id`, `change_type`, `risk_tier`, `confidence`, `action_mode`, `status`

---

## Data Flow

1. Client calls `POST /onboarding/analyze-folder`.
2. Service profiles folder and notes via `analyze_readonly`.
3. Service calls LLM proposal generator for each note profile.
4. LLM output is parsed and normalized into validated candidates.
5. Service converts candidates into run proposals and computes action mode.
6. Service persists run + proposal set and returns run payload.

---

## Error Handling

- **Per-note LLM failure**: skip failed note, track diagnostic.
- **Malformed LLM payload**: drop invalid proposals for that note.
- **All notes fail proposal generation**: keep run persisted and set run state to `failed_needs_attention` with reason summary.
- **Missing/invalid folder input**: preserve current validation behavior.

---

## Testing Strategy

- Unit tests for note profiling shape and metadata extraction.
- Unit tests for LLM proposal parser/validator with valid and invalid outputs.
- Service tests for:
  - successful proposal generation for analyzed folder
  - partial note-level failures
  - all-fail path transitioning to `failed_needs_attention`
- HTTP tests for analyze endpoint response integrity under success/failure paths.

---

## Success Criteria

- `analyze_folder` produces proposal sets based on actual note content.
- Proposal payloads are validated and normalized before persistence.
- Existing risk/action-tier contracts remain the source of action mode decisions.
- Failure modes are explicit and test-covered.
