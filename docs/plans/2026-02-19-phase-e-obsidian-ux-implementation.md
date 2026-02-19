# Phase E: Obsidian UX and Review Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local-first Obsidian plugin that exposes the full Mind Lite command surface and drives the API-backed review/apply workflow end-to-end.

**Architecture:** Create a TypeScript Obsidian plugin under `obsidian-plugin/` using feature-first modules (`onboarding`, `organize`, `links`, `publish`, `runs`). Each command opens modal UI, calls the local API (`http://localhost:8000`) through a shared client, and surfaces loading/errors/results consistently via a shared base modal utility.

**Tech Stack:** Obsidian Plugin API, TypeScript, esbuild, npm scripts, fetch API, lightweight TypeScript unit tests.

---

## Task 1: Scaffold Obsidian Plugin Project

**Files:**
- Create: `obsidian-plugin/package.json`
- Create: `obsidian-plugin/tsconfig.json`
- Create: `obsidian-plugin/manifest.json`
- Create: `obsidian-plugin/src/main.ts`
- Create: `obsidian-plugin/styles.css`

**Step 1: Write failing smoke test for plugin build output check**

```bash
mkdir -p obsidian-plugin/tests
cat > obsidian-plugin/tests/smoke.test.ts <<'EOF'
import { existsSync } from "node:fs";

if (!existsSync("obsidian-plugin/src/main.ts")) {
  throw new Error("missing plugin entrypoint");
}
EOF
```

**Step 2: Run test to verify it fails**

Run: `node obsidian-plugin/tests/smoke.test.ts`
Expected: FAIL because `obsidian-plugin/src/main.ts` does not exist.

**Step 3: Create minimal plugin scaffold**

```json
{
  "name": "mind-lite-obsidian-plugin",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "esbuild src/main.ts --bundle --outfile=main.js --platform=browser --format=cjs",
    "dev": "esbuild src/main.ts --bundle --outfile=main.js --platform=browser --format=cjs --watch",
    "test": "node tests/smoke.test.ts"
  },
  "devDependencies": {
    "esbuild": "^0.25.0",
    "typescript": "^5.6.0",
    "obsidian": "latest"
  }
}
```

```ts
// src/main.ts
import { Plugin } from "obsidian";

export default class MindLitePlugin extends Plugin {
  async onload(): Promise<void> {
    this.addCommand({
      id: "mind-lite-ping",
      name: "Mind Lite: Ping",
      callback: () => {
        new Notice("Mind Lite plugin loaded");
      },
    });
  }
}
```

**Step 4: Run test and build to verify pass**

Run: `cd obsidian-plugin && npm install && npm run test && npm run build`
Expected: PASS, and `obsidian-plugin/main.js` exists.

**Step 5: Commit**

```bash
git add obsidian-plugin/
git commit -m "feat: scaffold Obsidian plugin project"
```

---

## Task 2: Add Shared API Client and Typed Contracts

**Files:**
- Create: `obsidian-plugin/src/types/api.ts`
- Create: `obsidian-plugin/src/api/client.ts`
- Test: `obsidian-plugin/tests/api-client.test.ts`

**Step 1: Write failing API client test**

```ts
// tests/api-client.test.ts
import { apiPost } from "../src/api/client";

globalThis.fetch = async () =>
  new Response(JSON.stringify({ ok: true }), { status: 200 }) as any;

const result = await apiPost<{ ok: boolean }>("/health");
if (!result.ok) throw new Error("expected ok response");
```

**Step 2: Run test to verify it fails**

Run: `cd obsidian-plugin && node tests/api-client.test.ts`
Expected: FAIL with module not found for `src/api/client.ts`.

**Step 3: Implement typed contracts and client**

```ts
// src/api/client.ts
const API_BASE = "http://localhost:8000";

export class APIError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

async function parse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    throw new APIError(resp.status, await resp.text());
  }
  return (await resp.json()) as T;
}

export async function apiGet<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`);
  return parse<T>(resp);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return parse<T>(resp);
}
```

**Step 4: Run test to verify it passes**

Run: `cd obsidian-plugin && node tests/api-client.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add obsidian-plugin/src/api/client.ts obsidian-plugin/src/types/api.ts obsidian-plugin/tests/api-client.test.ts
git commit -m "feat: add typed localhost API client for plugin"
```

---

## Task 3: Implement Base Modal Utilities

**Files:**
- Create: `obsidian-plugin/src/modals/base.ts`
- Modify: `obsidian-plugin/styles.css`
- Test: `obsidian-plugin/tests/base-modal.test.ts`

**Step 1: Write failing test for modal helpers**

```ts
import { createErrorText } from "../src/modals/base";

const message = createErrorText("network");
if (!message.includes("network")) throw new Error("missing error text");
```

**Step 2: Run test to verify it fails**

Run: `cd obsidian-plugin && node tests/base-modal.test.ts`
Expected: FAIL because helper is missing.

**Step 3: Implement base modal and helper methods**

Include:
- `showLoading(container, label)`
- `showError(container, error)`
- `setPrimaryAction(...)`
- `setSecondaryAction(...)`

**Step 4: Run test to verify it passes**

Run: `cd obsidian-plugin && node tests/base-modal.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add obsidian-plugin/src/modals/base.ts obsidian-plugin/styles.css obsidian-plugin/tests/base-modal.test.ts
git commit -m "feat: add shared modal utilities"
```

---

## Task 4: Implement Analyze Folder + Run Status Flow

**Files:**
- Create: `obsidian-plugin/src/features/onboarding/analyze-folder.ts`
- Create: `obsidian-plugin/src/features/onboarding/modals/AnalyzeModal.ts`
- Create: `obsidian-plugin/src/features/onboarding/modals/RunStatusModal.ts`
- Modify: `obsidian-plugin/src/main.ts`
- Test: `obsidian-plugin/tests/analyze-folder.test.ts`

**Step 1: Write failing command wiring test**

Test should assert command id `mind-lite-analyze-folder` is registered.

**Step 2: Run test to verify it fails**

Run: `cd obsidian-plugin && node tests/analyze-folder.test.ts`
Expected: FAIL missing command.

**Step 3: Implement command + modal flow**

Behavior:
- Prompt folder path/default current folder
- Call `POST /onboarding/analyze-folder`
- Open run status modal with run id/state and proposal counts

**Step 4: Run test to verify it passes**

Run: `cd obsidian-plugin && node tests/analyze-folder.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add obsidian-plugin/src/features/onboarding/ obsidian-plugin/src/main.ts obsidian-plugin/tests/analyze-folder.test.ts
git commit -m "feat: add analyze folder command and run status modal"
```

---

## Task 5: Implement Review, Approve, Apply, and Rollback Commands

**Files:**
- Create: `obsidian-plugin/src/features/organize/modals/ReviewModal.ts`
- Create: `obsidian-plugin/src/features/runs/history.ts`
- Create: `obsidian-plugin/src/features/runs/modals/RollbackModal.ts`
- Modify: `obsidian-plugin/src/main.ts`
- Test: `obsidian-plugin/tests/review-apply-rollback.test.ts`

**Step 1: Write failing tests for command ids**

Assert these commands exist:
- `mind-lite-review-proposals`
- `mind-lite-apply-approved`
- `mind-lite-rollback-last-batch`

**Step 2: Run test to verify it fails**

Run: `cd obsidian-plugin && node tests/review-apply-rollback.test.ts`
Expected: FAIL missing commands.

**Step 3: Implement minimal workflow**

API mapping:
- Review: `GET /runs/{run_id}/proposals`
- Apply: `POST /runs/{run_id}/apply`
- Rollback: `POST /runs/{run_id}/rollback`

Review modal requirements:
- Group proposals by `status` + `risk_tier`
- Show confidence and reason/details
- Approve selected + approve all actions

**Step 4: Run tests to verify pass**

Run: `cd obsidian-plugin && node tests/review-apply-rollback.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add obsidian-plugin/src/features/organize/ obsidian-plugin/src/features/runs/ obsidian-plugin/src/main.ts obsidian-plugin/tests/review-apply-rollback.test.ts
git commit -m "feat: add review, apply, and rollback command workflow"
```

---

## Task 6: Implement Link Proposal and Apply Commands

**Files:**
- Create: `obsidian-plugin/src/features/links/propose-links.ts`
- Create: `obsidian-plugin/src/features/links/modals/LinksReviewModal.ts`
- Modify: `obsidian-plugin/src/main.ts`
- Test: `obsidian-plugin/tests/links-commands.test.ts`

**Step 1: Write failing tests for links command registration**

Assert command ids:
- `mind-lite-propose-links`
- `mind-lite-apply-links`

**Step 2: Run test to verify it fails**

Run: `cd obsidian-plugin && node tests/links-commands.test.ts`
Expected: FAIL missing links commands.

**Step 3: Implement links workflow**

API mapping:
- Propose: `POST /links/propose`
- Apply: `POST /links/apply`

UI:
- Links modal sorted by confidence descending
- Display reason enum and target note id
- Allow minimum confidence filter before apply

**Step 4: Run tests to verify pass**

Run: `cd obsidian-plugin && node tests/links-commands.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add obsidian-plugin/src/features/links/ obsidian-plugin/src/main.ts obsidian-plugin/tests/links-commands.test.ts
git commit -m "feat: add link proposal and apply commands"
```

---

## Task 7: Implement Daily Triage and Weekly Deep Review Commands

**Files:**
- Create: `obsidian-plugin/src/features/runs/modals/RunHistoryModal.ts`
- Modify: `obsidian-plugin/src/main.ts`
- Test: `obsidian-plugin/tests/triage-review.test.ts`

**Step 1: Write failing tests for command registration**

Assert command ids:
- `mind-lite-daily-triage`
- `mind-lite-weekly-deep-review`

**Step 2: Run test to verify it fails**

Run: `cd obsidian-plugin && node tests/triage-review.test.ts`
Expected: FAIL missing commands.

**Step 3: Implement command behavior**

- Daily triage: execute analyze on active folder + open summary modal
- Weekly review: call `GET /runs` and present run history with state filters

**Step 4: Run test to verify it passes**

Run: `cd obsidian-plugin && node tests/triage-review.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add obsidian-plugin/src/features/runs/ obsidian-plugin/src/main.ts obsidian-plugin/tests/triage-review.test.ts
git commit -m "feat: add daily triage and weekly deep review commands"
```

---

## Task 8: Implement GOM Publish Wizard Command

**Files:**
- Create: `obsidian-plugin/src/features/publish/gom-flow.ts`
- Create: `obsidian-plugin/src/features/publish/modals/PrepareModal.ts`
- Create: `obsidian-plugin/src/features/publish/modals/GateResultsModal.ts`
- Modify: `obsidian-plugin/src/main.ts`
- Test: `obsidian-plugin/tests/publish-flow.test.ts`

**Step 1: Write failing test for publish command registration**

Assert command id `mind-lite-publish-to-gom`.

**Step 2: Run test to verify it fails**

Run: `cd obsidian-plugin && node tests/publish-flow.test.ts`
Expected: FAIL missing publish command.

**Step 3: Implement publish flow wizard**

Flow:
1. `POST /publish/prepare`
2. `POST /publish/score`
3. If gate passes, `POST /publish/mark-for-gom`
4. Display staged outcome and diagnostics

**Step 4: Run test to verify it passes**

Run: `cd obsidian-plugin && node tests/publish-flow.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add obsidian-plugin/src/features/publish/ obsidian-plugin/src/main.ts obsidian-plugin/tests/publish-flow.test.ts
git commit -m "feat: add GOM publish wizard command"
```

---

## Task 9: Add End-to-End Command Registration and Build Verification

**Files:**
- Modify: `obsidian-plugin/src/main.ts`
- Modify: `obsidian-plugin/package.json`
- Create: `obsidian-plugin/tests/commands-smoke.test.ts`

**Step 1: Write failing full command set test**

Assert all command ids are registered:
- analyze, review, apply, rollback
- daily triage, weekly deep review
- propose links, apply links
- publish to GOM

**Step 2: Run test to verify it fails**

Run: `cd obsidian-plugin && node tests/commands-smoke.test.ts`
Expected: FAIL if any command is missing.

**Step 3: Ensure registration and build scripts are complete**

Add `npm run verify` script:

```json
"verify": "npm run test && npm run build"
```

**Step 4: Run verification**

Run: `cd obsidian-plugin && npm run verify`
Expected: PASS.

**Step 5: Commit**

```bash
git add obsidian-plugin/
git commit -m "test: verify full command surface and plugin build"
```

---

## Task 10: Update Docs for Phase E Completion

**Files:**
- Modify: `API.md`
- Modify: `ARCHITECTURE.md`
- Modify: `ROADMAP.md`

**Step 1: Add plugin command coverage notes to API docs**

Document command-to-endpoint mapping and local API requirement.

**Step 2: Update architecture doc with Obsidian UX implementation status**

Add status bullets for command surface + modal review workflow.

**Step 3: Update roadmap phase progress note**

Mark Phase E as implemented (or add status checkpoint bullets).

**Step 4: Verify docs references are accurate**

Run: `grep -n "Phase E\|Obsidian UX\|Mind Lite:" API.md ARCHITECTURE.md ROADMAP.md`
Expected: matching updated references.

**Step 5: Commit**

```bash
git add API.md ARCHITECTURE.md ROADMAP.md
git commit -m "docs: record Phase E Obsidian UX implementation status"
```

---

## Final Verification

Run full checks:

```bash
PYTHONPATH=src python3 -m unittest discover -q
cd obsidian-plugin && npm run verify
```

Expected:
- Python tests PASS
- Plugin tests/build PASS

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Scaffold plugin project |
| 2 | Add API client and types |
| 3 | Add shared modal utilities |
| 4 | Implement analyze flow |
| 5 | Implement review/apply/rollback |
| 6 | Implement link propose/apply |
| 7 | Implement daily/weekly commands |
| 8 | Implement GOM publish wizard |
| 9 | Verify full command surface and build |
| 10 | Update docs |
