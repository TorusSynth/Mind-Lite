# Mind Lite - Calm UX Rules (V1)

**Status:** Approved for Prebuild Gate  
**Last Updated:** 2026-02-18

---

## UX Goal

Mind Lite should reduce cognitive burden, not create more decisions than the value it returns.

---

## Friction Budget

- Daily triage flow: <= 7 interactions
- Approve low-risk change groups: <= 3 interactions
- Rollback last batch: <= 2 interactions
- Open "next actions" list: <= 2 interactions

---

## Interface Principles

- Show current run state clearly at all times
- Group decisions by change type, not by individual file first
- Provide diff preview before structural approvals
- Keep dangerous actions visually distinct
- Use clear, plain language labels

---

## Attention Protection Rules

- No interruptive prompts during capture
- Review prompts are batched, not constant
- Notifications default to digest mode
- Weekly review has explicit start and end state

---

## Session Design Rules

- Default to one primary task focus per session
- Hide non-critical controls until requested
- Use progressive disclosure for advanced diagnostics
- Keep failure messaging actionable (what failed, what next, rollback path)

---

## Trust Rules

- Never hide provider usage (local vs fallback)
- Always show why a structural suggestion exists
- Always show rollback availability for applied batches

---

## UX Failure Criteria

Rework interaction design if either occurs for 2 consecutive weeks:

- User reports rising anxiety/compulsive checking
- Weekly review completion drops below 70%

---

## Verification Checks (Required Before GO)

- Pilot users (you + one optional reviewer) can complete daily triage within friction budget
- Rollback action is discoverable in <= 10 seconds from review view
- Provider usage visibility is present on every routed answer
