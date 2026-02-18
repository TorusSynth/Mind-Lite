# Mind Lite - V1 Evaluation Scorecard

**Status:** Approved for Prebuild Gate  
**Last Updated:** 2026-02-18

---

## Dataset Plan

- Total notes: 300
- PARA classification: 150
- Link relevance: 100
- Publish readiness/rubric: 50
- Split: 70% tune, 15% validation, 15% locked test

---

## Core Metrics and Thresholds

- PARA macro-F1: target >= 0.80
- Structural suggestion acceptance rate: target >= 0.80
- Link false-positive rate: target < 0.10
- Link acceptance rate: target >= 0.80
- Rollback success rate: target = 1.00
- Idempotency drift failures: target = 0 on validation reruns
- Publish gate precision (safe and quality): target >= 0.85

---

## Routing and Cost Metrics

- Local-first utilization rate: target >= 0.70 of total requests
- Fallback effectiveness uplift: target >= 0.15 acceptance improvement on fallback-triggered subset
- Budget policy correctness: warnings at 70/90, hard-stop at 100 verified

---

## Release Blocking Rules

Block phase progression if any condition is true:

- rollback success < 100%
- false-link rate >= 10%
- sensitivity gate leaks protected data in validation tests
- publish hard-fail checks can be bypassed

---

## Measurement Cadence

- Run full benchmark before each phase exit
- Run focused regression checks after policy/routing threshold changes
- Save scorecard snapshots with timestamp and config version

---

## Failure Probe Set (Minimum)

- 10 intentionally ambiguous PARA samples
- 10 link-spam trap samples
- 10 sensitive-content cloud-routing trap samples
- 10 publish-gate bypass attempt samples

Any failure probe regression blocks progression until corrected.

---

## Evidence Pack Requirements

- before/after vault graph summary
- benchmark metrics report
- rollback and failure drill report
- local vs fallback quality/cost summary
