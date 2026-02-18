# Mind Lite - Second Brain Methodology

**Status:** Active  
**Last Updated:** 2026-02-18  
**Based on:** "Building a Second Brain" by Tiago Forte

**Contract Note:** This document defines methodology and behavioral principles. For implementation contracts and endpoint authority, use `API.md`.

---

## What Is a Second Brain?

A Second Brain is a digital archive of your most valuable memories, ideas, and knowledge. It serves as an external thinking tool that:

- Remembers what you can't
- Connects ideas across domains
- Surfaces relevant knowledge when you need it
- Helps you create and express your unique perspective

**The Problem:**
- Average person consumes 34 GB of information daily
- 76 hours/year spent looking for misplaced notes
- 26% of workday spent searching for information
- We forget 90% of what we learn within a week

**The Solution:**
A trusted system that captures, organizes, and surfaces your knowledge on demand.

---

## The CODE Framework

Mind Lite implements the CODE framework for building a Second Brain:

```
┌─────────────────────────────────────────────────────────────┐
│                      CODE Framework                          │
├─────────────────────────────────────────────────────────────┤
│  C ─── CAPTURE    │ Save what resonates                     │
│  O ─── ORGANIZE   │ Organize for actionability (PARA)       │
│  D ─── DISTILL    │ Progressive Summarization               │
│  E ─── EXPRESS    │ Show your work, create Intermediate     │
│                    Packets                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 1: Capture

**Principle:** Save what resonates, not everything.

Your brain is for having ideas, not holding them. The moment you have an insight, capture it before it evaporates.

### What to Capture

| Type | Examples |
|------|----------|
| **Stories** | Personal experiences, case studies, anecdotes |
| **Insights** | Aha moments, realizations, connections |
| **Facts** | Statistics, dates, definitions, references |
| **Quotes** | Memorable passages, aphorisms, sayings |
| **Resonances** | What moves you, provokes thought, feels important |

### Capture Sources

| Source | Mind Lite Endpoint |
|--------|-------------------|
| Manual input | `POST /capture` |
| Web clips | `POST /capture/web-clip` |
| Voice notes | `POST /capture` with `source: "voice"` |
| Documents | `POST /ingest` |
| Obsidian | Plugin commands |

### The Inbox Workflow

All captures go to an **inbox** first. This prevents analysis paralysis:

1. **Capture** → Items land in inbox
2. **Process later** → Review inbox regularly
3. **Assign PARA** → Move to Projects/Areas/Resources/Archive

```
Capture → Inbox → Process → PARA
         (no decisions needed during capture)
```

### Guidelines

- **Capture is cheap** - Don't overthink, just save
- **Trust resonance** - If it moves you, save it
- **Don't organize yet** - That's a separate step
- **Source matters** - Always preserve where it came from

---

## Step 2: Organize (PARA)

**Principle:** Organize for actionability, not by topic.

Most people organize by topic (folders like "Marketing," "Psychology," "Technology"). This fails because topics are infinite and you never know which note you'll need when.

PARA organizes by **actionability** - how soon you'll need to act on the information:

```
┌─────────────────────────────────────────────────────────────┐
│                      PARA Framework                          │
├─────────────────────────────────────────────────────────────┤
│  PROJECTS   │ Active efforts with clear outcomes           │
│              │ "Launch blog by Q2", "Write conference talk" │
│              │ HIGH ACTIONABILITY → Check daily             │
├─────────────────────────────────────────────────────────────┤
│  AREAS      │ Ongoing responsibilities                     │
│              │ Health, Finances, Career, Relationships      │
│              │ MEDIUM ACTIONABILITY → Check weekly          │
├─────────────────────────────────────────────────────────────┤
│  RESOURCES  │ Topics of ongoing interest                    │
│              │ Creativity, Design, Psychology, Cooking      │
│              │ LOW ACTIONABILITY → Check as needed          │
├─────────────────────────────────────────────────────────────┤
│  ARCHIVES   │ Completed or inactive items                   │
│              │ Finished projects, old areas                 │
│              │ REFERENCE → Search when needed               │
└─────────────────────────────────────────────────────────────┘
```

### Projects vs Areas

| Projects | Areas |
|----------|-------|
| Have a deadline | No deadline |
| Clear completion criteria | Ongoing responsibility |
| "Launch blog" | "Health" |
| "Write talk" | "Finances" |
| "Plan vacation" | "Career" |

### How PARA Flows

```
New Note → PROJECTS (active use)
    │
    ├── Project completes → ARCHIVES
    │
    ├── No active project, but relevant → AREAS
    │
    ├── Interesting topic, no area → RESOURCES
    │
    └── Not actionable now → ARCHIVES
```

### Mind Lite PARA API

```
POST /organize/projects      → Create project
POST /organize/areas         → Create area
POST /organize/notes/{id}/assign → Assign note to PARA
POST /organize/notes/{id}/archive → Archive note
GET /organize/overview       → See PARA distribution
```

---

## Step 3: Distill (Progressive Summarization)

**Principle:** Distill notes over time to surface what matters.

Progressive Summarization is a technique for preserving notes in a discoverable format by summarizing them in layers:

```
┌─────────────────────────────────────────────────────────────┐
│               Progressive Summarization                      │
├─────────────────────────────────────────────────────────────┤
│  Level 1: RAW                                                │
│  └── Original captured content                               │
│      │                                                       │
│      ▼ (bold key points)                                     │
│  Level 2: BOLDED                                             │
│  └── 10-20% of Level 1                                       │
│      │                                                       │
│      ▼ (highlight essence)                                   │
│  Level 3: HIGHLIGHTED                                        │
│  └── 10-20% of Level 2 (1-4% of original)                    │
│      │                                                       │
│      ▼ (write executive summary)                             │
│  Level 4: SUMMARY                                            │
│  └── Your distilled understanding in your words              │
└─────────────────────────────────────────────────────────────┘
```

### When to Distill

**Don't** distill every note immediately. That's premature optimization.

**Do** distill when:
- You're preparing to create something
- You're about to use the note
- You're reviewing it for a project

### The Campsite Rule

Every time you "touch" a note, leave it better than you found it:
- Add a highlight
- Add a heading
- Bold a key passage
- Add a summary

Notes you interact with most become most discoverable.

### Mind Lite Distillation API

```
POST /distill/notes/{id}/bold      → Level 2
POST /distill/notes/{id}/highlight → Level 3
POST /distill/notes/{id}/summary   → Level 4
GET /distill/notes/{id}            → Get distilled version
```

### Common Mistakes

| Mistake | Solution |
|---------|----------|
| Over-highlighting | Each level should be 10-20% of previous |
| Highlighting without purpose | Only distill when preparing to create |
| Making it difficult | Trust intuition, don't over-analyze |

---

## Step 4: Express

**Principle:** Show your work. Create Intermediate Packets.

Your Second Brain exists to help you create and share. The Express step is about transforming your knowledge into outputs.

### Intermediate Packets

Instead of creating from scratch, work with "packets" - reusable building blocks:

| Packet Type | Examples |
|-------------|----------|
| **Distilled notes** | Summaries, key points from reading |
| **Outtakes** | Content cut from previous projects |
| **Work-in-process** | Drafts, outlines, research |
| **Final deliverables** | Completed reports, articles, slides |
| **Others' work** | Templates, references, examples |

### Assembly Over Creation

Professional creatives don't start with blank slates. They:
1. Assemble relevant packets
2. Rearrange and combine
3. Add their unique perspective
4. Fill gaps

### Retrieval Methods

| Method | Use When |
|--------|----------|
| **Search** | You know what you're looking for |
| **Browse** | Exploring a project/area folder |
| **Tags** | Gathering notes across categories |
| **Serendipity** | Discovering unexpected connections |

### Mind Lite Express Features

```
POST /links                    → Create note links
GET /links/backlinks/{id}      → Find connections
GET /links/related/{id}        → Semantic related notes
POST /publish/mark-for-gom     → Prepare for publication
POST /publish/export-for-gom   → Export for digital garden
```

---

## The Second Brain Mindset

### Shifts in Thinking

| From | To |
|------|-----|
| Remember everything | Offload to system |
| Organize by topic | Organize by actionability |
| Capture is storage | Capture is beginning of process |
| Notes are static | Notes evolve through distillation |
| Creation from scratch | Assembly from packets |
| Private knowledge | Shareable wisdom |

### The Superpowers

A Second Brain gives you:

1. **Make ideas concrete** - Get them out of your head
2. **Reveal associations** - Connect across domains
3. **Incubate over time** - Ideas improve with age
4. **Sharpen perspective** - Your unique lens emerges

### The Promise

With a Second Brain, you can:
- Find anything you've learned within seconds
- Move projects forward consistently
- Save your best thinking (don't repeat it)
- Connect ideas across domains
- Share work confidently
- Turn work "off" and relax

---

## Mind Lite Implementation

Mind Lite implements CODE with these features:

| CODE Step | Mind Lite Feature | API Prefix |
|-----------|-------------------|------------|
| Capture | Quick capture, inbox, web clips | `/capture` |
| Organize | PARA (Projects, Areas, Resources, Archives) | `/organize` |
| Distill | Progressive Summarization (4 levels) | `/distill` |
| Express | Linking, publishing, RAG queries | `/links`, `/publish`, `/ask` |

### The Complete Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   Mind Lite Workflow                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  CAPTURE                    ORGANIZE                         │
│  ┌─────────┐               ┌─────────┐                       │
│  │ Fleeting│──────────────▶│  Inbox  │                       │
│  │   Note  │               │         │                       │
│  └─────────┘               └────┬────┘                       │
│  ┌─────────┐                    │                            │
│  │ Web Clip│────────────────────┤                            │
│  └─────────┘                    ▼                            │
│  ┌─────────┐               ┌─────────┐                       │
│  │ Document│──────────────▶│  PARA   │                       │
│  └─────────┘               │Projects │                       │
│                            │ Areas   │                       │
│                            │Resources│                       │
│                            │Archive  │                       │
│                            └────┬────┘                       │
│                                 │                            │
│  DISTILL                        │                            │
│  ┌─────────┐                    │                            │
│  │ Level 1 │◀───────────────────┘                            │
│  │  (Raw)  │                                                │
│  └────┬────┘                                                │
│       │ Bold key points                                     │
│       ▼                                                     │
│  ┌─────────┐                                                │
│  │ Level 2 │                                                │
│  │(Bolded) │                                                │
│  └────┬────┘                                                │
│       │ Highlight essence                                   │
│       ▼                                                     │
│  ┌─────────┐                                                │
│  │ Level 3 │                                                │
│  │(Highlight│                                               │
│  └────┬────┘                                                │
│       │ Write summary                                       │
│       ▼                                                     │
│  ┌─────────┐                                                │
│  │ Level 4 │                                                │
│  │(Summary)│                                                │
│  └────┬────┘                                                │
│       │                                                     │
│  EXPRESS                                                     │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                  │
│  │  Links  │───▶│   RAG   │───▶│Publish  │                  │
│  │(Connect)│    │ (Query) │    │  (GOM)  │                  │
│  └─────────┘    └─────────┘    └─────────┘                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## References

- "Building a Second Brain" by Tiago Forte
- PARA Method: https://fortelabs.com/blog/para-method/
- Progressive Summarization: https://fortelabs.com/blog/progressive-summarization-a-practical-technique-for-designing-discoverable-notes/
- Intermediate Packets: https://fortelabs.com/blog/how-to-create-an-intermediate-packet/
