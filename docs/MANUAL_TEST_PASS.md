# Mind Lite Manual Test Pass Guide

This guide is a full hands-on instruction manual for installing and testing Mind Lite manually.

It is written for a local developer environment and assumes no prior setup.

---

## 1. Prerequisites

- Python `3.10+`
- Node.js `18+` and npm
- Obsidian Desktop
- A local Obsidian vault to test against

Optional but useful:

- `curl` for API checks
- `jq` for readable JSON output

---

## 2. Install and Boot Mind Lite

### 2.1 Clone and install Python package

```bash
git clone https://github.com/TorusSynth/Mind-Lite.git
cd Mind-Lite
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Optional dev dependencies:

```bash
pip install -e ".[dev]"
```

### 2.2 Start API server

```bash
PYTHONPATH=src python3 -m mind_lite.api
```

Expected terminal output:

```text
Mind Lite API listening on http://127.0.0.1:8000
```

### 2.3 Build plugin

Open another terminal:

```bash
cd Mind-Lite/obsidian-plugin
npm install
npm run build
```

### 2.4 Install plugin in Obsidian

Copy files into your vault plugin folder:

- source: `Mind-Lite/obsidian-plugin/main.js`
- source: `Mind-Lite/obsidian-plugin/manifest.json`
- source: `Mind-Lite/obsidian-plugin/styles.css`
- destination: `<vault>/.obsidian/plugins/mind-lite/`

Then in Obsidian:

1. Open Settings -> Community Plugins
2. Enable Community Plugins
3. Enable `Mind Lite`

---

## 3. Preflight Checks

### 3.1 API health

```bash
curl -s http://127.0.0.1:8000/health
```

Expected: JSON with healthy status.

### 3.2 Runs list

```bash
curl -s http://127.0.0.1:8000/runs
```

Expected: JSON with `runs` array (possibly empty initially).

### 3.3 Publish queues

```bash
curl -s http://127.0.0.1:8000/publish/gom-queue
curl -s http://127.0.0.1:8000/publish/revision-queue
```

Expected: queue payloads with `count` and `items`.

---

## 4. Manual Workflow Test Plan

Use Obsidian command palette for each command and validate expected outcomes.

### 4.1 Onboarding and run lifecycle

1. Run `Mind Lite: Analyze Folder`
2. Provide a folder path when prompted
3. Confirm run status modal appears

Expected:

- run id returned
- state is shown (for example `ready_safe_auto` or `awaiting_review`)

### 4.2 Review and apply

1. Run `Mind Lite: Review Proposals`
2. Confirm proposals render by status/risk grouping
3. Run `Mind Lite: Apply Approved`

Expected:

- apply completes with user-facing notice
- no unhandled plugin errors

### 4.3 Rollback

1. Run `Mind Lite: Rollback Last Batch`
2. Confirm rollback modal
3. Execute rollback

Expected:

- rollback endpoint call succeeds
- success notice shown

### 4.4 Links flow

1. Run `Mind Lite: Propose Links`
2. Enter source note id
3. Enter candidate note ids (comma separated)
4. Verify modal shows suggestions sorted by confidence
5. Run `Mind Lite: Apply Links` with optional minimum confidence

Expected:

- apply only uses fresh suggestions
- stale suggestion guard works if propose was not run first

### 4.5 Daily and weekly workflows

1. Run `Mind Lite: Daily Triage`
2. Run `Mind Lite: Weekly Deep Review`

Expected:

- daily triage analyzes active/default folder
- weekly review displays run history and state filters

### 4.6 Publish flow (Phase F critical)

1. Run `Mind Lite: Publish to GOM`
2. Enter `draft_id`, `content`, `target`
3. Enter stage (`seed|sprout|tree`)

Validate both branches:

- **Pass path:** gate passes and flow marks for GOM queue
- **Fail path:** gate fails and flow marks for revision queue

Expected:

- gate modal shows scores + threshold
- fail path shows `hard_fail_reasons` and `recommended_actions`

---

## 5. API Contract Spot Checks (Optional but Recommended)

### 5.1 Score with valid stage

```bash
curl -s -X POST http://127.0.0.1:8000/publish/score \
  -H "Content-Type: application/json" \
  -d '{"draft_id":"draft_manual_1","content":"This is a complete paragraph with clear structure and no TODO markers.","stage":"seed"}'
```

Expected fields:

- `scores`
- `threshold`
- `gate_passed`
- `hard_fail_reasons`
- `recommended_actions`

### 5.2 Score with invalid stage

```bash
curl -s -X POST http://127.0.0.1:8000/publish/score \
  -H "Content-Type: application/json" \
  -d '{"draft_id":"draft_manual_2","content":"Reasonable content","stage":"invalid-stage"}'
```

Expected:

- `gate_passed: false`
- hard-fail reason references invalid stage

### 5.3 Revision queue visibility

```bash
curl -s http://127.0.0.1:8000/publish/revision-queue
```

Expected:

- items include failed draft diagnostics

---

## 6. Acceptance Criteria

Mark manual pass complete when all are true:

- API boots and responds on `127.0.0.1:8000`
- Plugin loads and all commands are available
- Analyze/review/apply/rollback flow runs without crashes
- Links propose/apply flow works with confidence filtering
- Publish flow supports stage-aware scoring
- Gate pass routes to GOM queue
- Gate fail routes to revision queue with diagnostics

---

## 7. Troubleshooting

### `tsc: not found`

Run in plugin folder:

```bash
npm install
```

### Plugin command does nothing

- Confirm API server is running on `http://127.0.0.1:8000`
- Check Obsidian developer console for runtime errors

### `No fresh link suggestions available`

Run `Mind Lite: Propose Links` before `Mind Lite: Apply Links`.

### Publish flow blocks unexpectedly

- Review stage value
- Inspect `hard_fail_reasons` in gate modal
- Use `recommended_actions` to revise content

---

## 8. Useful Project Commands

Backend tests:

```bash
PYTHONPATH=src python3 -m unittest discover -q
```

Plugin verify:

```bash
cd obsidian-plugin
npm run verify
```
