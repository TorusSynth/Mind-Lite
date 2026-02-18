# Mind Lite - Docs Approval Rubric

**Status:** Active  
**Last Updated:** 2026-02-18  
**Approval Mode:** Self sign-off

---

## Purpose

Use this rubric to decide whether documentation is clear enough to start implementation safely.

This is a narrative-first gate. It prioritizes readability, consistency, and decision traceability over exhaustive test-spec precision.

---

## How to Use

1. Read docs in sequence from `README.md` to the core specs in `docs/specs/`.
2. Score each dimension using the bands below.
3. Record pass/fail checks and sign-off notes.
4. Mark GO only when all required checks are complete.

---

## Scoring Dimensions

### 1) Coherence

Can a first-time reader follow the system story without re-interpreting terms or jumping between unrelated docs?

### 2) Consistency

Do terms, phase names, thresholds, and gates match across top-level docs and specs?

### 3) Decision Visibility

Can a reader quickly find why major decisions were made and where they are constrained?

### 4) Actionability

Does each core doc make the next step obvious (what to read next, what to do next)?

---

## Scoring Bands

- **4 - Clear and reliable:** ready for implementation use without clarification rounds.
- **3 - Mostly clear:** minor edits needed; does not block implementation planning.
- **2 - Partially clear:** recurring ambiguity; requires targeted rewrites.
- **1 - Unclear:** reader cannot reliably determine behavior or sequence.

Target: all dimensions score **3 or 4**, with no critical contradictions.

---

## Sign-Off Checklist

- [ ] Coherence pass completed
- [ ] Consistency pass completed
- [ ] Decision visibility pass completed
- [ ] Actionability pass completed
- [ ] Contradiction sweep completed
- [ ] Read-next links verified in core docs

---

## Sign-Off Decision

- [ ] GO - Documentation is implementation-ready under narrative-first criteria
- [ ] NO-GO - Return to doc clarity pass and resolve gaps

Reviewer: ____________________  
Date: ____________________  
Notes: ____________________

---

## Decision Log Template

Copy this block for each sign-off cycle:

```markdown
### Cycle <N> - <YYYY-MM-DD>

- Outcome: GO | NO-GO
- Coherence score: <1-4>
- Consistency score: <1-4>
- Decision visibility score: <1-4>
- Actionability score: <1-4>
- Key gaps found:
  - <gap 1>
  - <gap 2>
- Follow-up actions:
  - <action 1>
  - <action 2>
```

---

## Read Next

- `README.md` for entrypoint narrative
- `ROADMAP.md` for capability progression
- `docs/specs/prebuild-go-no-go-checklist.md` for binary coding start gate
