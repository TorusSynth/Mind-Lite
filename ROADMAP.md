# Mind Lite - Capability Roadmap v2.0

**Status:** Active  
**Last Updated:** 2026-02-19  
**Roadmap Style:** Capability-gated (not calendar-based)

---

## Why This Roadmap Changed

Mind Lite is built with assisted development workflows, so a fixed 10-week timeline is less useful than clear capability gates.

This roadmap ships by **verified outcomes**, not by dates.

---

## Purpose

This roadmap defines capability gates for Mind Lite v1. It is the planning contract for what must be true before moving between phases.

---

## Scope

### In Scope

- Capability phases from safety foundations through portfolio hardening
- Exit criteria for each phase
- Locked v1 decisions and out-of-scope boundaries

### Out of Scope

- Detailed component implementation design (see `ARCHITECTURE.md`)
- Endpoint-level behavior definitions (see `API.md`)
- Task-by-task execution sequencing (see `docs/plans/`)

---

## Product Goal

Build an Obsidian-native, local-first second brain that:

1. Organizes large existing vaults safely
2. Reconstructs useful note linking and graph context
3. Helps daily task execution through focused workflows
4. Publishes high-quality content to GOM through strict gates
5. Demonstrates portfolio-grade AI engineering quality

---

## Locked V1 Decisions

- Hybrid automation: safe auto + structural suggestions + manual high-risk
- Guided staged onboarding
- Folder-based rollout (active project folders first)
- PARA primary + secondary labeling
- Soft standardization only (never forced auto-rename in v1)
- Local-first model routing (LM Studio default)
- Cloud fallback provider: OpenAI only (v1)
- Cloud budget cap: $30/month
- Strict GOM editorial gate
- Repeated quality failure mode: auto-safe mode

---

## Capability Phases

## Phase A - Contracts and Safety Foundations

### Scope
- Obsidian compatibility contract
- Action tier policy (auto/suggest/manual)
- Confidence thresholds and quality gates
- Snapshot, rollback, idempotency, and audit requirements

### Exit Criteria
- Policy defaults documented and versioned
- Safety acceptance tests defined
- Run lifecycle states defined and documented

---

## Phase B - Vault Onboarding Engine

### Scope
- Read-only vault analysis
- Folder profiling (link density, orphan notes, metadata health)
- Staged onboarding flow
- Batch operations by folder

### Exit Criteria
- Pilot folder run works in analyze mode
- Batch state transitions documented
- Rollback checkpoints created per batch

---

## Phase C - Organization and Graph Reconstruction

### Scope
- PARA primary/secondary assignment
- Safe auto-apply for low-risk enrichments
- Suggest-only structural actions
- Link proposal engine with anti-link-spam controls

### Exit Criteria
- Low-risk actions auto-apply only when confidence >= 0.80
- Medium-risk actions routed to review when confidence >= 0.70
- False-link rate target and acceptance-rate targets defined

---

## Phase D - Model Routing and Privacy Control

### Scope
- LM Studio default local provider
- OpenAI fallback triggers
- Sensitivity gate (frontmatter/tags/path/regex)
- Budget guardrails with cap behavior

### Exit Criteria
- Fallback trigger policy documented and testable
- Sensitive-content cloud-block rules verified
- Budget warning (70/90) and hard cap (100) behavior verified

---

## Phase E - Obsidian UX and Review Workflow

**Progress:** Implemented (command surface and review workflow shipped in `obsidian-plugin/`).

### Scope
- Command surface for analyze/review/apply/rollback
- Batch approval by change type
- Run history and diagnostics
- Daily triage and weekly deep review commands

### Exit Criteria
- Core command set finalized and mapped to API endpoints
- Review panel states documented in plugin modal flows
- Pilot review cycle usable end-to-end (analyze -> review -> apply/rollback)

---

## Phase F - GOM Publishing and Editorial Gate

### Scope
- GOM stage-aware publication flow (seed/sprout/tree)
- Strict rubric scoring + hard fail checks
- Revision queue vs publish queue separation
- Obsidian-to-GOM publishing flow

### Exit Criteria
- Required metadata and sanitization checks pass
- Editorial scoring thresholds enforced
- Publish flow works from Obsidian without bypassing gate

---

## Phase G - Benchmarking and Portfolio Hardening

### Scope
- Benchmark dataset (300 labeled notes)
- Quality metrics reporting
- Reliability evidence (rollback/idempotency/failure drills)
- Before/after vault case study

### Exit Criteria
- Benchmark protocol documented
- Core metrics tracked and reviewable
- Portfolio evidence pack assembled

---

## Operating Cadence (After Onboarding)

- **Daily:** lightweight triage and low-risk enrichment
- **Weekly:** deep review and structural suggestion approvals
- **Monthly:** threshold tuning, routing review, and benchmark snapshot

---

## V1 Definition of Done

Mind Lite v1 is complete when all are true:

- Vault safety controls are implemented and verified
- Organization and linking improve real vault quality measurably
- Local-first routing with guarded cloud fallback works reliably
- Obsidian review workflow is fast and understandable
- Publishing gate prevents low-quality or sensitive output
- Benchmark evidence proves practical usefulness and engineering quality

---

## Out of Scope for V1

- Multi-user collaboration and auth
- Multi-device sync and CRDT
- Autonomous agentic execution without review
- Full GOM hosting/deployment automation
- Multi-cloud provider orchestration beyond OpenAI fallback

These remain future-phase upgrades.

---

## Read Next

1. `ARCHITECTURE.md` for system-level component boundaries
2. `API.md` for behavior contracts that satisfy roadmap gates
3. `docs/specs/prebuild-go-no-go-checklist.md` for coding start decision
