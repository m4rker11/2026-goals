# 2026 Goals

A personal goal tracking system built as a Jekyll static site with Claude Code integration.

## Quick Start

**View the site:** Deploy to GitHub Pages or run `jekyll serve` locally.

**Log daily progress:** Say "log today" to Claude Code, or manually edit `_data/daily.yml`.

## Goals Overview

| Goal | Difficulty | Timeline |
|------|------------|----------|
| Hindi to B2 | Hard | 25 chapters |
| Calendar Mastery | Hard | 6 weeks |
| 200 min Zone 2 Weekly | Hard | 8 weeks |
| Spend Less ($1000) | Medium | 11 weeks |
| Work Boundaries | Medium | 4 weeks |
| Options Trading | Easy | 4 periods (biweekly) |
| Sell Things | Easy | 6 items by Feb |
| Call Brother | Easy | Biweekly calls |

## Week Structure

All weeks run Monday-Sunday, starting **January 5, 2026**.

| Week | Dates |
|------|-------|
| 1 | Jan 5-11 |
| 2 | Jan 12-18 |
| 3 | Jan 19-25 |
| 4 | Jan 26 - Feb 1 |
| 5 | Feb 2-8 |
| 6 | Feb 9-15 |
| 7 | Feb 16-22 |
| 8 | Feb 23 - Mar 1 |

## Repository Structure

```
2026-goals/
├── _config.yml              # Jekyll configuration
├── _data/
│   ├── daily.yml            # Daily tracking entries
│   ├── goals.yml            # Goal configuration for MCP server
│   ├── logs/                # Per-goal progress logs
│   └── todos/               # Per-goal task tracking
├── index.md                 # Main dashboard
├── Goals.md                 # Detailed goal descriptions
├── agent-usage-guide.md     # Claude Code instructions
│
├── calendaring/
│   ├── overview.md          # 6-week program (4 tracks)
│   └── weeks/               # Weekly task files
│
├── fitness/
│   ├── overview.md          # 8-week progression plan
│   └── weeks/               # Week 1-8 detailed schedules
│
├── Hindi/
│   ├── overview.md          # Learning system + tutors
│   ├── chapters/            # 25 grammar chapter synopses
│   └── weeks/               # Weekly tutor tasks
│
├── spend-less/
│   ├── overview.md          # Save $1000 for Steam Frame
│   └── weeks/               # Phase 1-4 files
│
├── trading/
│   ├── overview.md          # Biweekly trading routine
│   └── periods/             # Period 1-4 trade logs
│
├── work-boundaries/
│   ├── overview.md          # 4-week program (4 tracks)
│   └── weeks/               # Weekly task files
│
├── sell/
│   ├── overview.md          # 6 items to sell
│   └── [item].md            # Per-item tracking
│
├── brother/
│   └── index.md             # Biweekly call schedule
│
└── updates/
    ├── index.md             # Coach view / latest status
    └── history.md           # Progress charts
```

## Daily Tracking

### With Claude Code

```
You: "log today"
Claude: I'll help you log today's progress...
        1. Did you check your calendar this morning?
        2. How many minutes of exercise?
        3. Any Hindi chapters studied?
        4. Mood/energy (1-5)?
        5. Any notes?
```

### Manual Entry

Add to `_data/daily.yml`:

```yaml
- date: 2026-01-06
  calendar: true
  fitness: 45
  hindi: 1
  mood: 4
  notes: "Good gym session"
```

## Goal Configuration

Goals are defined in `_data/goals.yml` with:

- **name** - Display name
- **aliases** - Alternative trigger words
- **content** - Path to detailed content
- **progression** - `sequential`, `time-weekly`, or `unordered`
- **cadence** - `daily`, `weekly`, or `every_2_weeks`
- **start** - When tracking begins

## Key Connections

```
Calendar Mastery (keystone habit)
       │
       ├──► Work Boundaries (know when to start/stop)
       ├──► Fitness (gym blocks scheduled)
       ├──► Trading (scheduled check-ins)
       └──► Anuska coordination (shared visibility)

Spend Less ◄── Sell Things (money IN vs OUT)
       │
       └──► Trading (financial discipline)
```

## Commit Convention

```bash
git commit -m "status-update:2026-01-06"
```

## Tech Stack

- **Jekyll** with Cayman theme (GitHub Pages)
- **YAML** data files for tracking
- **Claude Code** for AI-assisted logging
- **MCP server** integration (optional)

## License

Personal use.
