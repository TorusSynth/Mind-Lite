# Phase C: Organization & Graph Reconstruction - LLM Integration Design

## Goal

Replace stub LLM implementations with real LM Studio integration for:
1. PARA primary/secondary classification
2. Link proposal scoring
3. Anti-link-spam controls

## Exit Criteria

- Low-risk actions auto-apply when confidence >= 0.80
- Medium-risk actions routed to review when confidence >= 0.70
- False-link rate target and acceptance-rate targets defined

---

## Architecture

### New Modules

```
src/mind_lite/
├── organize/
│   └── classify_llm.py      # PARA classification via LLM
└── links/
    └── propose_llm.py        # Link scoring via LLM
```

### Existing Contracts (Reuse)

| Contract | Purpose | Location |
|----------|---------|----------|
| `decide_action_mode()` | Maps risk_tier + confidence → action_mode | `contracts/action_tiering.py` |
| `select_provider()` | LM Studio vs OpenAI fallback | `contracts/provider_routing.py` |
| `cloud_eligibility()` | Content filtering for cloud | `contracts/sensitivity_gate.py` |
| `evaluate_budget()` | Spending caps | `contracts/budget_guardrails.py` |

### Stubs to Replace

In `src/mind_lite/api/service.py`:
- `_classify_para(title)` → real LLM call
- `_link_confidence(title)` → real LLM call
- `_link_reason(title)` → real LLM call (via propose_llm)
- `_proposed_folder(title, folder)` → real LLM call

---

## Data Model

### PARA Classification

**Input:**
```python
{
    "note_id": str,
    "title": str,
    "folder": str,
    "tags": list[str],
    "content_preview": str,  # first 500 chars
}
```

**Output:**
```python
{
    "note_id": str,
    "primary_para": "project" | "area" | "resource" | "archive",
    "secondary_para": list[str],  # max 2, excluding primary
    "confidence": float,  # 0.0 - 1.0
    "action_mode": "auto" | "suggest" | "manual",
}
```

**Constraints:**
- `primary_para` must be exactly one of the four PARA categories
- `secondary_para` must NOT contain the same value as `primary_para`
- `secondary_para` limited to max 2 entries
- `confidence` must be in [0.0, 1.0]

### Link Proposal

**Input:**
```python
{
    "source_note": {
        "note_id": str,
        "title": str,
        "tags": list[str],
        "content_preview": str,
    },
    "candidate_notes": list[dict],  # same structure
}
```

**Output:**
```python
{
    "source_note_id": str,
    "suggestions": [
        {
            "target_note_id": str,
            "confidence": float,
            "reason": "shared_project_context" | "structural_overlap" | "semantic_similarity",
        }
    ],
}
```

**Constraints:**
- `reason` must be one of the three enum values (matching existing code)
- Suggestions sorted by confidence descending
- Max suggestions per batch: 10

---

## Data Flow

### PARA Classification Flow

```
1. API receives notes in organize_classify()
2. For each note:
   a. Build prompt with note context
   b. Call classify_llm.classify_note()
   c. LLM returns {primary, secondary[], confidence}
   d. Validate response (enums, constraints)
   e. Apply decide_action_mode("low", confidence)
   f. Return result
```

### Link Proposal Flow

```
1. API receives source_note + candidate_notes in links_propose()
2. Build batch prompt with all candidates
3. Call propose_llm.score_links()
4. LLM returns [{target_note_id, confidence, reason}]
5. Validate response (reason enum, confidence range)
6. Apply anti-spam controls:
   a. Filter suggestions with confidence < 0.50
   b. Limit max suggestions per source to 10
   c. Limit target saturation (max 3 times same target per batch)
7. Sort by confidence descending
8. Return suggestions
```

### LLM Integration Pattern

Follow `src/mind_lite/onboarding/proposal_llm.py`:
1. Build structured prompt with JSON schema
2. Parse response with validation
3. Raise ValueError on malformed responses

---

## Anti-Spam Controls

### Rules

| Rule | Threshold | Rationale |
|------|-----------|-----------|
| Min confidence | 0.50 | Filter low-quality suggestions |
| Max per source | 10 | Prevent link explosion |
| Target saturation | 3 | Same target appears max 3 times across batch |
| Duplicate link check | N/A | Skip if link already exists |

### Implementation

```python
def apply_link_spam_controls(
    suggestions: list[dict],
    existing_links: set[str],
    batch_targets: Counter,
) -> list[dict]:
    filtered = []
    for s in suggestions:
        # Skip low confidence
        if s["confidence"] < 0.50:
            continue
        # Skip existing links
        if s["target_note_id"] in existing_links:
            continue
        # Check target saturation
        if batch_targets[s["target_note_id"]] >= 3:
            continue
        batch_targets[s["target_note_id"]] += 1
        filtered.append(s)
    # Limit to top 10
    return sorted(filtered, key=lambda x: x["confidence"], reverse=True)[:10]
```

---

## Error Handling

### LLM Call Failures

| Scenario | Response |
|----------|----------|
| LM Studio unavailable | Fallback to stub behavior, log warning |
| Invalid JSON response | Raise ValueError, caller handles |
| Missing required fields | Raise ValueError with field name |
| Invalid enum value | Raise ValueError with allowed values |
| Confidence out of range | Clamp to [0.0, 1.0] with warning |

### Graceful Degradation

If LLM fails, return conservative defaults:
- PARA: `"resource"` with confidence `0.50`, action_mode `"manual"`
- Links: empty suggestions list

---

## Testing

### Unit Tests

| Module | Test Cases |
|--------|------------|
| `classify_llm.py` | Prompt building, response parsing, validation |
| `propose_llm.py` | Prompt building, response parsing, validation |
| Anti-spam | Confidence filter, saturation limit, dedup |

### Integration Tests

| Scenario | Expected |
|----------|----------|
| Valid LLM response | Correct classification |
| Malformed JSON | ValueError raised |
| Missing fields | ValueError with field name |
| Invalid PARA category | ValueError with allowed values |
| LLM timeout | Fallback to stub |

### Contract Tests

| Contract | Test |
|----------|------|
| Action tiering | `decide_action_mode("low", 0.85) == AUTO` |
| Action tiering | `decide_action_mode("medium", 0.75) == SUGGEST` |
| Provider routing | LM Studio preferred over OpenAI |

---

## Implementation Order

1. Create `src/mind_lite/organize/classify_llm.py`
2. Create `src/mind_lite/links/propose_llm.py`
3. Update `organize_classify()` to use classify_llm
4. Update `links_propose()` to use propose_llm
5. Add anti-spam controls
6. Add error handling + fallback
7. Write tests
8. Update docs

---

## Metrics to Track

| Metric | Target | Current |
|--------|--------|---------|
| False-link rate | < 15% | TBD |
| Acceptance rate (auto) | > 80% | TBD |
| Acceptance rate (suggest) | > 50% | TBD |
| LLM latency | < 2s per batch | TBD |
