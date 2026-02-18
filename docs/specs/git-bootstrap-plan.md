# Mind Lite - Git Bootstrap Plan

**Status:** Planned (Pre-coding)  
**Last Updated:** 2026-02-18

---

## Purpose

Define the minimum git setup sequence before coding starts, so documentation baseline is tracked and implementation can proceed in controlled commits.

---

## Scope

### In Scope

- Minimum repository bootstrapping sequence before first code work
- Baseline documentation commit expectations
- Guardrails for separating planning and implementation commits

### Out of Scope

- Branching strategy after implementation is underway
- CI/CD automation setup
- Release and deployment workflow

---

## Sequence

1. Initialize repository in project root
2. Create initial docs baseline commit
3. Create `main` branch baseline tag (optional)
4. Start implementation from Phase A in a feature branch

---

## Baseline Commit Scope

- `README.md`
- `FOUNDATION.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`
- `API.md`
- `INTEGRATIONS.md`
- `DECISIONS.md`
- `docs/specs/*`
- `docs/evals/*`
- `docs/plans/*`

---

## Guardrails

- Do not start coding before docs baseline commit exists
- Keep planning commits separate from implementation commits
- Require passing prebuild checklist before first code commit

---

## Read Next

- `docs/specs/prebuild-go-no-go-checklist.md` for coding start gate
- `docs/specs/docs-approval-rubric.md` for narrative clarity sign-off
