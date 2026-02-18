# Mind Lite - Project Overview

**Status:** Documentation-First Planning (Coding Not Started)  
**Version:** 2.0 (planning baseline)  
**Last Updated:** 2026-02-18

---

## One-Line Definition

Mind Lite is a local-first, Obsidian-native second brain engine that safely organizes existing vault notes, improves graph linking, and publishes quality-gated outputs to GOM.

---

## Why Mind Lite Exists

Mind Lite is designed to solve two problems at once:

1. **Personal utility:** turn an unorganized vault into a usable daily thinking and execution system
2. **Portfolio utility:** prove real AI engineering ability through measurable, reliable behavior

---

## What It Does for You

- Scans existing vault folders in staged onboarding batches
- Applies safe low-risk improvements automatically
- Suggests structural changes for human approval
- Reconstructs links to improve Obsidian graph usefulness
- Routes AI tasks local-first (LM Studio), then cloud fallback only when justified
- Blocks sensitive content from cloud by policy
- Publishes only quality-approved content to GOM

---

## V1 Design Decisions (Locked)

- Hybrid automation model (auto/suggest/manual)
- Guided staged onboarding
- Folder-based rollout, active project folders first
- PARA primary + secondary labels
- Soft standardization only
- Batch approval by change type
- Low-risk auto threshold: `>= 0.80`
- Medium-risk suggest threshold: `>= 0.70`
- Local runtime default: LM Studio
- Cloud fallback: OpenAI only (v1)
- Cloud budget cap: $30/month
- Repeated quality failures -> auto-safe mode
- Strict editorial gate for GOM publishing

---

## Safety and Trust Model

- Snapshot before apply
- One-click rollback for last batch
- Idempotent re-runs
- Full run audit trail
- Obsidian markdown/frontmatter/wiki-link compatibility as non-negotiable

---

## Routing and Privacy

### Local-First
- Use LM Studio by default

### Cloud Fallback
- Use OpenAI only when triggers are met (for example low confidence or timeout)
- Block cloud usage when sensitivity rules hit
- Enforce cost controls and hard budget cap

### Sensitivity Gate Inputs
- Frontmatter flags
- Tags
- Path rules
- Regex-based pattern detection

---

## Publishing to GOM

Mind Lite publishes intentionally, never by default.

- Stage-aware content flow (`seed`, `sprout`, `tree`)
- Weighted editorial rubric
- Hard-fail checks for sensitivity and grounding
- Revision queue separated from publish queue

---

## Documentation Map

- `FOUNDATION.md` - core product definition and pre-coding constraints
- `ROADMAP.md` - capability-gated phases
- `ARCHITECTURE.md` - system design and component boundaries
- `API.md` - API behavior and endpoint contracts
- `SECOND_BRAIN.md` - CODE/PARA methodology
- `GOM.md` - digital garden identity and publishing philosophy
- `INTEGRATIONS.md` - external runtime and integration strategy
- `docs/plans/` - implementation plans (for when coding starts)

---

## Current Phase

This repository is in **documentation approval mode**.

Coding starts only after documentation is reviewed and confirmed to match real user needs.
