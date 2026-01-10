# Claude Code Agent Usage Guide

This document helps Claude Code assist Mark with his 2026 goals tracking.

## Quick Commands

When Mark says something like:
- "log today" or "update my goals" → Add a new entry to `_data/daily.yml`
- "how am I doing" or "show progress" → Read `_data/daily.yml` and summarize
- "commit my update" → Stage changes and commit with `status-update:YYYY-MM-DD`

---

## Daily Tracking System

### Data File Location
`_data/daily.yml`

### Entry Format
```yaml
- date: 2026-01-06          # Required: YYYY-MM-DD format
  calendar: true            # Required: Did morning calendar check? (true/false)
  fitness: 45               # Required: Minutes of exercise (0 if none)
  hindi: 1                  # Required: Chapters/lessons completed (0 if none)
  mood: 4                   # Optional: 1-5 scale (1=low, 5=high)
  notes: "Good gym session" # Optional: Brief reflection
```

### Adding a New Entry

1. Read current `_data/daily.yml`
2. Append new entry at the bottom (newest last)
3. Ask Mark for each field if not provided:
   - "Did you check your calendar this morning?"
   - "How many minutes of exercise today?"
   - "Any Hindi study today?"
   - "How's your energy/mood (1-5)?"
   - "Any notes for today?"

### Example Interaction

```
Mark: "log today"

Claude: I'll help you log today's progress. Let me ask a few questions:

1. Did you check your calendar this morning?
2. How many minutes of fitness/exercise?
3. Any Hindi chapters studied?
4. Mood/energy level (1-5)?
5. Any notes?

[After getting answers, append to _data/daily.yml]
```

---

## Commit Convention

When committing updates, use this format:
```
status-update:2026-01-06
```

Full commit command:
```bash
git add _data/daily.yml && git commit -m "status-update:$(date +%Y-%m-%d)"
```

Or with a note:
```bash
git add . && git commit -m "status-update:2026-01-06 - great workout day"
```

---

## File Structure Reference

```
2026-goals/
├── _config.yml              # Jekyll config
├── _data/
│   └── daily.yml            # ← DAILY TRACKING DATA
├── index.md                 # Main dashboard
├── Goals.md                 # Goal descriptions
├── updates/
│   ├── index.md             # Latest status (coach view)
│   └── history.md           # Charts and history
├── calendaring/
│   ├── index.md
│   ├── overview.md
│   └── weeks/
├── fitness/
│   ├── index.md
│   ├── overview.md
│   └── weeks/
└── Hindi/
    ├── index.md
    └── chapters/
```

---

## Goals Reference

| Goal | Metric | Target |
|------|--------|--------|
| Calendar Mastery | Daily check | 7/7 days per week |
| Fitness | Weekly minutes | 200 min/week |
| Hindi | Chapters | 18 total |
| Work Boundaries | - | Planning phase |
| Spend Less | - | Planning phase |

---

## Updating the Coach Page

When Mark logs his daily update, also update `updates/index.md`:
1. Change the "Latest Update" date
2. Update the summary of what was worked on
3. Add entry to "Update History" table

---

## Useful Queries

**Calculate weekly fitness total:**
```
Sum fitness minutes from last 7 entries in _data/daily.yml
```

**Calculate calendar streak:**
```
Count consecutive true values for calendar field from most recent
```

**Check if on track:**
- Calendar: 5+ days/week = on track
- Fitness: Compare weekly sum to target for current week (see fitness/overview.md)
- Hindi: total chapters / 18 = progress %

---

## Sample Daily Log Flow

1. Mark says "evening update" or "log today"
2. Ask for today's data (or Mark provides it)
3. Append to `_data/daily.yml`
4. Update `updates/index.md` with latest status
5. Commit with `status-update:YYYY-MM-DD`
6. Optionally push to GitHub

---

## Don't Forget

- Always append to daily.yml, never overwrite
- Use today's actual date
- Validate yaml syntax before saving
- The history page auto-generates charts from the data
