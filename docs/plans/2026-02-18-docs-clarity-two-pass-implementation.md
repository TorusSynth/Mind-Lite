# Docs Clarity Two-Pass Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute a narrative-first two-pass documentation clarity upgrade, then complete self sign-off to unlock implementation work.

**Architecture:** Work in two passes. Pass 1 upgrades high-impact docs plus a new approval rubric; Pass 2 aligns remaining docs to the same structure and terminology. Finish with a coherence sweep and explicit self sign-off record.

**Tech Stack:** Markdown, Git, repository documentation conventions

---

### Task 1: Add Approval Rubric Doc

**Files:**
- Create: `docs/specs/docs-approval-rubric.md`
- Reference: `README.md`
- Reference: `docs/plans/2026-02-18-docs-clarity-self-signoff-design.md`

**Step 1: Write the failing review checks**

```markdown
## Initial Review Result

- [ ] Coherence: reader can follow end-to-end without re-interpretation
- [ ] Consistency: terms and phase names match across docs
- [ ] Decision visibility: major decisions have clear rationale
- [ ] Actionability: clear next-doc pointers and next action
```

**Step 2: Run check to verify failure state exists**

Run: `git grep -n "\[ \]" docs/specs/docs-approval-rubric.md`
Expected: PASS with checklist lines present (indicates unresolved checks)

**Step 3: Write minimal implementation**

```markdown
# Docs Approval Rubric

## Purpose
...

## Scoring Bands
...

## Sign-Off Checklist
...

## Decision Log Template
...
```

**Step 4: Run verification check**

Run: `git grep -n "^## " docs/specs/docs-approval-rubric.md`
Expected: PASS with expected section headers

**Step 5: Commit**

```bash
git add docs/specs/docs-approval-rubric.md
git commit -m "docs: add narrative clarity approval rubric"
```

### Task 2: Pass 1 - Rewrite Entry and Roadmap Docs

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`

**Step 1: Write failing clarity assertions in working notes**

```markdown
- README intro is too broad for first-time reader
- ROADMAP phase exits are not immediately skimmable
- Reading order between docs is implied, not explicit
```

**Step 2: Run baseline check before edits**

Run: `git diff -- README.md ROADMAP.md`
Expected: no doc-clarity edits yet

**Step 3: Write minimal implementation**

```markdown
## In each file, enforce:
1. Purpose at top
2. Scope (in/out)
3. Current status
4. Read-next links
```

**Step 4: Run verification check**

Run: `git diff -- README.md ROADMAP.md`
Expected: clear structure, improved reader flow, explicit cross-links

**Step 5: Commit**

```bash
git add README.md ROADMAP.md
git commit -m "docs: clarify entrypoint and roadmap narrative"
```

### Task 3: Pass 1 - Normalize Architecture and API Docs

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `API.md`

**Step 1: Write failing terminology checks**

```markdown
- Core terms must match README/ROADMAP exactly
- Routing and gate language must not conflict
```

**Step 2: Run baseline check**

Run: `git diff -- ARCHITECTURE.md API.md`
Expected: no pass-1 normalization yet

**Step 3: Write minimal implementation**

```markdown
## Terminology Contract
- Hybrid automation
- Local-first routing
- Cloud fallback gate
- Editorial publish gate
```

**Step 4: Run verification check**

Run: `git diff -- ARCHITECTURE.md API.md`
Expected: aligned terms and reduced ambiguity

**Step 5: Commit**

```bash
git add ARCHITECTURE.md API.md
git commit -m "docs: align architecture and api terminology"
```

### Task 4: Pass 1 - Tighten Core Specs

**Files:**
- Modify: `docs/specs/calm-ux-rules.md`
- Modify: `docs/specs/git-bootstrap-plan.md`
- Modify: `docs/specs/prebuild-go-no-go-checklist.md`
- Modify: `docs/specs/provenance-lineage-contract.md`
- Modify: `docs/specs/task-workflow-doctrine.md`
- Modify: `docs/specs/threat-model-v1.md`

**Step 1: Write failing overlap checks**

```markdown
- Duplicate policy statements across specs
- Missing or weak "what to read next" pointers
- Mixed tone and inconsistent section order
```

**Step 2: Run baseline check**

Run: `git diff -- docs/specs/`
Expected: only previous committed changes visible

**Step 3: Write minimal implementation**

```markdown
## For each spec add or normalize:
- Purpose
- Scope
- Key rules
- Operational notes
- Read-next links
```

**Step 4: Run verification check**

Run: `git diff -- docs/specs/`
Expected: consistent structure and reduced overlap

**Step 5: Commit**

```bash
git add docs/specs/
git commit -m "docs: tighten core specs for narrative clarity"
```

### Task 5: Pass 2 - Align Remaining Top-Level Docs

**Files:**
- Modify: `FOUNDATION.md`
- Modify: `DECISIONS.md`
- Modify: `SECOND_BRAIN.md`
- Modify: `GOM.md`
- Modify: `INTEGRATIONS.md`

**Step 1: Write failing consistency checks**

```markdown
- Missing shared section contract in one or more docs
- Inconsistent reference style for linked docs
```

**Step 2: Run baseline check**

Run: `git diff -- FOUNDATION.md DECISIONS.md SECOND_BRAIN.md GOM.md INTEGRATIONS.md`
Expected: no pass-2 edits yet

**Step 3: Write minimal implementation**

```markdown
## Standard section order:
1. Purpose
2. Scope
3. Current status
4. Core content
5. Read next
```

**Step 4: Run verification check**

Run: `git diff -- FOUNDATION.md DECISIONS.md SECOND_BRAIN.md GOM.md INTEGRATIONS.md`
Expected: uniform structure and clearer progression

**Step 5: Commit**

```bash
git add FOUNDATION.md DECISIONS.md SECOND_BRAIN.md GOM.md INTEGRATIONS.md
git commit -m "docs: align remaining top-level documentation"
```

### Task 6: Final Coherence Sweep and Self Sign-Off

**Files:**
- Modify: `docs/specs/docs-approval-rubric.md`
- Create: `docs/plans/2026-02-18-docs-clarity-self-signoff-record.md`

**Step 1: Write failing final checklist state**

```markdown
## Final Sign-Off State

- [ ] All high-impact docs pass clarity review
- [ ] All remaining docs aligned to shared structure
- [ ] No unresolved contradiction found in core claims
- [ ] Read-next links form a coherent path
```

**Step 2: Run baseline check before sign-off**

Run: `git grep -n "\[ \]" docs/specs/docs-approval-rubric.md`
Expected: checklist still unresolved

**Step 3: Write minimal implementation**

```markdown
# Docs Clarity Self Sign-Off Record

## Result
- Outcome: Approved
- Reviewer: Self
- Date: 2026-02-18

## Notes
- Key improvements made
- Remaining minor follow-ups (if any)
```

**Step 4: Run verification check**

Run: `git grep -n "\[x\]" docs/specs/docs-approval-rubric.md`
Expected: completed checks are present

**Step 5: Commit**

```bash
git add docs/specs/docs-approval-rubric.md docs/plans/2026-02-18-docs-clarity-self-signoff-record.md
git commit -m "docs: complete clarity sign-off and record approval"
```

---

## Global Guardrails

- Do not change product behavior or policy thresholds.
- Prefer concise, explicit language over broad aspirational phrasing.
- Preserve existing intent; improve readability and navigability.
- Keep all edits ASCII unless a file already requires Unicode.
