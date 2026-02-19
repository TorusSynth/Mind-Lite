# Phase E: Obsidian UX and Review Workflow Design

## Goal

Build an Obsidian plugin that provides command-first UX for all Mind Lite operations, connecting to the local API at localhost:8000.

## Exit Criteria

- Core command set finalized
- Review panel states documented
- Pilot review cycle usable end-to-end

---

## Architecture

### Project Structure

```
obsidian-plugin/
├── src/
│   ├── main.ts                 # Plugin entry, register commands
│   ├── api/
│   │   └── client.ts           # HTTP client for localhost:8000
│   ├── features/
│   │   ├── onboarding/
│   │   │   ├── analyze-folder.ts
│   │   │   └── modals/
│   │   │       ├── AnalyzeModal.ts
│   │   │       └── RunStatusModal.ts
│   │   ├── organize/
│   │   │   ├── classify.ts
│   │   │   └── modals/
│   │   │       └── ReviewModal.ts
│   │   ├── links/
│   │   │   ├── propose-links.ts
│   │   │   └── modals/
│   │   │       └── LinksReviewModal.ts
│   │   ├── publish/
│   │   │   ├── gom-flow.ts
│   │   │   └── modals/
│   │   │       ├── PrepareModal.ts
│   │   │       └── GateResultsModal.ts
│   │   └── runs/
│   │       ├── history.ts
│   │       └── modals/
│   │           ├── RunHistoryModal.ts
│   │           └── RollbackModal.ts
│   ├── modals/
│   │   └── base.ts             # Shared modal utilities
│   └── types/
│       └── api.ts              # API response types
├── manifest.json
├── styles.css
├── tsconfig.json
└── package.json
```

### Tech Stack

- Plain TypeScript (no framework)
- Obsidian Plugin API
- esbuild for bundling
- localhost:8000 API connection

---

## Commands

| Command | API Endpoint | Modal |
|---------|--------------|-------|
| `Mind Lite: Analyze Folder` | `POST /onboarding/analyze-folder` | AnalyzeModal (folder picker → progress → results) |
| `Mind Lite: Review Proposals` | `GET /runs/{id}/proposals` | ReviewModal (grouped list, approve/reject) |
| `Mind Lite: Apply Approved` | `POST /runs/{id}/apply` | ConfirmModal → success/error |
| `Mind Lite: Rollback` | `POST /runs/{id}/rollback` | RollbackModal (confirm → execute) |
| `Mind Lite: Daily Triage` | `POST /onboarding/analyze-folder` (active folder) | Quick review modal |
| `Mind Lite: Weekly Deep Review` | `GET /runs` | RunHistoryModal → drill into runs |
| `Mind Lite: Propose Links` | `POST /links/propose` | LinksReviewModal |
| `Mind Lite: Apply Links` | `POST /links/apply` | ConfirmModal |
| `Mind Lite: Publish to GOM` | `POST /publish/prepare` → `score` → `mark-for-gom` | Multi-step wizard |

---

## API Client

```typescript
// src/api/client.ts
const API_BASE = 'http://localhost:8000';

export async function apiGet<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`);
  if (!resp.ok) throw new APIError(resp.status, await resp.text());
  return resp.json();
}

export async function apiPost<T>(path: string, body?: object): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) throw new APIError(resp.status, await resp.text());
  return resp.json();
}

export class APIError extends Error {
  constructor(public status: number, message: string) {
    super(`API Error ${status}: ${message}`);
  }
}
```

- Single base URL: `localhost:8000`
- Typed responses via `types/api.ts`
- Error handling surfaces in modals

---

## Modal Patterns

### Base Modal (`src/modals/base.ts`)

- Extends `App` and `Modal` from Obsidian API
- Common methods: `showError()`, `showLoading()`, `setButtons()`
- Consistent styling via `styles.css`

### Review Modal (most complex)

- Sections: Auto-approved, Awaiting Review, Failed
- Each proposal shows: note title, change type, confidence, diff preview
- Actions: Approve All, Approve Selected, Reject, Cancel

### AnalyzeModal Flow

1. Folder picker (default: current folder)
2. "Analyze" button → POST `/onboarding/analyze-folder`
3. Loading state while API processes
4. Results: note count, proposal counts by risk tier
5. "Review Proposals" button → open ReviewModal

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| API unreachable | Modal: "Mind Lite API not running. Start with `python3 -m mind_lite.api`" |
| API error (4xx/5xx) | Modal: Show error message from API, "Retry" button |
| Network timeout | Modal: "Request timed out", "Retry" button |
| Validation error | Highlight field, show inline error |

All errors surface in-modals, never silent failures. `APIError` caught at command level and displayed.

---

## Testing

- Unit tests for `api/client.ts` (mock fetch)
- Integration: manual testing against live API
- No E2E framework needed for v1

---

## Build & Distribution

```json
// package.json scripts
{
  "build": "esbuild src/main.ts --bundle --outfile=main.js --platform=browser",
  "dev": "esbuild src/main.ts --bundle --outfile=main.js --platform=browser --watch"
}
```

- Output: `main.js`, `manifest.json`, `styles.css`
- Install: Copy to `.obsidian/plugins/mind-lite/` or symlink for dev
- No npm publish for v1 (local only)

---

## Implementation Order

1. Scaffold plugin with `manifest.json`, `tsconfig.json`, `package.json`
2. Implement `api/client.ts` with typed responses
3. Build base modal utilities
4. Implement commands in order:
   - Analyze Folder (entry point)
   - Review Proposals (core workflow)
   - Apply Approved
   - Rollback
   - Propose Links
   - Apply Links
   - Daily Triage
   - Weekly Deep Review
   - Publish to GOM
5. Style with `styles.css`
6. Manual integration testing
