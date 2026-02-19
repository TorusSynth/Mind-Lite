# Phase C: Organization LLM Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace stub LLM implementations with real LM Studio integration for PARA classification and link scoring.

**Architecture:** Two new modules (`organize/classify_llm.py`, `links/propose_llm.py`) provide LLM-based classification and scoring. Existing endpoints (`organize_classify`, `links_propose`) call these modules. Anti-spam controls filter link suggestions. Graceful fallback on LLM failure.

**Tech Stack:** Python 3.11, httpx for LLM calls, existing contracts (action_tiering, provider_routing)

---

## Task 1: Create classify_llm.py Module

**Files:**
- Create: `src/mind_lite/organize/__init__.py`
- Create: `src/mind_lite/organize/classify_llm.py`
- Create: `tests/organize/__init__.py`
- Create: `tests/organize/test_classify_llm.py`

**Step 1: Write the failing tests**

```python
# tests/organize/test_classify_llm.py
import pytest
from mind_lite.organize.classify_llm import (
    build_classify_prompt,
    parse_classify_response,
    classify_note,
)


class TestBuildClassifyPrompt:
    def test_includes_note_context(self):
        note = {
            "note_id": "abc123",
            "title": "Project Alpha Launch",
            "folder": "Inbox",
            "tags": ["project", "launch"],
            "content_preview": "Planning the Q1 launch...",
        }
        prompt = build_classify_prompt(note)
        assert "Project Alpha Launch" in prompt
        assert "project, launch" in prompt
        assert "Planning the Q1 launch" in prompt


class TestParseClassifyResponse:
    def test_valid_response(self):
        raw = '{"primary": "project", "secondary": ["area"], "confidence": 0.85}'
        result = parse_classify_response(raw)
        assert result == {"primary": "project", "secondary": ["area"], "confidence": 0.85}

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="valid JSON"):
            parse_classify_response("not json")

    def test_missing_primary_raises(self):
        with pytest.raises(ValueError, match="primary"):
            parse_classify_response('{"secondary": [], "confidence": 0.5}')

    def test_invalid_primary_raises(self):
        with pytest.raises(ValueError, match "project, area, resource, archive"):
            parse_classify_response('{"primary": "invalid", "confidence": 0.5}')

    def test_secondary_excludes_primary(self):
        with pytest.raises(ValueError, match "cannot repeat primary"):
            parse_classify_response('{"primary": "project", "secondary": ["project"], "confidence": 0.8}')

    def test_confidence_out_of_range_clamps(self):
        raw = '{"primary": "resource", "secondary": [], "confidence": 1.5}'
        result = parse_classify_response(raw)
        assert result["confidence"] == 1.0


class TestClassifyNote:
    def test_returns_classified_result(self, monkeypatch):
        def mock_llm_call(prompt: str) -> str:
            return '{"primary": "project", "secondary": ["area"], "confidence": 0.82}'
        monkeypatch.setattr("mind_lite.organize.classify_llm._call_llm", mock_llm_call)
        
        note = {"note_id": "x", "title": "Test", "folder": "", "tags": [], "content_preview": ""}
        result = classify_note(note)
        assert result["primary"] == "project"
        assert "area" in result["secondary"]
        assert result["confidence"] == 0.82
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/organize/test_classify_llm.py -v`
Expected: FAIL with "module not found"

**Step 3: Create module directories**

```bash
mkdir -p src/mind_lite/organize
mkdir -p tests/organize
touch src/mind_lite/organize/__init__.py
touch tests/organize/__init__.py
```

**Step 4: Write minimal implementation**

```python
# src/mind_lite/organize/classify_llm.py
import json

ALLOWED_PARA = {"project", "area", "resource", "archive"}


def build_classify_prompt(note: dict) -> str:
    tags = note.get("tags", [])
    if isinstance(tags, list):
        rendered_tags = ", ".join(str(t) for t in tags)
    elif isinstance(tags, str):
        rendered_tags = tags
    else:
        rendered_tags = ""

    return (
        f"Classify this note into PARA (Projects, Areas, Resources, Archive).\n\n"
        f"title: {note.get('title', '')}\n"
        f"folder: {note.get('folder', '')}\n"
        f"tags: {rendered_tags}\n"
        f"content_preview: {note.get('content_preview', '')[:500]}\n\n"
        f'Respond with JSON: {{"primary": "<category>", "secondary": ["<category>"], "confidence": 0.0-1.0}}\n'
        f"primary must be exactly one of: project, area, resource, archive\n"
        f"secondary can have up to 2 additional categories (not including primary)"
    )


def parse_classify_response(raw: str) -> dict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("response must be valid JSON") from error

    if not isinstance(payload, dict):
        raise ValueError("response must be a JSON object")

    primary = payload.get("primary")
    if primary not in ALLOWED_PARA:
        allowed = ", ".join(sorted(ALLOWED_PARA))
        raise ValueError(f"primary must be one of: {allowed}")

    secondary = payload.get("secondary", [])
    if not isinstance(secondary, list):
        raise ValueError("secondary must be a list")
    if primary in secondary:
        raise ValueError("secondary cannot repeat primary")
    if len(secondary) > 2:
        raise ValueError("secondary can have at most 2 entries")

    confidence = payload.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    confidence = max(0.0, min(1.0, float(confidence)))

    return {
        "primary": primary,
        "secondary": [s for s in secondary if s in ALLOWED_PARA and s != primary],
        "confidence": confidence,
    }


def _call_llm(prompt: str) -> str:
    import httpx
    from mind_lite.contracts.provider_routing import select_provider
    from mind_lite.config import get_settings

    settings = get_settings()
    provider = select_provider(settings)

    if provider == "lmstudio":
        base_url = settings.lmstudio_base_url or "http://localhost:1234"
        try:
            response = httpx.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": settings.lmstudio_model or "local-model",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 200,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception:
            return '{"primary": "resource", "secondary": [], "confidence": 0.5}'
    else:
        return '{"primary": "resource", "secondary": [], "confidence": 0.5}'


def classify_note(note: dict) -> dict:
    prompt = build_classify_prompt(note)
    raw = _call_llm(prompt)
    parsed = parse_classify_response(raw)
    parsed["note_id"] = note.get("note_id", "")
    return parsed
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/organize/test_classify_llm.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/mind_lite/organize/ tests/organize/
git commit -m "feat: add classify_llm module for PARA classification"
```

---

## Task 2: Create propose_llm.py Module

**Files:**
- Create: `src/mind_lite/links/__init__.py`
- Create: `src/mind_lite/links/propose_llm.py`
- Create: `tests/links/__init__.py`
- Create: `tests/links/test_propose_llm.py`

**Step 1: Write the failing tests**

```python
# tests/links/test_propose_llm.py
import pytest
from mind_lite.links.propose_llm import (
    build_link_prompt,
    parse_link_response,
    apply_spam_controls,
    score_links,
)


class TestBuildLinkPrompt:
    def test_includes_source_and_candidates(self):
        source = {"note_id": "s1", "title": "Source Note", "tags": [], "content_preview": "abc"}
        candidates = [
            {"note_id": "c1", "title": "Candidate 1", "tags": [], "content_preview": "def"},
        ]
        prompt = build_link_prompt(source, candidates)
        assert "Source Note" in prompt
        assert "Candidate 1" in prompt


class TestParseLinkResponse:
    def test_valid_response(self):
        raw = '{"suggestions": [{"target_note_id": "c1", "confidence": 0.85, "reason": "semantic_similarity"}]}'
        result = parse_link_response(raw)
        assert len(result) == 1
        assert result[0]["target_note_id"] == "c1"
        assert result[0]["reason"] == "semantic_similarity"

    def test_invalid_reason_raises(self):
        with pytest.raises(ValueError, match="shared_project_context, structural_overlap, semantic_similarity"):
            parse_link_response('{"suggestions": [{"target_note_id": "x", "confidence": 0.5, "reason": "invalid"}]}')

    def test_missing_suggestions_returns_empty(self):
        result = parse_link_response('{}')
        assert result == []


class TestApplySpamControls:
    def test_filters_low_confidence(self):
        suggestions = [
            {"target_note_id": "a", "confidence": 0.85, "reason": "semantic_similarity"},
            {"target_note_id": "b", "confidence": 0.40, "reason": "semantic_similarity"},
        ]
        result = apply_spam_controls(suggestions, existing_links=set(), batch_targets={})
        assert len(result) == 1
        assert result[0]["target_note_id"] == "a"

    def test_filters_existing_links(self):
        suggestions = [
            {"target_note_id": "a", "confidence": 0.85, "reason": "semantic_similarity"},
        ]
        result = apply_spam_controls(suggestions, existing_links={"a"}, batch_targets={})
        assert len(result) == 0

    def test_limits_target_saturation(self):
        suggestions = [
            {"target_note_id": "a", "confidence": 0.85, "reason": "semantic_similarity"},
            {"target_note_id": "a", "confidence": 0.80, "reason": "semantic_similarity"},
            {"target_note_id": "a", "confidence": 0.75, "reason": "semantic_similarity"},
            {"target_note_id": "a", "confidence": 0.70, "reason": "semantic_similarity"},
        ]
        batch_targets = {"a": 2}
        result = apply_spam_controls(suggestions, existing_links=set(), batch_targets=batch_targets)
        assert len(result) == 1

    def test_limits_max_suggestions(self):
        suggestions = [
            {"target_note_id": str(i), "confidence": 0.80, "reason": "semantic_similarity"}
            for i in range(20)
        ]
        result = apply_spam_controls(suggestions, existing_links=set(), batch_targets={})
        assert len(result) == 10


class TestScoreLinks:
    def test_returns_scored_suggestions(self, monkeypatch):
        def mock_llm_call(prompt: str) -> str:
            return '{"suggestions": [{"target_note_id": "c1", "confidence": 0.88, "reason": "shared_project_context"}]}'
        monkeypatch.setattr("mind_lite.links.propose_llm._call_llm", mock_llm_call)

        source = {"note_id": "s1", "title": "Source", "tags": [], "content_preview": ""}
        candidates = [{"note_id": "c1", "title": "C1", "tags": [], "content_preview": ""}]
        result = score_links(source, candidates)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.88
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/links/test_propose_llm.py -v`
Expected: FAIL with "module not found"

**Step 3: Create module directories**

```bash
mkdir -p src/mind_lite/links
mkdir -p tests/links
touch src/mind_lite/links/__init__.py
touch tests/links/__init__.py
```

**Step 4: Write minimal implementation**

```python
# src/mind_lite/links/propose_llm.py
import json
from collections import Counter

ALLOWED_REASONS = {"shared_project_context", "structural_overlap", "semantic_similarity"}
MAX_SUGGESTIONS = 10
MAX_TARGET_SATURATION = 3
MIN_CONFIDENCE = 0.50


def build_link_prompt(source: dict, candidates: list[dict]) -> str:
    def render_note(n: dict) -> str:
        tags = n.get("tags", [])
        tag_str = ", ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags)
        return f"- id: {n.get('note_id')}\n  title: {n.get('title')}\n  tags: {tag_str}"

    candidates_block = "\n".join(render_note(c) for c in candidates)
    return (
        f"Score link suggestions from source note to candidates.\n\n"
        f"SOURCE:\n{render_note(source)}\n\n"
        f"CANDIDATES:\n{candidates_block}\n\n"
        f'Respond with JSON: {{"suggestions": [{{"target_note_id": "<id>", "confidence": 0.0-1.0, "reason": "<reason>"}}]}}\n'
        f"reason must be one of: shared_project_context, structural_overlap, semantic_similarity\n"
        f"Only include suggestions with confidence >= 0.50"
    )


def parse_link_response(raw: str) -> list[dict]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, dict):
        return []

    suggestions = payload.get("suggestions", [])
    if not isinstance(suggestions, list):
        return []

    parsed = []
    for s in suggestions:
        if not isinstance(s, dict):
            continue
        target = s.get("target_note_id")
        if not isinstance(target, str) or not target.strip():
            continue
        reason = s.get("reason")
        if reason not in ALLOWED_REASONS:
            continue
        confidence = s.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        confidence = max(0.0, min(1.0, float(confidence)))
        parsed.append({
            "target_note_id": target.strip(),
            "confidence": confidence,
            "reason": reason,
        })
    return parsed


def apply_spam_controls(
    suggestions: list[dict],
    existing_links: set[str],
    batch_targets: Counter,
) -> list[dict]:
    filtered = []
    for s in suggestions:
        if s["confidence"] < MIN_CONFIDENCE:
            continue
        target = s["target_note_id"]
        if target in existing_links:
            continue
        if batch_targets.get(target, 0) >= MAX_TARGET_SATURATION:
            continue
        batch_targets[target] = batch_targets.get(target, 0) + 1
        filtered.append(s)
    return sorted(filtered, key=lambda x: x["confidence"], reverse=True)[:MAX_SUGGESTIONS]


def _call_llm(prompt: str) -> str:
    import httpx
    from mind_lite.contracts.provider_routing import select_provider
    from mind_lite.config import get_settings

    settings = get_settings()
    provider = select_provider(settings)

    if provider == "lmstudio":
        base_url = settings.lmstudio_base_url or "http://localhost:1234"
        try:
            response = httpx.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": settings.lmstudio_model or "local-model",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception:
            return '{"suggestions": []}'
    else:
        return '{"suggestions": []}'


def score_links(source: dict, candidates: list[dict]) -> list[dict]:
    prompt = build_link_prompt(source, candidates)
    raw = _call_llm(prompt)
    return parse_link_response(raw)
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/links/test_propose_llm.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/mind_lite/links/ tests/links/
git commit -m "feat: add propose_llm module for link scoring"
```

---

## Task 3: Integrate classify_llm into organize_classify()

**Files:**
- Modify: `src/mind_lite/api/service.py:808-837`
- Modify: `tests/api/test_api_service.py`

**Step 1: Write the failing test**

```python
# tests/api/test_api_service.py - add to existing file
class TestOrganizeClassifyLLM:
    def test_uses_llm_classification(self, monkeypatch):
        from mind_lite.api.service import APIService
        
        def mock_classify(note):
            return {
                "note_id": note["note_id"],
                "primary": "project",
                "secondary": ["area"],
                "confidence": 0.88,
            }
        monkeypatch.setattr("mind_lite.organize.classify_llm.classify_note", mock_classify)
        
        service = APIService()
        result = service.organize_classify({
            "notes": [{"note_id": "x", "title": "Test Note", "folder": "", "tags": [], "content_preview": ""}]
        })
        assert result["results"][0]["primary_para"] == "project"
        assert result["results"][0]["secondary_para"] == ["area"]
        assert result["results"][0]["confidence"] == 0.88
        assert result["results"][0]["action_mode"] == "auto"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_api_service.py::TestOrganizeClassifyLLM -v`
Expected: FAIL (still using stub)

**Step 3: Update organize_classify to use classify_llm**

```python
# src/mind_lite/api/service.py - replace organize_classify method
def organize_classify(self, payload: dict) -> dict:
    from mind_lite.organize.classify_llm import classify_note
    
    notes = payload.get("notes")
    if not isinstance(notes, list) or not notes:
        raise ValueError("notes must be a non-empty list")

    results = []
    for note in notes:
        if not isinstance(note, dict):
            raise ValueError("each note must be an object")

        note_id = note.get("note_id")
        if not isinstance(note_id, str) or not note_id.strip():
            raise ValueError("note_id is required")

        classified = classify_note(note)
        confidence = classified.get("confidence", 0.5)
        action_mode = decide_action_mode("low", confidence).value
        results.append({
            "note_id": note_id.strip(),
            "primary_para": classified.get("primary", "resource"),
            "secondary_para": classified.get("secondary", []),
            "confidence": confidence,
            "action_mode": action_mode,
        })

    return {"results": results}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_api_service.py::TestOrganizeClassifyLLM -v`
Expected: PASS

**Step 5: Remove stub method _classify_para**

Delete lines 1253-1261 in `src/mind_lite/api/service.py`.

**Step 6: Run all tests to verify no regression**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add src/mind_lite/api/service.py tests/api/test_api_service.py
git commit -m "feat: integrate classify_llm into organize_classify endpoint"
```

---

## Task 4: Integrate propose_llm into links_propose()

**Files:**
- Modify: `src/mind_lite/api/service.py:872-905`
- Modify: `tests/api/test_api_service.py`

**Step 1: Write the failing test**

```python
# tests/api/test_api_service.py - add to existing file
class TestLinksProposeLLM:
    def test_uses_llm_scoring(self, monkeypatch):
        from mind_lite.api.service import APIService
        
        def mock_score(source, candidates):
            return [
                {"target_note_id": "c1", "confidence": 0.92, "reason": "shared_project_context"},
            ]
        monkeypatch.setattr("mind_lite.links.propose_llm.score_links", mock_score)
        
        service = APIService()
        result = service.links_propose({
            "source_note_id": "s1",
            "candidate_notes": [{"note_id": "c1", "title": "C1", "tags": [], "content_preview": ""}]
        })
        assert result["suggestions"][0]["target_note_id"] == "c1"
        assert result["suggestions"][0]["confidence"] == 0.92
        assert result["suggestions"][0]["reason"] == "shared_project_context"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_api_service.py::TestLinksProposeLLM -v`
Expected: FAIL (still using stub)

**Step 3: Update links_propose to use propose_llm**

```python
# src/mind_lite/api/service.py - replace links_propose method
def links_propose(self, payload: dict) -> dict:
    from mind_lite.links.propose_llm import score_links, apply_spam_controls
    from collections import Counter
    
    source_note_id = payload.get("source_note_id")
    if not isinstance(source_note_id, str) or not source_note_id.strip():
        raise ValueError("source_note_id is required")

    candidate_notes = payload.get("candidate_notes")
    if not isinstance(candidate_notes, list) or not candidate_notes:
        raise ValueError("candidate_notes must be a non-empty list")

    source_note = {"note_id": source_note_id.strip()}
    for key in ["title", "tags", "content_preview"]:
        if key in payload:
            source_note[key] = payload[key]

    for note in candidate_notes:
        if not isinstance(note, dict):
            raise ValueError("each candidate note must be an object")
        note_id = note.get("note_id")
        if not isinstance(note_id, str) or not note_id.strip():
            raise ValueError("candidate note_id is required")

    suggestions = score_links(source_note, candidate_notes)
    suggestions = apply_spam_controls(suggestions, existing_links=set(), batch_targets=Counter())

    return {
        "source_note_id": source_note_id.strip(),
        "suggestions": suggestions,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_api_service.py::TestLinksProposeLLM -v`
Expected: PASS

**Step 5: Remove stub methods _link_confidence and _link_reason**

Delete lines 1263-1277 in `src/mind_lite/api/service.py`.

**Step 6: Run all tests to verify no regression**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add src/mind_lite/api/service.py tests/api/test_api_service.py
git commit -m "feat: integrate propose_llm into links_propose endpoint"
```

---

## Task 5: Add Error Handling and Fallback

**Files:**
- Modify: `src/mind_lite/organize/classify_llm.py`
- Modify: `src/mind_lite/links/propose_llm.py`
- Modify: `tests/organize/test_classify_llm.py`
- Modify: `tests/links/test_propose_llm.py`

**Step 1: Add fallback test for classify_llm**

```python
# tests/organize/test_classify_llm.py - add to TestClassifyNote
def test_llm_failure_returns_fallback(self, monkeypatch):
    def mock_llm_fail(prompt):
        raise Exception("LM Studio unavailable")
    monkeypatch.setattr("mind_lite.organize.classify_llm._call_llm", mock_llm_fail)
    
    # _call_llm should catch exception and return fallback
    note = {"note_id": "x", "title": "Test", "folder": "", "tags": [], "content_preview": ""}
    result = classify_note(note)
    assert result["primary"] == "resource"
    assert result["confidence"] == 0.5
```

**Step 2: Verify fallback already in place**

The `_call_llm` functions already have try/except returning fallback JSON. Run test:

Run: `pytest tests/organize/test_classify_llm.py::TestClassifyNote::test_llm_failure_returns_fallback -v`
Expected: PASS

**Step 3: Add fallback test for propose_llm**

```python
# tests/links/test_propose_llm.py - add to TestScoreLinks
def test_llm_failure_returns_empty(self, monkeypatch):
    def mock_llm_fail(prompt):
        raise Exception("LM Studio unavailable")
    monkeypatch.setattr("mind_lite.links.propose_llm._call_llm", mock_llm_fail)
    
    source = {"note_id": "s1", "title": "Source", "tags": [], "content_preview": ""}
    candidates = [{"note_id": "c1", "title": "C1", "tags": [], "content_preview": ""}]
    result = score_links(source, candidates)
    assert result == []
```

**Step 4: Verify fallback already in place**

Run: `pytest tests/links/test_propose_llm.py::TestScoreLinks::test_llm_failure_returns_empty -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/
git commit -m "test: add fallback tests for LLM failure scenarios"
```

---

## Task 6: Update Documentation

**Files:**
- Modify: `API.md`
- Modify: `ARCHITECTURE.md`

**Step 1: Update API.md with LLM integration notes**

Add section noting LLM integration for `organize_classify` and `links_propose`.

**Step 2: Update ARCHITECTURE.md with Phase C completion**

Mark Phase C as complete with exit criteria met.

**Step 3: Commit**

```bash
git add API.md ARCHITECTURE.md
git commit -m "docs: update API and ARCHITECTURE for Phase C completion"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Create classify_llm.py with PARA classification |
| 2 | Create propose_llm.py with link scoring |
| 3 | Integrate classify_llm into organize_classify() |
| 4 | Integrate propose_llm into links_propose() |
| 5 | Add error handling and fallback tests |
| 6 | Update documentation |

**Exit Criteria Verification:**
- Low-risk actions auto-apply when confidence >= 0.80: `decide_action_mode("low", 0.80) == AUTO`
- Medium-risk actions routed to review when confidence >= 0.70: `decide_action_mode("medium", 0.70) == SUGGEST`
- Anti-spam controls: confidence filter, saturation limit, max suggestions
