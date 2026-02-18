# GOM - Digital Garden Specification

**Status:** Active Definition  
**Last Updated:** 2026-02-18  
**Relationship:** GOM grows out of Mind Lite

**Contract Note:** GOM publishing philosophy and quality intent live here. Endpoint and workflow contract authority remains in `API.md`, `FOUNDATION.md`, and `ROADMAP.md`.

---

## What GOM Is

**GOM is your digital garden** — a curated public space where the fruits of Mind Lite become visible, navigable, and useful to others (and future you).

> Mind Lite = the inner engine (sense-making, synthesis, intention, values)  
> GOM = the living public surface (cultivated landscape of matured ideas)

GOM is **not a mirror** of Mind Lite. It is a **curated selection** of distilled knowledge, artistic work, and personal perspective on reality.

---

## Core Identity

### GOM Represents

- **Personal brand identity** — your consistent public presence
- **Knowledge fruits** — articles, guides, research, idea explorations
- **Artistic expression** — portfolio, creative works, THE GOM comic releases
- **Curated perspective** — your lens on reality, growth, and meaning

### GOM Is Not

- Not a blog (no chronological pressure)
- Not a documentation dump
- Not a mirror of private notes
- Not a social media feed

---

## Conceptual Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         MIND                                │
│              (Your inner sense-making process)              │
│                                                             │
│  Curiosity → Insight → Values → Creative Direction         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Mind Lite                              │
│           (Second Brain Habitat / Operating System)         │
│                                                             │
│  Capture → Organize → Distill → Package → Express          │
│                                                             │
│  ┌───────────┐   ┌───────────┐   ┌─────────────────────┐   │
│  │  Private  │   │   Draft   │   │   Ready for GOM     │   │
│  │   Notes   │   │   Ideas   │   │   (publish:true)    │   │
│  └───────────┘   └───────────┘   └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                                          │
                                          │ Publishing Pipeline
                                          ▼
┌─────────────────────────────────────────────────────────────┐
│                          GOM                                │
│              (Digital Garden / Public Surface)              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Curated Public Content                  │   │
│  │                                                     │   │
│  │  • Evergreen notes (concepts, frameworks)           │   │
│  │  • Knowledge packets (guides, essays)               │   │
│  │  • THE GOM comic releases                           │   │
│  │  • Portfolio / artistic work                        │   │
│  │  • Technical documentation                          │   │
│  │  • Personal research                                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Principles

### 1. One-Way Flow

```
Mind Lite  →  GOM
```

**Never the other way around.**

- GOM never edits Mind Lite
- GOM never becomes source of truth
- Mind Lite never depends on GOM

### 2. Opt-In Publishing

**Nothing is public by default.**

- Only explicitly marked content publishes
- Multiple gates before release
- Quality over quantity

### 3. Distillation Before Expression

Content must be:
- Refined to its essence
- Reviewed for accuracy
- Checked for sensitivity
- Intentionally released

### 4. Simplicity, Compassion, Accuracy

GOM reflects your values:
- Simple, clean presentation
- Compassionate, honest voice
- Accurate, well-sourced claims

---

## Content Categories

### What Gets Published

| Category | Examples |
|----------|----------|
| **Evergreen Notes** | Concepts, frameworks, distilled insights, principles |
| **Knowledge Packets** | Guides, tutorials, how-tos, explainers |
| **Research** | Personal research, idea explorations, experiments |
| **Creative Work** | THE GOM comic releases, art, visual experiments |
| **Portfolio** | Project showcases, case studies, process documentation |
| **Retrospectives** | Lessons learned, patterns, growth documentation |

### What Never Publishes

| Category | Reason |
|----------|--------|
| Inbox / Raw capture | Unprocessed |
| Drafts | Unfinished |
| Active projects | Work in progress |
| Daily logs | Private, operational |
| Sensitive info | Personal, financial |
| Status briefs | Temporary |
| Raw sources | Unmodified external |

---

## Publishing Control

### Required Frontmatter for GOM

```yaml
---
publish: true
gom: true
visibility: public
status: evergreen  # or seed, sprout, tree
---
```

### Blocking Flags

These prevent publication even with `publish: true`:

```yaml
private: true
sensitive: true
draft: true
project_status: active
```

---

## Publishing Pipeline

### Step 1: Select
Scan Mind Lite for eligible content (`publish: true`, `gom: true`, not blocked)

### Step 2: Review
Human reviews and approves:
- Preview content
- Check for sensitivity
- Verify accuracy

### Step 3: Sanitize
Before export:
- Remove private metadata
- Strip internal-only links
- Convert internal links to GOM URLs

### Step 4: Export
Generate static site:
- Apply GOM templates
- Build navigation and backlinks
- Generate final output

### Step 5: Deploy
Push to hosting platform

---

## GOM Site Characteristics

### Digital Garden Features

- **Topography over timeline** — browse by topics, not dates
- **Evergreen + editable** — pages evolve, not decay
- **Networked** — rich internal linking and trails
- **Growth stages** — seed → sprout → tree (visible maturity)
- **Slow publishing** — quality cadence, not schedule

### Visual Identity

- **Aesthetic matters** — form shapes cognition
- Clean, humane, precise design
- Reflects simplicity + compassion + accuracy
- Navigable landscape, not overwhelming feed

---

## GOM Growth Stages

Content in GOM can show its maturity:

| Stage | Description | Visual |
|-------|-------------|--------|
| **Seed** | Early idea, rough exploration | 🌱 |
| **Sprout** | Developing, partial | 🌿 |
| **Tree** | Mature, evergreen, refined | 🌳 |

This signals to readers what stage an idea is in.

---

## What GOM Does For You

### Personal Benefits

1. **Continuity across projects** — compound knowledge over time
2. **Coherent identity** — one home for art, tech, guides, philosophy
3. **Public path without social media** — depth over reach
4. **Feedback loop of refinement** — "leave it better than you found it"
5. **Portfolio platform** — showcase work and releases

### Philosophical Benefits

- **Truth as cultivation** — not performance
- **Externalized memory** — clarity and freedom
- **Curator of your reality-tunnel** — perspective worthy of structure

---

## THE GOM Comic Integration

THE GOM comic is a **canonical output** of GOM:

- Grows from clusters of notes and ideas
- Mythic narrative layer expressing philosophy through story
- Periodic releases as "harvests"
- Sits naturally alongside other content types

---

## Relationship to Mind Lite

| Aspect | Mind Lite | GOM |
|--------|-----------|-----|
| Visibility | Private | Public |
| State | Operational, raw | Curated, refined |
| Purpose | Personal productivity | Public expression |
| Content | Everything | Selected fruits |
| Flow | Source → | Destination |

---

## Success Criteria

GOM succeeds when:
- Content is useful (including to future you)
- Publishing feels intentional, not rushed
- Private content never leaks
- Garden grows slowly and sustainably
- Represents your best thinking, not all thinking
- Aesthetic reflects your values
- THE GOM comic finds a natural home

---

## Maintenance

### Ongoing
- Review publish queue weekly
- Update stale content
- Fix broken links
- Refine and improve evergreens

### Philosophy
- Old notes stay accessible
- Updated notes show evolution
- Version history visible
- Garden grows, never just accumulates

---

## Mission Statement

**GOM is a digital garden where careful thinking becomes visible** — a humane, structured, aesthetic space that documents your growth and releases your work: research, guides, experiments, and art.

It's your personal perspective on reality, cultivated over time, offered as a navigable landscape rather than a feed.
