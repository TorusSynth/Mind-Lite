# Mind Lite - Integrations

**Status:** Active Design  
**Last Updated:** 2026-02-18

---

## Integration Principles

1. Add value without breaking Obsidian-native workflows
2. Local-first by default
3. Explicit policy before cloud usage
4. Graceful degradation on failures
5. Full observability for routing and cost behavior

---

## V1 Runtime Integrations

## 1) LM Studio (Primary Local Runtime)

Role in v1:

- Default provider for generation tasks
- Used for organization support, linking assistance, and drafting
- First choice for privacy and cost control

Why primary:

- Fast local iteration during onboarding
- Direct model experimentation
- Avoids unnecessary cloud dependency

---

## 2) OpenAI (Fallback Cloud Runtime)

Role in v1:

- Fallback only when local quality/performance trigger conditions are met
- Used under strict sensitivity and budget policy

Fallback examples:

- Local timeout
- Low confidence below threshold
- Failed grounding quality check

Controls:

- Hybrid sensitivity gate (frontmatter, tags, path, regex)
- Monthly budget cap of $30
- Warning levels at 70% and 90%
- Hard stop at 100%

---

## Optional Future Integrations (Not V1)

- Ollama as additional local runtime
- OpenMemory for cross-session memory enrichment
- External content connectors (GitHub/Notion)
- Multi-provider cloud failover

---

## Failure and Degradation Strategy

- If local runtime fails and fallback is blocked, continue in local-only reduced mode
- If cloud budget cap is hit, continue local-only mode
- Repeated quality failures trigger auto-safe mode

The system should always remain usable even with integrations partially unavailable.
