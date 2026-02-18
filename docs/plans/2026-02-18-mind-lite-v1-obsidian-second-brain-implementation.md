# Mind Lite v1 Obsidian Second Brain Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local-first, Obsidian-native second brain system that organizes existing vault notes, improves graph connectivity, supports task workflows, and publishes quality-gated content to GOM.

**Architecture:** Mind Lite uses staged onboarding by folder, risk-tiered change actions, LM Studio as default provider, OpenAI fallback via policy gates, and strict safety controls (diff preview, snapshots, rollback, idempotency, audit logs). Publishing uses an editorial gate and stage-aware scoring before release.

**Tech Stack:** FastAPI, Python, SQLite, vector DB (Qdrant/Chroma), Obsidian plugin (TypeScript), LM Studio, OpenAI API, Docker, pytest.

---

## Scope Lock (Approved)

- Hybrid automation
- Guided staged onboarding
- Folder-based rollout, active projects first
- PARA primary + secondary labels
- Soft standardization
- Batch approval by change type
- Confidence thresholds: `0.80` auto low-risk, `0.70` suggest medium-risk
- LM Studio local default + OpenAI fallback
- Sensitive cloud gate + $30 monthly cap
- Strict GOM editorial gate
- Auto-safe mode on repeated quality failures

---

## Capability Workstreams

1. Contracts and safety policy
2. Onboarding orchestrator
3. Action tiering and PARA assignment
4. Linking quality controls
5. Routing, privacy, and budget controls
6. Obsidian review UX
7. GOM gate and publishing flow
8. Benchmark and portfolio evidence

---

## Pre-Build Exit Criteria

Before implementation starts:

- Documentation set is internally consistent
- Human-readable behavior is clear for non-technical review
- Policies are explicit enough to write tests against
- Failure behavior is defined and recoverable

---

## Build Exit Criteria (V1)

- Safety: rollback + idempotency proven
- Quality: organization/link/publish thresholds met
- Privacy: sensitivity gate blocks cloud leakage
- Cost: cap behavior verified with local-only continuation
- UX: daily and weekly Obsidian workflows validated
- Evidence: benchmark and before/after reports generated

---

## Notes

This plan intentionally prioritizes trust and usability over aggressive autonomy.

Coding should begin only after documentation approval.
