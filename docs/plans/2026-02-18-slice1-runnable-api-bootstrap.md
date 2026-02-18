# Slice 1 Runnable API Bootstrap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a runnable local API with health and analyze-folder endpoints backed by existing onboarding analysis logic.

**Architecture:** Implement a small in-process `ApiService` (no external dependencies) and expose it via Python `http.server`. Keep run state in memory with generated run IDs. Use `unittest` tests first to lock behavior for `health`, `analyze-folder`, and run retrieval.

**Tech Stack:** Python 3 standard library, unittest

---

### Task 1: Define failing service tests

**Files:**
- Create: `tests/api/__init__.py`
- Create: `tests/api/test_api_service.py`

**Step 1: Write failing tests**
- `health()` returns `{"status": "ok"}`
- `analyze_folder()` returns `run_id`, `state`, and profile
- `get_run()` returns stored run details
- Invalid folder path raises `ValueError`

**Step 2: Verify red state**
Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service -q`
Expected: FAIL with missing `mind_lite.api.service` module.

### Task 2: Implement minimal API service

**Files:**
- Create: `src/mind_lite/api/__init__.py`
- Create: `src/mind_lite/api/service.py`

**Step 1: Implement minimal service behavior**
- `health()`
- `analyze_folder()` with in-memory run storage
- `get_run()` lookup

**Step 2: Verify green**
Run: `PYTHONPATH=src python3 -m unittest tests.api.test_api_service -q`
Expected: PASS.

### Task 3: Expose runnable HTTP server

**Files:**
- Create: `src/mind_lite/api/http_server.py`

**Step 1: Implement endpoints**
- `GET /health`
- `POST /onboarding/analyze-folder`
- `GET /runs/<run_id>`

**Step 2: Add basic server tests (function-level and route-level smoke)**
- Create: `tests/api/test_http_server.py`

**Step 3: Verify full suite**
Run: `PYTHONPATH=src python3 -m unittest discover -q`
Expected: PASS.

### Task 4: Update docs and ship

**Files:**
- Modify: `API.md`
- Modify: `ARCHITECTURE.md`

**Step 1: Add implementation status entries for Slice 1**

**Step 2: Commit sequence**
- tests commit
- implementation commit
- docs commit
