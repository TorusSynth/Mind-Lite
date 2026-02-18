# Phase A Contracts Bootstrap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a minimal, test-first backend foundation for Mind Lite Phase A with an explicit policy contract for action-tier decisions.

**Architecture:** Build a tiny Python package under `src/mind_lite` with one contract module that maps risk/confidence to action mode (`auto`, `suggest`, `manual`). Add `pytest`-based tests that define expected behavior first, then implement the smallest code required. Keep this PR intentionally narrow: no API server, no persistence, no routing runtime.

**Tech Stack:** Python 3, pytest

---

### Task 1: Create Python project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/mind_lite/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Write the failing test command expectation**

Run: `python -m pytest -q`
Expected: FAIL because `pytest` is not configured and no package layout exists.

**Step 2: Run command to verify failure**

Run: `python -m pytest -q`
Expected: FAIL with missing test framework or import errors.

**Step 3: Write minimal scaffold implementation**

```toml
[project]
name = "mind-lite"
version = "0.1.0"
requires-python = ">=3.10"

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# src/mind_lite/__init__.py
"""Mind Lite package."""
```

**Step 4: Run test command to verify scaffold readiness**

Run: `python -m pytest -q`
Expected: PASS with `0 tests` collected, no import/config errors.

**Step 5: Commit**

```bash
git add pyproject.toml src/mind_lite/__init__.py tests/__init__.py
git commit -m "build: add minimal python project scaffold"
```

### Task 2: Define action-tier policy contract with failing tests

**Files:**
- Create: `tests/contracts/test_action_tiering_policy.py`

**Step 1: Write the failing test**

```python
import pytest

from mind_lite.contracts.action_tiering import ActionMode, decide_action_mode


def test_low_risk_auto_at_threshold():
    assert decide_action_mode("low", 0.80) is ActionMode.AUTO


def test_low_risk_manual_below_threshold():
    assert decide_action_mode("low", 0.79) is ActionMode.MANUAL


def test_medium_risk_suggest_at_threshold():
    assert decide_action_mode("medium", 0.70) is ActionMode.SUGGEST


def test_medium_risk_manual_below_threshold():
    assert decide_action_mode("medium", 0.69) is ActionMode.MANUAL


def test_high_risk_always_manual():
    assert decide_action_mode("high", 0.99) is ActionMode.MANUAL


def test_invalid_risk_tier_raises():
    with pytest.raises(ValueError):
        decide_action_mode("unknown", 0.90)


def test_out_of_range_confidence_raises():
    with pytest.raises(ValueError):
        decide_action_mode("low", 1.01)
```

**Step 2: Run test to verify failure**

Run: `python -m pytest tests/contracts/test_action_tiering_policy.py -q`
Expected: FAIL with import error (`mind_lite.contracts` not found).

**Step 3: Commit test file only**

```bash
git add tests/contracts/test_action_tiering_policy.py
git commit -m "test: define failing action-tiering policy contract"
```

### Task 3: Implement minimal action-tier policy module

**Files:**
- Create: `src/mind_lite/contracts/__init__.py`
- Create: `src/mind_lite/contracts/action_tiering.py`

**Step 1: Write minimal implementation**

```python
from enum import Enum


class ActionMode(str, Enum):
    AUTO = "auto"
    SUGGEST = "suggest"
    MANUAL = "manual"


def decide_action_mode(risk_tier: str, confidence: float) -> ActionMode:
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    if risk_tier == "high":
        return ActionMode.MANUAL
    if risk_tier == "medium":
        return ActionMode.SUGGEST if confidence >= 0.70 else ActionMode.MANUAL
    if risk_tier == "low":
        return ActionMode.AUTO if confidence >= 0.80 else ActionMode.MANUAL

    raise ValueError(f"unknown risk tier: {risk_tier}")
```

**Step 2: Run targeted tests to verify green**

Run: `python -m pytest tests/contracts/test_action_tiering_policy.py -q`
Expected: PASS (all tests green).

**Step 3: Run full suite**

Run: `python -m pytest -q`
Expected: PASS (all tests green).

**Step 4: Commit implementation**

```bash
git add src/mind_lite/contracts/__init__.py src/mind_lite/contracts/action_tiering.py
git commit -m "feat: add action-tiering policy contract"
```

### Task 4: Document the implemented contract

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `API.md`

**Step 1: Add implementation status note for the new contract**

```markdown
## Phase A Implementation Status

- Action-tiering contract implemented in `src/mind_lite/contracts/action_tiering.py`
- Covered by tests in `tests/contracts/test_action_tiering_policy.py`
```

**Step 2: Verify docs mention concrete file paths**

Run: `python -m pytest -q`
Expected: PASS (no behavior change).

**Step 3: Commit docs update**

```bash
git add ARCHITECTURE.md API.md
git commit -m "docs: record phase-a action-tiering contract status"
```

---

## Guardrails

- Do not add FastAPI endpoints in this PR.
- Do not add persistence, snapshots, or routing logic yet.
- Keep contract function deterministic and pure.
- Keep risk tiers and thresholds aligned to approved docs (`low >= 0.80`, `medium >= 0.70`, `high = manual`).
