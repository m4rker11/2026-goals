# Goals MCP Tools - Design Document

**Status:** Proposed
**Date:** 2026-01-13
**Reviewed by:** Claude + Codex (critical design review)

## Executive Summary

The current MCP tools require 3+ tool calls for common actions like "mark my workout done." This design proposes a unified `done` tool that cascades updates automatically while keeping the existing storage structure unchanged.

---

## Problem Statement

### The Core Friction

When a user completes a workout, the current system requires:
1. `log_goal` to create a log entry in `logs/fitness.yml`
2. Manual edit to mark the todo done in `todos/fitness/week-2.yml`
3. Update to `daily.yml` to record fitness minutes

**Three writes for one action.** This is the root cause of friction.

### Specific Problems Identified

1. **log_goal doesn't mark todos done automatically**
   - User says "mark work announced on Tuesday"
   - Assistant must call log_goal AND manually edit todo files
   - Expected: single call should handle both

2. **No day-of-week intelligence**
   - Daily recurring tasks use day prefixes: `tue-morning`, `wed-announce`
   - System doesn't understand "today is Tuesday, so mark tue-morning done"
   - User/AI must manually map dates to task IDs

3. **Three disconnected data sources**
   - `daily.yml` - daily metrics (calendar, fitness minutes, hindi chapters)
   - `logs/*.yml` - detailed goal activity logs
   - `todos/*/*.yml` - task completion tracking
   - They don't sync automatically

4. **No simple mark_done operation**
   - `log_goal` has `todo_task` param but it's buried and requires explicit `todo_unit`
   - No straightforward: `mark_done(goal="calendar", task="morning")`

5. **read_todo requires exact unit**
   - Must specify `read_todo goal=calendar unit=week-2`
   - Should default to current week

---

## Current Architecture

### Data Sources

```
_data/
├── daily.yml           # Daily metrics snapshot
├── logs/
│   ├── fitness.yml     # Detailed fitness logs
│   ├── calendar.yml    # Calendar activity logs
│   └── ...
├── todos/
│   ├── calendar/
│   │   ├── week-1.yml
│   │   └── week-2.yml
│   ├── fitness/
│   │   ├── week-1.yml
│   │   └── week-2.yml
│   └── ...
├── memory.yml          # Patterns and insights
└── goals.yml           # Goal configuration
```

### Current Tool Count: 11+

| Tool | Purpose |
|------|---------|
| check_in | Show what needs attention |
| log_goal | Create log entry |
| log_daily | Update daily metrics |
| edit_goal_log | Modify existing log |
| get_goal_status | Goal progress summary |
| read_todo | Read todo file |
| write_todo | Create/overwrite todos |
| memory_save | Save insight |
| memory_read | Read insights |
| schedule_goal_task | Add calendar event for todo |
| add_calendar_event | Add calendar event |

**Problem:** Too many tools with overlapping concerns, no unified "I did X" action.

---

## Proposed Architecture

### Design Principle

> Keep storage structure unchanged. Change tool semantics to unify write paths.

### Tool Reduction: 11 → 6

| Before | After |
|--------|-------|
| log_goal, log_daily, edit_goal_log | **done** |
| check_in, get_goal_status, read_todo | **status** |
| memory_save, memory_read | **remember** |
| write_todo | **plan** |
| schedule_goal_task, add_calendar_event | **schedule** |
| (manual edits) | **edit** |

---

## Tool Specifications

### 1. `done` - Primary Action Tool

**Purpose:** Record completion of any goal-related activity with automatic cascading updates.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| goal | string | Yes | Goal ID: fitness, calendar, work-boundaries, hindi, etc. |
| what | string | No | Task hint and/or duration: "morning", "35 min run", "run-session" |
| date | string | No | ISO date, defaults to today |
| notes | string | No | Additional context |

#### Behavior Flow

```
done(goal, what, date, notes)
    │
    ├─► Parse 'what' for duration and task hint
    │
    ├─► Determine current week from date
    │
    ├─► Search todos/{goal}/week-{N}.yml for matching task
    │   │
    │   ├─► Day-prefix match: date=Tuesday → tue-*
    │   ├─► ID/name match: "run" → run-session
    │   └─► Substring match: "morning" → tue-morning
    │
    ├─► If match found:
    │   └─► Mark todo done, add notes
    │
    ├─► If duration present:
    │   └─► Create log entry in logs/{goal}.yml
    │
    ├─► Sync to daily.yml:
    │   ├─► calendar: set true
    │   ├─► fitness: add minutes
    │   └─► hindi: increment chapters
    │
    └─► Return detailed response
```

#### Parsing Spec

**Duration Extraction:**
```
Patterns (case-insensitive):
  - Integer: 35 → 35 minutes
  - With unit: 35m, 35 min, 35 mins, 35 minutes → 35 minutes
  - Hours: 0.5h, 0.5hr, 0.5 hour, 1h, 1.5 hours → convert to minutes
  - Standalone number at start: "35 min run" → duration=35, hint="run"
```

**Task Hint Extraction:**
```
After removing duration, remaining text becomes hint.
  - "35 min run" → hint="run"
  - "morning" → hint="morning"
  - "tue-morning" → hint="tue-morning", day_hint="tue"
```

**Day Hint Sources:**
```
1. Explicit in 'what': "tue-morning" → day_hint="tue"
2. Derived from date: 2026-01-14 → day_hint="tue"
```

#### Matching Priority

Given `what="morning"`, `date=2026-01-14` (Tuesday):

1. **Exact ID match:** task.id == "morning"
2. **Exact name match:** task.name == "morning"
3. **Day-prefix + hint:** task.id == "tue-morning" (date is Tuesday + hint contains "morning")
4. **Substring on ID:** "morning" in task.id
5. **Substring on name:** "morning" in task.name.lower()

#### Conflict Resolution

| Conflict | Resolution |
|----------|------------|
| what="tue-morning" but date=Wednesday | Prefer date, warn in response |
| Multiple matches | Return ambiguous with top 3 candidates |
| Task already done | Allow, append notes, warn in response |
| No match but has duration | Log ad-hoc entry, warn "No matching todo" |

#### Response Format

**Success:**
```yaml
status: ok
matched:
  goal: calendar
  unit: week-2
  task_id: tue-morning
  task_name: "Tue AM: Check calendar first thing"
daily_updated:
  calendar: true
message: "Marked tue-morning done. Daily updated."
```

**Partial (no todo match):**
```yaml
status: partial
logged:
  goal: fitness
  value: 20
  notes: "evening walk"
daily_updated:
  fitness: 55  # cumulative
message: "Logged 20 min. No matching todo found. Daily: 55 min total."
```

**Ambiguous:**
```yaml
status: ambiguous
candidates:
  - id: run-session
    name: "Run session (30 min)"
  - id: gym-session
    name: "Gym + PT session (60 min)"
message: "Multiple matches for 'session'. Specify: run-session or gym-session"
```

#### Examples

```python
# Morning calendar check on Tuesday
done(goal="calendar", what="morning")
# → Matches tue-morning, marks done, sets daily.calendar=true

# 35 minute run
done(goal="fitness", what="35 min run")
# → Matches run-session, marks done, logs 35 min, updates daily.fitness

# Ad-hoc walk (no todo)
done(goal="fitness", what="20 min walk")
# → No match, logs 20 min, updates daily.fitness, warns "No matching todo"

# Work boundaries announce
done(goal="work-boundaries", what="announce", date="2026-01-14")
# → Matches tue-announce, marks done

# Hindi session with notes
done(goal="hindi", what="anki", notes="Unit 3 vocab")
# → Matches anki-* task, marks done, increments daily.hindi
```

---

### 2. `status` - Read Current State

**Purpose:** Unified view of current state, replacing check_in + read_todo.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| goal | string | No | Filter to specific goal |
| date | string | No | Date to show, defaults to today |
| week | int | No | Specific week number |

#### Output Sections

```
Goals Status (2026-01-14, 9:32am)

**Week 2** (Jan 13-19)

**Today's Progress:**
  Calendar: ✓ (morning done)
  Fitness: 0 min (target: 90 min/week, 0/90)
  Hindi: 0 chapters
  Work: pending (announce, stop on time)

**Pending Today:**
  - calendar/wed-morning: Wed AM: Check calendar first thing
  - calendar/wed-immediate: Wed: Every event added immediately
  - work-boundaries/wed-announce: Wednesday - announce start/stop times

**Coming Up:**
  - 9:00am: [Goal] Run session (30 min)

**Overdue:**
  - hindi/anki-3: Anki review session 3 (week-1)

**Recent Memory:**
  - [2026-01-12] Environment matters: at brother's, less structure → dopamine spiral
```

---

### 3. `remember` - Save Insight

**Purpose:** Record patterns, observations, insights for future reference.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | The observation/insight |
| date | string | No | Date, defaults to today |

#### Examples

```python
remember(text="Screenless Sunday perfect for workouts - no phone distractions")
remember(text="Quote: 'I'll definitely do it tomorrow' - watch for this pattern")
```

---

### 4. `plan` - Create Todo Task

**Purpose:** Add a new task to a goal's todo list.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| goal | string | Yes | Goal ID |
| unit | string | No | Unit (week-2, chapter-3). Defaults to current week. |
| task_id | string | Yes | Task identifier |
| name | string | Yes | Human-readable name |
| description | string | No | Detailed instructions |

#### Example

```python
plan(
  goal="fitness",
  task_id="yoga-session",
  name="Yoga session (20 min)",
  description="Morning stretching routine"
)
# → Adds to fitness/week-2.yml (current week)
```

---

### 5. `schedule` - Add Calendar Event

**Purpose:** Create calendar event, optionally linked to a goal task.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| title | string | Yes | Event title |
| time | string | Yes | When: "today 4pm", "tomorrow 9am", ISO datetime |
| duration | int | No | Minutes, default 30 |
| goal | string | No | Link to goal (adds [Goal] prefix) |
| task | string | No | Task ID to link (updates todo with event_id) |
| notes | string | No | Event description |

---

### 6. `edit` - Modify Existing Task

**Purpose:** Update task properties (rare operation).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| goal | string | Yes | Goal ID |
| unit | string | No | Unit, defaults to current week |
| task_id | string | Yes | Task to edit |
| name | string | No | New name |
| notes | string | No | New notes |
| done | bool | No | Override done status |
| delete | bool | No | Remove task |

---

## Daily.yml Sync Rules

| Goal | Field | Sync Behavior |
|------|-------|---------------|
| calendar | calendar | Set `true` when any calendar task done |
| fitness | fitness | Add duration to daily total |
| hindi | hindi | Increment by 1 for each session |
| work-boundaries | (notes) | Add to daily notes |

---

## Migration Plan

### Phase 1: Add `done` Tool (Non-breaking)
- Implement `done` as new tool
- Keep all existing tools functional
- Test with real usage

### Phase 2: Add `status` Tool
- Implement unified status view
- Update check_in to suggest using status
- Keep check_in functional

### Phase 3: Deprecation Notices
- Add deprecation warnings to old tools
- Update documentation
- Monitor usage

### Phase 4: Remove Deprecated Tools
- Remove: log_goal, log_daily, edit_goal_log, read_todo
- Keep: schedule tools (still useful standalone)

---

## Appendix: Matching Algorithm Pseudocode

```python
def find_matching_task(goal_id: str, what: str, date: str) -> TaskMatch:
    """Find the best matching task for a done() call."""

    # Parse what
    duration, hint = parse_what(what)

    # Get day from date
    date_day = get_day_abbrev(date)  # "tue", "wed", etc.

    # Get current week
    week_num = get_week_for_date(date)
    unit = f"week-{week_num}"

    # Load tasks
    tasks = get_unit_todo(goal_id, unit).get("tasks", [])

    candidates = []

    for task in tasks:
        if task.get("done"):
            continue  # Skip already done (unless we want to re-done)

        task_id = task.get("id", "")
        task_name = task.get("name", "")

        score = 0
        match_reason = None

        # Priority 1: Exact ID match
        if hint and task_id == hint:
            score = 100
            match_reason = "exact_id"

        # Priority 2: Exact name match
        elif hint and task_name.lower() == hint.lower():
            score = 90
            match_reason = "exact_name"

        # Priority 3: Day-prefix + hint
        elif task_id.startswith(f"{date_day}-"):
            if not hint or hint.lower() in task_id or hint.lower() in task_name.lower():
                score = 80
                match_reason = "day_prefix"

        # Priority 4: Substring on ID
        elif hint and hint.lower() in task_id.lower():
            score = 60
            match_reason = "substring_id"

        # Priority 5: Substring on name
        elif hint and hint.lower() in task_name.lower():
            score = 50
            match_reason = "substring_name"

        if score > 0:
            candidates.append({
                "task": task,
                "score": score,
                "reason": match_reason
            })

    # Sort by score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)

    if not candidates:
        return TaskMatch(status="no_match", duration=duration)

    if len(candidates) == 1 or candidates[0]["score"] > candidates[1]["score"]:
        return TaskMatch(
            status="ok",
            task=candidates[0]["task"],
            unit=unit,
            duration=duration
        )

    # Multiple matches with same score
    return TaskMatch(
        status="ambiguous",
        candidates=[c["task"] for c in candidates[:3]],
        duration=duration
    )


def parse_what(what: str) -> tuple[int | None, str]:
    """Extract duration and hint from 'what' parameter."""
    if not what:
        return None, ""

    # Duration patterns
    import re

    # Match: 35, 35m, 35 min, 35 mins, 35 minutes
    min_match = re.match(r'^(\d+)\s*(?:m|min|mins|minutes?)?\s*(.*)$', what, re.I)
    if min_match:
        duration = int(min_match.group(1))
        hint = min_match.group(2).strip()
        return duration, hint

    # Match: 0.5h, 1.5hr, 2 hours
    hr_match = re.match(r'^(\d+\.?\d*)\s*(?:h|hr|hrs|hours?)?\s*(.*)$', what, re.I)
    if hr_match:
        hours = float(hr_match.group(1))
        duration = round(hours * 60)
        hint = hr_match.group(2).strip()
        return duration, hint

    # No duration found
    return None, what
```

---

## Open Questions

1. **Week boundary handling:** If user logs on Sunday night for Monday, which week?
   - Proposed: Use the date's week, not current calendar week

2. **Retroactive logging:** Can user do `done(goal="fitness", what="30 min", date="2026-01-10")`?
   - Proposed: Yes, finds week-1 for that date

3. **Multiple same-day completions:** Two workouts in one day?
   - Proposed: Allow multiple, daily.fitness accumulates, log has multiple entries

---

## Changelog

- 2026-01-13: Initial design after critical review with Codex
