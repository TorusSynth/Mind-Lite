# Mind Lite - Technical Architecture v2.0

**Status:** Active Design  
**Last Updated:** 2026-02-18

---

## Architecture Goal

Deliver a trustworthy second brain workflow for Obsidian vaults by combining safe automation, human review, local-first AI, and quality-gated publishing.

---

## System Overview

```
Obsidian Plugin (Primary UX)
    -> API Layer (FastAPI)
        -> Onboarding and Organization Engine
        -> Linking and Retrieval Engine
        -> Routing and Privacy Engine
        -> Publishing and Editorial Gate Engine
        -> Safety and Audit Engine
            -> Storage Layer (notes, proposals, run logs, snapshots, vectors)
```

---

## Core Components

## 1) Obsidian UX Layer

Provides command-first operations:

- Analyze Current Folder
- Run Safe Auto Pass
- Review Structural Suggestions
- Apply Approved Changes
- Roll Back Last Batch
- Daily Triage
- Weekly Deep Review
- Prepare GOM Draft
- Publish to GOM (After Gate)

UI includes grouped review by change type, diff previews, run states, and diagnostics.

---

## 2) Onboarding and Organization Engine

Responsibilities:

- Folder-based onboarding runs
- Note profiling and confidence scoring
- PARA assignment (primary + secondary)
- Action tiering:
  - low-risk auto (`>=0.80`)
  - medium-risk suggest (`>=0.70`)
  - high-risk manual

Design requirement: no destructive operations during onboarding.

---

## 3) Linking and Retrieval Engine

Responsibilities:

- Generate link proposals for graph improvement
- Prevent link spam via limits and relevance thresholds
- Serve retrieval and RAG-based answering with citations

Graph quality is evaluated via orphan reduction, acceptance rate, and false-link rate.

---

## 4) Routing and Privacy Engine

### Model Routing

- Default provider: LM Studio (local)
- Fallback provider (v1): OpenAI
- Fallback triggers: low confidence, timeout, or grounding failure

### Privacy Gate

Hybrid sensitive detector checks:

- Frontmatter flags
- Tags
- Path rules
- Regex patterns

If blocked, request stays local-only.

### Cost Guardrails

- Monthly cloud cap: $30
- Warnings at 70% and 90%
- Hard stop at 100% with local-only continuation

---

## 5) Publishing and Editorial Gate Engine

Responsibilities:

- Manage publish queue and revision queue
- Score drafts with weighted rubric
- Apply hard-fail checks (sensitivity, grounding, metadata)
- Enforce stage thresholds (`seed`, `sprout`, `tree`)

Nothing reaches GOM without passing gate checks.

---

## 6) Safety and Audit Engine

Responsibilities:

- Snapshot before apply
- Rollback last batch
- Idempotency guards
- Run lifecycle tracking and audit logs

Run states:

`queued -> analyzing -> ready_safe_auto -> awaiting_review -> approved -> applied -> verified`

Failure states:

`auto_safe_mode`, `rolled_back`, `failed_needs_attention`

---

## Data Objects

- **Note** - markdown content + metadata
- **Change Proposal** - action, risk tier, confidence, rationale, status
- **Run Record** - run ID, scope, provider decisions, diagnostics
- **Snapshot** - rollback checkpoint for applied batch
- **Query Result** - answer + citations + provider trace
- **Publish Artifact** - gated content + stage + export status

---

## Reliability Rules

- Obsidian compatibility is non-negotiable
- Re-runs must be idempotent
- Repeated quality failures trigger auto-safe mode
- Structural changes require human approval

---

## Out of Scope (V1)

- Multi-device sync
- Multi-user auth and collaboration
- Autonomous unattended agents
- Multi-cloud provider orchestration
- Full GOM hosting automation

---

## Build Path

Implementation follows capability phases defined in `ROADMAP.md`.

Coding begins only after documentation approval.
