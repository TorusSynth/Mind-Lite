# Mind Lite - Foundation Document v2.0

**Status:** Active Definition  
**Last Updated:** 2026-02-18  
**Purpose:** Define what Mind Lite is, what it is not, and what must be true before coding starts

---

## What Mind Lite Is

Mind Lite is a local-first, Obsidian-native second brain engine that helps you transform an unorganized vault into an actionable knowledge system, then publish your best outputs to GOM through strict quality gates.

It is designed to be:

- **Personally useful** - better daily clarity, faster retrieval, easier execution
- **Portfolio-worthy** - clear AI engineering evidence (RAG, routing, safety, evaluation)
- **Safe by design** - controlled automation with rollback and audit trails
- **Incremental** - guided onboarding by folder, not risky one-shot rewrites

---

## Product Promise (V1)

Mind Lite v1 must deliver all of the following:

1. **Vault Onboarding** - staged folder analysis for large existing Obsidian vaults
2. **Safe Organization** - low-risk auto updates, medium-risk suggestions, high-risk manual only
3. **Graph Improvement** - relevant link proposals with anti-link-spam controls
4. **Grounded Q&A** - citation-backed retrieval and answer generation
5. **Model Routing** - LM Studio default, OpenAI fallback with policy controls
6. **Privacy Protection** - hybrid sensitive-content gate before cloud usage
7. **GOM Publishing** - strict editorial gate before public release
8. **Evidence Output** - benchmark and reliability reports for portfolio proof

---

## What Mind Lite Is NOT (V1 Exclusions)

- No multi-user collaboration
- No multi-device sync / CRDT
- No autonomous agent actions without review
- No forced global renaming/standardization
- No cloud provider mesh (OpenAI is the only fallback provider in v1)
- No direct replacement of Obsidian as source of truth

These exclusions preserve reliability and keep scope shippable.

---

## Core Operating Model

### Hybrid Automation Policy

- **Auto (low-risk):** metadata enrichments, safe tag updates, index hints
- **Suggest (medium-risk):** PARA moves, title suggestions, merge candidates
- **Manual (high-risk):** deletions, heavy rewrites, irreversible restructures

### Confidence Gates

- Low-risk auto actions require confidence `>= 0.80`
- Medium-risk suggestions require confidence `>= 0.70`
- Lower confidence routes to manual review queue

### Reliability and Recovery

- Snapshot before apply
- One-click rollback of last batch
- Idempotent re-runs (no duplicate churn)
- Full run audit trail with run IDs

---

## Obsidian-First UX Contract

Mind Lite must preserve Obsidian usability at all times:

- Keep markdown valid and readable
- Preserve frontmatter semantics
- Preserve wiki-links and embeds
- Show grouped diffs before structural approvals
- Expose run state, diagnostics, and rollback controls in plugin UI

---

## Model Strategy (V1)

### Local-First by Default

- Primary runtime: **LM Studio**

### Cloud Fallback

- Fallback provider: **OpenAI only**
- Triggered only when policy says needed (for example timeout or low confidence)
- Blocked when sensitive-content rules are hit
- Budget cap: **$30/month** with warning and hard-stop behavior

---

## Publishing Contract (Mind Lite -> GOM)

Publication is always intentional and gated.

- Nothing is public by default
- Content must pass strict editorial scoring
- Hard-fail checks block unsafe or weak outputs
- Growth stages are explicit (`seed`, `sprout`, `tree`)

---

## Minimum Object Model

### Note
- Markdown note and metadata from Obsidian vault

### Change Proposal
- Proposed change, risk tier, confidence, rationale, approval state

### Query Result
- Answer, citations, confidence, provider trace

### Publish Artifact
- Sanitized output, stage score, gate result, export status

### Run Record
- Run ID, folder scope, actions applied, rollback snapshot, diagnostics

---

## Capability-Gated Build Philosophy

Mind Lite no longer follows a fixed week-based plan.

It ships by validated capabilities:

- Contracts and policy
- Onboarding engine
- Organization and linking
- Routing and privacy
- Obsidian review UX
- GOM editorial gate
- Benchmark and portfolio evidence

See `ROADMAP.md` for capability phases.

---

## V1 Success Criteria

Mind Lite v1 is complete when all are true:

- [ ] Vault onboarding works in staged folder batches
- [ ] Auto-safe actions apply without markdown/frontmatter breakage
- [ ] Structural changes are reviewable with clear diffs
- [ ] Rollback succeeds on tested batches
- [ ] Local-first routing and guarded fallback behave as specified
- [ ] Sensitive-content policy prevents cloud leakage
- [ ] Obsidian daily and weekly workflows are usable in practice
- [ ] GOM publishing gate blocks low-quality or unsafe content
- [ ] Benchmark and reliability reports are generated

---

## Pre-Coding Requirement

Coding should not start until documentation is approved as human-readable, consistent, and sufficient to predict how Mind Lite will behave in real vault usage.

This requirement is intentional and part of project quality.
