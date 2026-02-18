# Mind Lite - Task Workflow Doctrine (V1)

**Status:** Approved for Prebuild Gate  
**Last Updated:** 2026-02-18

---

## Purpose

Define how Mind Lite reduces daily cognitive load by turning notes into clear next actions, without replacing user judgment.

---

## Daily Workflow (Light)

1. Run `Mind Lite: Daily Triage`
2. Process inbox and new notes in current priority folders
3. Apply low-risk auto actions (`>= 0.80` confidence)
4. Review medium-risk suggestions quickly by change type
5. Produce a "Today Next Actions" list

### Daily Failure Handling

- If confidence quality drops, switch to suggestion-heavy mode
- If run enters `auto_safe_mode`, skip structural actions and continue only low-risk triage
- If daily triage exceeds time budget, reduce suggestion volume by folder priority

### Daily Output Contract

- Max 5 suggested next actions
- Each action must include source note references
- At least one action marked "high leverage"

---

## Weekly Workflow (Deep)

1. Run `Mind Lite: Weekly Deep Review`
2. Review folder batch profile and graph changes
3. Approve/reject medium-risk structural proposals
4. Review publish candidates and revision queue
5. Generate weekly recap with unresolved blockers

### Weekly Escalation Rules

- If structural acceptance rate < 70%, review prompts/policies before next batch
- If false-link rate >= 10%, reduce linking aggressiveness and rerun on pilot folder
- If publish queue failures > 40%, tighten draft criteria before scoring

### Weekly Output Contract

- Approved/rejected proposal summary
- Graph quality delta summary
- GOM queue summary (`seed/sprout/tree`)
- Top 3 priorities for next week

---

## Command-to-Outcome Map

- `Analyze Current Folder` -> run profile and proposal inventory
- `Run Safe Auto Pass` -> low-risk enrichments with snapshot
- `Review Structural Suggestions` -> batch decision UI by change type
- `Apply Approved Changes` -> deterministic apply with run audit
- `Roll Back Last Batch` -> last batch fully reverted
- `Prepare GOM Draft` -> draft enters scoring pipeline
- `Publish to GOM (After Gate)` -> publish only if all gates pass

---

## Productivity KPIs

- Time to first actionable task after opening vault: target <= 3 minutes
- Resume-without-restart rate (weekly self-check): target >= 80%
- Weekly review completion rate: target >= 90%
- Structural suggestion acceptance rate: target >= 80%

---

## Portfolio Evidence Hooks

- Store weekly KPI snapshots for trend graphing
- Include one "before vs after" case per active folder
- Track time-saved estimates from accepted suggestions

---

## Stop Conditions

Mind Lite workflow must be re-tuned if either condition is true for 2 consecutive weeks:

- Daily triage exceeds 15 minutes on average
- Suggested tasks are judged "not useful" in > 30% of cases
