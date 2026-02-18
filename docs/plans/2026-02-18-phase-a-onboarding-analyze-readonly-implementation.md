# Phase A Onboarding Analyze Readonly Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a minimal read-only folder analysis contract that profiles markdown notes for onboarding.

**Architecture:** Add a pure analysis module under `src/mind_lite/onboarding` that scans a folder recursively for markdown files and returns a small profile object. Define behavior via failing tests first, then implement only what is needed to pass: note count, orphan note count, and link density. No write operations, no API server, no database.

**Tech Stack:** Python 3, unittest

---

### Task 1: Define failing tests for read-only folder analysis

**Files:**
- Create: `tests/onboarding/__init__.py`
- Create: `tests/onboarding/test_analyze_readonly.py`

**Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from mind_lite.onboarding.analyze_readonly import analyze_folder


class AnalyzeReadonlyTests(unittest.TestCase):
    def test_profiles_markdown_files_only(self):
        ...

    def test_counts_orphans_without_wikilinks(self):
        ...

    def test_rejects_nonexistent_folder(self):
        ...
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests.onboarding.test_analyze_readonly -q`
Expected: FAIL with module import error for `mind_lite.onboarding`.

**Step 3: Commit red tests**

```bash
git add tests/onboarding/__init__.py tests/onboarding/test_analyze_readonly.py
git commit -m "test: define failing onboarding analyze readonly contract"
```

### Task 2: Implement minimal analyze-readonly contract

**Files:**
- Create: `src/mind_lite/onboarding/__init__.py`
- Create: `src/mind_lite/onboarding/analyze_readonly.py`

**Step 1: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FolderProfile:
    note_count: int
    orphan_notes: int
    link_density: float


def analyze_folder(folder_path: str) -> FolderProfile:
    ...
```

Implementation requirements:
- Include `.md` and `.markdown` files only
- Count wiki links with `[[...]]` patterns
- Define orphan as note with zero wiki links
- Compute `link_density` as `total_links / note_count` (0.0 if no notes)
- Raise `ValueError` when folder path does not exist or is not a directory

**Step 2: Run targeted tests to verify green**

Run: `PYTHONPATH=src python3 -m unittest tests.onboarding.test_analyze_readonly -q`
Expected: PASS.

**Step 3: Run full test suite**

Run: `PYTHONPATH=src python3 -m unittest discover -q`
Expected: PASS.

**Step 4: Commit implementation**

```bash
git add src/mind_lite/onboarding/__init__.py src/mind_lite/onboarding/analyze_readonly.py
git commit -m "feat: add readonly onboarding folder analysis contract"
```

### Task 3: Record implementation status in docs

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `API.md`

**Step 1: Add status note**

```markdown
- Read-only onboarding folder analysis implemented in `src/mind_lite/onboarding/analyze_readonly.py`
- Covered by tests in `tests/onboarding/test_analyze_readonly.py`
```

**Step 2: Verify tests still pass**

Run: `PYTHONPATH=src python3 -m unittest discover -q`
Expected: PASS.

**Step 3: Commit docs**

```bash
git add ARCHITECTURE.md API.md
git commit -m "docs: record readonly onboarding analysis status"
```

### Task 4: Push branch and prepare PR

**Files:**
- Modify: none

**Step 1: Push branch**

Run: `git push -u origin phase-a/onboarding-analyze-readonly`
Expected: branch published.

**Step 2: Prepare PR summary**

Include:
- New read-only onboarding contract
- TDD proof (red then green)
- Explicit non-goals (no API, no persistence, no writes)

---

## Guardrails

- Never write to analyzed folders.
- Keep implementation pure and deterministic.
- Do not add API endpoints in this slice.
- Keep profile output limited to note count, orphan count, and link density.
