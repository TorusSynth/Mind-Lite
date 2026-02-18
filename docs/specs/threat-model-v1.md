# Mind Lite - Threat Model v1

**Status:** Approved for Prebuild Gate  
**Last Updated:** 2026-02-18

---

## Scope

Single-user local deployment with Obsidian plugin, local runtime (LM Studio), and OpenAI fallback under policy constraints.

---

## Assets to Protect

- Private vault markdown and metadata
- API credentials (OpenAI key)
- Audit logs and run history
- Rollback snapshots
- Publish artifacts before and after sanitization

---

## Threat Actors

- Accidental user misconfiguration
- Malicious/unsafe local scripts or plugins
- Prompt-injection style content in notes/sources
- Device compromise (local machine)

---

## Attack Surfaces

- Plugin command actions and approval flows
- Cloud fallback routing boundary
- Publish export boundary (private -> public)
- Snapshot storage and audit log retention

---

## Risk Register (Top V1 Risks)

- **R1: Sensitive note leaks to cloud fallback**
  - Likelihood: medium
  - Impact: critical
  - Controls: hybrid sensitivity gate, default block on protected tags/path, audit event `blocked_by_policy`

- **R2: Destructive structural mutation accepted by mistake**
  - Likelihood: medium
  - Impact: high
  - Controls: suggest-only structural actions, grouped diff preview, snapshot + rollback

- **R3: Prompt injection from note content influences unsafe actions**
  - Likelihood: medium
  - Impact: high
  - Controls: no direct execution from model text, explicit action allowlist, human approval gates

- **R4: Cost runaway from fallback loops**
  - Likelihood: low
  - Impact: medium
  - Controls: $30 cap, 70/90 warnings, hard-stop at 100%

---

## Core Controls

- Sensitivity gate blocks cloud for protected content
- Explicit approvals for medium/high-risk mutations
- Snapshot before apply and one-click rollback
- Full run audit with actor, provider, and rationale fields
- Budget cap and provider routing constraints

---

## Minimum Security Rules

- OpenAI key never stored in vault notes
- Logs cannot store full sensitive payloads
- Publish hard-fail on privacy flags
- High-risk actions never auto-applied in v1

---

## Verification Checks (Required Before GO)

- Sensitivity gate test suite includes hard-block and soft-flag samples
- Publish hard-fail checks reject known sensitive fixtures
- Rollback drill succeeds on at least 3 consecutive test runs
- Budget cap behavior tested for 70/90/100 transitions

---

## Non-Goals (V1)

- Multi-user permission model
- Remote public API exposure hardening
- Enterprise key management systems
- Zero-trust distributed deployment patterns
