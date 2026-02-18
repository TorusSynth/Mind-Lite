# Phase B LLM Onboarding Proposals Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace stub onboarding proposals with validated, note-derived LLM-assisted proposal generation in `analyze_folder`.

**Architecture:** Extend readonly onboarding analysis to produce note-level profiles, then add a dedicated onboarding LLM proposal module that outputs strict JSON candidates. Integrate this module into `ApiService.analyze_folder`, converting normalized candidates into proposal records with action mode computed by existing action-tiering contracts.

**Tech Stack:** Python 3, standard library (`unittest`, `json`, `dataclasses`, `pathlib`, `re`)

---

### Task 1: Extend onboarding profile model with per-note data

**Files:**
- Modify: `src/mind_lite/onboarding/analyze_readonly.py`
- Modify: `tests/onboarding/test_analyze_readonly.py`

**Step 1: Write failing test for note-level profile output**

Add a test in `tests/onboarding/test_analyze_readonly.py` that asserts `analyze_folder` returns note details, including:
- `notes` exists and contains one entry per markdown file
- each note includes `note_id`, `title`, `folder`, `tags`, `content_preview`, `link_count`

```python
def test_includes_note_profiles_with_metadata(self):
    profile = analyze_folder(str(root))
    self.assertEqual(len(profile.notes), 2)
    self.assertEqual(profile.notes[0].note_id, "a.md")
```

**Step 2: Run failing onboarding test**

Run: `PYTHONPATH=src python3 -m unittest tests.onboarding.test_analyze_readonly.AnalyzeReadonlyTests.test_includes_note_profiles_with_metadata -q`
Expected: FAIL because `FolderProfile` currently has no `notes` field.

**Step 3: Implement minimal NoteProfile + FolderProfile extension**

In `src/mind_lite/onboarding/analyze_readonly.py`:
- add `NoteProfile` dataclass
- add `notes: list[NoteProfile]` to `FolderProfile`
- extract note metadata for each markdown file

```python
@dataclass(frozen=True)
class NoteProfile:
    note_id: str
    title: str
    folder: str
    tags: list[str]
    content_preview: str
    link_count: int
```

**Step 4: Run onboarding tests**

Run: `PYTHONPATH=src python3 -m unittest tests.onboarding.test_analyze_readonly -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/mind_lite/onboarding/analyze_readonly.py tests/onboarding/test_analyze_readonly.py
git commit -m "feat: enrich onboarding profile with note-level metadata"
```

---

### Task 2: Add LLM proposal normalization module

**Files:**
- Create: `src/mind_lite/onboarding/proposal_llm.py`
- Modify: `src/mind_lite/onboarding/__init__.py`
- Create: `tests/onboarding/test_proposal_llm.py`

**Step 1: Write failing parser tests**

Add tests in `tests/onboarding/test_proposal_llm.py` for:
- valid JSON candidate payload normalized successfully
- invalid `risk_tier` rejected
- confidence out of range rejected
- missing `note_id` rejected

```python
def test_parse_candidates_accepts_valid_payload(self):
    payload = '{"proposals": [{"note_id": "a.md", "change_type": "tag_enrichment", "risk_tier": "low", "confidence": 0.82, "details": {"suggested_tags": ["project"]}}]}'
    out = parse_llm_candidates(payload)
    self.assertEqual(out[0]["risk_tier"], "low")
```

**Step 2: Run failing parser tests**

Run: `PYTHONPATH=src python3 -m unittest tests.onboarding.test_proposal_llm -q`
Expected: FAIL because module/function does not yet exist.

**Step 3: Implement minimal proposal parsing and validation**

In `src/mind_lite/onboarding/proposal_llm.py` implement:
- `build_note_prompt(note: dict) -> str`
- `parse_llm_candidates(raw: str) -> list[dict]`
- strict validation for allowed enums:
  - `change_type`: `tag_enrichment`, `link_add`, `folder_standardization`
  - `risk_tier`: `low`, `medium`, `high`
  - `0.0 <= confidence <= 1.0`

**Step 4: Run parser tests**

Run: `PYTHONPATH=src python3 -m unittest tests.onboarding.test_proposal_llm -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/mind_lite/onboarding/proposal_llm.py src/mind_lite/onboarding/__init__.py tests/onboarding/test_proposal_llm.py
git commit -m "feat: add onboarding llm proposal normalization"
```

---

### Task 3: Integrate proposal generation in ApiService analyze flow

**Files:**
- Modify: `src/mind_lite/api/service.py`
- Modify: `tests/api/test_api_service.py`

**Step 1: Write failing service test for real onboarding proposals**

Add a new test in `tests/api/test_api_service.py` that:
- creates markdown notes
- monkeypatches/stubs an LLM response generator to return proposal candidates
- calls `analyze_folder`
- asserts stored proposals contain note-linked, non-stub data

```python
def test_analyze_folder_populates_proposals_from_note_candidates(self):
    run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
    listed = service.get_run_proposals(run["run_id"])
    self.assertEqual(listed["proposals"][0]["note_id"], "a.md")
```

**Step 2: Run failing service test**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_analyze_folder_populates_proposals_from_note_candidates -q`
Expected: FAIL due missing integration in `analyze_folder`.

**Step 3: Implement analyze flow integration**

In `src/mind_lite/api/service.py`:
- add helper that builds proposal candidates from analyzed `profile["notes"]`
- convert candidates into stored proposal rows
- compute `action_mode` with `decide_action_mode(...)`
- keep `status="pending"`

**Step 4: Run focused service module tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/mind_lite/api/service.py tests/api/test_api_service.py
git commit -m "feat: generate onboarding proposals from llm note candidates"
```

---

### Task 4: Handle partial/all-failure proposal paths

**Files:**
- Modify: `src/mind_lite/api/service.py`
- Modify: `tests/api/test_api_service.py`
- Modify: `tests/api/test_http_server.py`

**Step 1: Write failing tests for degraded behavior**

Add tests covering:
- partial note failures: run remains available with reduced proposal set
- all-note failures: run state set to `failed_needs_attention` and diagnostics included
- HTTP `/onboarding/analyze-folder` returns these states correctly

**Step 2: Run failing degraded-path tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service.ApiServiceTests.test_analyze_folder_handles_partial_note_failures tests.api.test_api_service.ApiServiceTests.test_analyze_folder_sets_failed_needs_attention_when_all_notes_fail tests.api.test_http_server.HttpServerTests.test_analyze_folder_endpoint_reports_failed_needs_attention_when_all_notes_fail -q`
Expected: FAIL before implementation.

**Step 3: Implement minimal degraded-path behavior**

In service:
- catch per-note generation/parse errors
- accumulate diagnostics list
- if no valid proposals generated, set run state to `failed_needs_attention`

**Step 4: Run focused API tests**

Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service tests.api.test_http_server -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/mind_lite/api/service.py tests/api/test_api_service.py tests/api/test_http_server.py
git commit -m "feat: add onboarding proposal failure-state handling"
```

---

### Task 5: Update docs and run full verification

**Files:**
- Modify: `API.md`
- Modify: `ARCHITECTURE.md`
- Modify: `docs/plans/2026-02-18-mind-lite-v1-obsidian-second-brain-implementation.md`

**Step 1: Add implementation status entries**

Document:
- LLM onboarding proposal generation component location
- note-level profiling contract and tests
- failure-state handling behavior for onboarding analyze runs

**Step 2: Run full suite**

Run: `PYTHONPATH=src python3 -m unittest discover -q`
Expected: PASS.

**Step 3: Commit**

```bash
git add API.md ARCHITECTURE.md docs/plans/2026-02-18-mind-lite-v1-obsidian-second-brain-implementation.md
git commit -m "docs: record phase b llm onboarding proposal status"
```

---

## Guardrails

- Keep onboarding read-only (no note mutation in this slice).
- Reject malformed LLM output rather than storing weak data.
- Preserve existing endpoint contracts unless explicitly expanded.
- Keep routing/privacy/budget policy decisions in existing contracts.
