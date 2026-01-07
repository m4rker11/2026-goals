"""MCP tool definitions and handlers."""

from datetime import datetime, timedelta

from mcp.types import TextContent, Tool

from .storage import (
    get_goals_config, get_goal_logs, save_goal_logs,
    get_unit_todo, save_unit_todo, update_todo_task, get_all_pending_tasks,
    get_all_scheduled_tasks, find_task_by_event_id,
    get_today, get_daily_entry, update_daily_entry, get_daily_entries, to_date_str,
    get_memory_entries, save_memory_entries, add_memory_entry, get_recent_memory
)
from .goals import get_current, compute_todos, resolve_goal_id
from . import calendar_service
from . import tasks_service


def get_tool_definitions(urgent_summary: str = "", goals_list: str = "") -> list[Tool]:
    """Generate tool definitions with dynamic descriptions."""

    # Dynamic check_in description with current urgent status
    if urgent_summary and urgent_summary != "All goals on track.":
        check_in_desc = f"""⚠️ STOP - READ THIS FIRST ⚠️
{urgent_summary}
You MUST say this to the user in your FIRST sentence, BEFORE invoking any skill (debugging, brainstorming, etc).
Also re-call when 30+ min elapsed: long-running scripts, logs with timestamps, user mentions time.
Example: "Quick note: [overdue items]. Now, about your request..."
This is non-negotiable accountability."""
    else:
        check_in_desc = """Check what goals need attention today.
Call at: (1) conversation start, (2) when 30+ min elapsed (scripts, logs, timestamps, user mentions)."""

    # Dynamic log description with available goals
    log_desc = f"""Log progress on a goal. Available goals: {goals_list or 'hindi, fitness, calendar, brother, trading, sell, spend-less, work-boundaries'}.
Use path for subgoals (e.g., 'chapter-3/vocab'). Optionally update a todo task when logging."""

    return [
        Tool(
            name="check_in",
            description=check_in_desc,
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="daily",
        description="""Update today's daily tracking entry. Use this for quick daily metrics.
Updates _data/daily.yml which feeds the Jekyll dashboard.""",
        inputSchema={
            "type": "object",
            "properties": {
                "calendar": {
                    "type": "boolean",
                    "description": "Did you check your calendar today?"
                },
                "fitness": {
                    "type": "number",
                    "description": "Minutes of exercise today"
                },
                "hindi": {
                    "type": "number",
                    "description": "Hindi chapters/lessons completed today"
                },
                "mood": {
                    "type": "number",
                    "description": "Energy/motivation level 1-5"
                },
                "notes": {
                    "type": "string",
                    "description": "Brief reflection on the day"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format (defaults to today)"
                }
            },
            "required": []
        }
    ),
        Tool(
            name="log",
            description=log_desc,
            inputSchema={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Goal ID or alias (e.g., 'fitness', 'hindi', 'gym')"
                },
                "value": {
                    "type": ["number", "boolean"],
                    "description": "Value to log (minutes for fitness, true/false for completion)"
                },
                "path": {
                    "type": "string",
                    "description": "Subgoal path (e.g., 'chapter-3', 'morning-check')"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes about completion (stored in log)"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format (defaults to today)"
                },
                "todo_unit": {
                    "type": "string",
                    "description": "Unit for todo update (e.g., 'week-1', '01-foundations-of-case')"
                },
                "todo_task": {
                    "type": "string",
                    "description": "Task ID to mark done in the unit's todo.yml"
                },
                "todo_notes": {
                    "type": "string",
                    "description": "Notes to add to the todo task (learnings, context about the task)"
                }
            },
            "required": ["goal"]
        }
    ),
    Tool(
        name="edit",
        description="Edit or delete an existing log entry.",
        inputSchema={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Goal ID or alias"
                },
                "date": {
                    "type": "string",
                    "description": "Date of entry to edit (YYYY-MM-DD)"
                },
                "path": {
                    "type": "string",
                    "description": "Path of entry to edit (if applicable)"
                },
                "value": {
                    "type": ["number", "boolean"],
                    "description": "New value"
                },
                "notes": {
                    "type": "string",
                    "description": "New notes"
                },
                "delete": {
                    "type": "boolean",
                    "description": "Set to true to delete the entry"
                }
            },
            "required": ["goal", "date"]
        }
    ),
    Tool(
        name="status",
        description="Get detailed status for a goal or all goals.",
        inputSchema={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Goal ID or alias (omit for all goals)"
                },
                "period": {
                    "type": "string",
                    "enum": ["today", "week", "month", "all"],
                    "description": "Time period to show (defaults to 'week')"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="read_todo",
        description="""Read todo tasks for a specific unit (week/chapter).
Returns the task list with completion status and notes.""",
        inputSchema={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Goal ID or alias"
                },
                "unit": {
                    "type": "string",
                    "description": "Unit identifier (e.g., 'week-1', '01-foundations-of-case')"
                }
            },
            "required": ["goal", "unit"]
        }
    ),
    Tool(
        name="write_todo",
        description="""Create or overwrite the todo list for a unit.
Use when setting up tasks for a new week/chapter or resetting the list.""",
        inputSchema={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Goal ID or alias"
                },
                "unit": {
                    "type": "string",
                    "description": "Unit identifier (e.g., 'week-1', '01-foundations-of-case')"
                },
                "tasks": {
                    "type": "array",
                    "description": "List of tasks",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Task identifier (e.g., 'vocab', 'synopsis')"},
                            "name": {"type": "string", "description": "Human-readable task name"},
                            "done": {"type": "boolean", "description": "Whether task is complete (default: false)"},
                            "notes": {"type": "string", "description": "Optional notes about the task"}
                        },
                        "required": ["id", "name"]
                    }
                }
            },
            "required": ["goal", "unit", "tasks"]
        }
        ),
        Tool(
            name="schedule",
            description="""Schedule a todo task for a specific time on Google Calendar.
Creates a calendar event with [Goal] prefix. Syncs to todo.yml for visibility.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Goal ID or alias"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit identifier (e.g., 'week-1', '01-foundations-of-case')"
                    },
                    "task": {
                        "type": "string",
                        "description": "Task ID to schedule"
                    },
                    "time": {
                        "type": "string",
                        "description": "When to schedule: 'today 4pm', 'tomorrow 9am', or ISO datetime"
                    },
                    "duration": {
                        "type": "number",
                        "description": "Duration in minutes (default: 30)"
                    },
                    "calendar": {
                        "type": "string",
                        "description": "Calendar name (e.g., 'Personal', 'Work'). Defaults to primary calendar."
                    },
                    "invite": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Email addresses to invite"
                    }
                },
                "required": ["goal", "unit", "task", "time"]
            }
        ),
        Tool(
            name="reschedule",
            description="Move a scheduled goal to a new time.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "Calendar event ID (from list_scheduled)"
                    },
                    "new_time": {
                        "type": "string",
                        "description": "New time: 'today 5pm', 'tomorrow 2pm', or ISO datetime"
                    }
                },
                "required": ["event_id", "new_time"]
            }
        ),
        Tool(
            name="unschedule",
            description="Remove a scheduled goal event from calendar.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "Calendar event ID to remove"
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="list_scheduled",
            description="Show scheduled events from Google Calendar. Shows both goal events and regular events.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "number",
                        "description": "Hours ahead to look (default: 24)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memory_save",
            description="""Save an observation to memory. Call this when you notice:
- Behavioral patterns (e.g., "Skipped fitness 3rd day - said 'too tired' but watched TV")
- User quotes/commitments (e.g., "Quote: 'I'll definitely finish chapter 5 tomorrow'")
- Insights about what works/doesn't (e.g., "Completed fitness despite resistance - felt great after")
- Energy/context notes (e.g., "Very tired today, might need rest day")
Memory is reviewed during check_in to surface patterns over time.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The observation, quote, or insight to remember"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (defaults to today)"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="memory_read",
            description="Read memory entries. Returns recent observations, quotes, and insights.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Number of entries to return (default: 10)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memory_condense",
            description="""Condense memory by summarizing old entries. Use when memory gets long.
Reads all entries, you provide a condensed summary, and it replaces the old entries.
Keep: key patterns, significant quotes, important insights. Remove: redundant entries, noise.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "condensed_entries": {
                        "type": "array",
                        "description": "The condensed list of memory entries to save",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string", "description": "Date range covered (e.g., '2026-01-01 to 2026-01-15')"},
                                "text": {"type": "string", "description": "The condensed observation"}
                            },
                            "required": ["date", "text"]
                        }
                    }
                },
                "required": ["condensed_entries"]
            }
        ),
        Tool(
            name="add",
            description="""Add an event or task to Google Calendar.
- type="event": Calendar event only (meetings, appointments)
- type="task": Calendar event + Google Task (action items to complete)
Tasks appear both on calendar (time block) and in Google Tasks (checklist).""",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Event/task title"
                    },
                    "time": {
                        "type": "string",
                        "description": "When to schedule: 'today 4pm', 'tomorrow 9am', or ISO datetime"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["event", "task"],
                        "description": "event = calendar only, task = calendar + Google Tasks"
                    },
                    "duration": {
                        "type": "number",
                        "description": "Duration in minutes (default: 30)"
                    },
                    "calendar": {
                        "type": "string",
                        "description": "Calendar name (e.g., 'Personal', 'Work'). Defaults to primary."
                    },
                    "color": {
                        "type": "number",
                        "description": "Color ID: 9=blue(Work), 2=green(Personal), 3=purple(Social), 11=red(Health), 6=orange(Anuska)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional description/notes"
                    }
                },
                "required": ["title", "time", "type"]
            }
        )
    ]


def handle_check_in() -> list[TextContent]:
    """Handle check_in tool."""
    config = get_goals_config()
    goal_todos = compute_todos(config)
    pending_tasks = get_all_pending_tasks()

    # Get today's daily entry
    today_entry = get_daily_entry()

    # Get recent memory entries
    recent_memory = get_recent_memory(limit=5)

    # Get current time for display
    now = datetime.now()
    time_str = now.strftime("%I:%M%p").lower().lstrip("0")

    lines = [f"Goals Check-in ({get_today()}, {time_str})", ""]

    # Show recent memory first (for context)
    if recent_memory:
        lines.append("**Recent memory:**")
        for entry in recent_memory:
            lines.append(f"- [{entry.get('date', '?')}] {entry.get('text', '')}")
        lines.append("")

    # Show upcoming calendar events (next 4 hours)
    upcoming_events = calendar_service.get_upcoming_events(hours_ahead=4)
    if upcoming_events:
        lines.append("**Coming up:**")
        for e in upcoming_events:
            prefix = "[Goal] " if e["is_goal"] else ""
            duration = f" ({e['duration_min']} min)" if e["duration_min"] != 30 else ""
            lines.append(f"  • {e['time']} - {prefix}{e['title']}{duration}")
        lines.append("")

    # Show today's daily status first
    if today_entry:
        lines.append("**Today's tracking:**")
        lines.append(f"  Calendar: {'yes' if today_entry.get('calendar') else 'no'}")
        lines.append(f"  Fitness: {today_entry.get('fitness', 0)} min")
        lines.append(f"  Hindi: {today_entry.get('hindi', 0)} chapters")
        if today_entry.get('mood'):
            lines.append(f"  Mood: {today_entry['mood']}/5")
        lines.append("")
    else:
        lines.append("**Today's tracking:** No entry yet. Use `daily` tool to log.")
        lines.append("")

    # New priority categories: overdue, due, info
    overdue = [t for t in goal_todos if t.get("priority") == "overdue"]
    due = [t for t in goal_todos if t.get("priority") == "due"]
    info = [t for t in goal_todos if t.get("priority") == "info"]

    if overdue:
        lines.append("**Overdue:**")
        for t in overdue:
            lines.append(f"- {t['message']}")
        lines.append("")

    if due:
        lines.append("**Due:**")
        for t in due:
            lines.append(f"- {t['message']}")
        lines.append("")

    if info:
        lines.append("**Progress:**")
        for t in info:
            lines.append(f"- {t['message']}")
        lines.append("")

    # Show missed scheduled events (past 24 hours)
    missed = calendar_service.get_missed_scheduled(hours_back=24)
    if missed:
        lines.append("**Missed scheduled:**")
        for m in missed:
            lines.append(f"- {m['title']} was scheduled for {m['date']} {m['time']} - not logged")
        lines.append("")

    # Detect drift between todo.yml scheduled tasks and calendar
    scheduled_tasks = get_all_scheduled_tasks()
    drift_items = []
    for st in scheduled_tasks:
        task = st["task"]
        event_id = task.get("event_id")
        scheduled_for = task.get("scheduled_for")

        if not event_id or not scheduled_for:
            continue

        event_info = calendar_service.get_event_info(event_id)
        if event_info is None:
            continue  # Not authenticated

        task_name = task.get("name", task.get("id"))

        if not event_info.get("exists"):
            drift_items.append(f"- {task_name}: calendar event deleted (was {scheduled_for[:16]})")
        elif event_info.get("start"):
            cal_start = event_info["start"]
            todo_time = datetime.fromisoformat(scheduled_for)
            # Check if times differ by more than 1 minute
            if abs((cal_start - todo_time).total_seconds()) > 60:
                cal_time_str = cal_start.strftime("%I:%M%p").lower().lstrip("0")
                drift_items.append(f"- {task_name}: moved to {cal_time_str} in calendar (todo says {scheduled_for[:16]})")

    if drift_items:
        lines.append("**Calendar drift detected:**")
        lines.extend(drift_items)
        lines.append("(Use reschedule/unschedule to sync)")
        lines.append("")

    # Add pending tasks from todos
    if pending_tasks:
        lines.append("**Pending tasks:**")
        # Group by goal
        by_goal = {}
        for pt in pending_tasks:
            gid = pt["goal_id"]
            if gid not in by_goal:
                by_goal[gid] = []
            by_goal[gid].append(pt)

        for gid, tasks in by_goal.items():
            # Show up to 3 tasks per goal
            for pt in tasks[:3]:
                task = pt["task"]
                lines.append(f"- {gid}/{pt['unit']}: {task.get('name', task.get('id'))}")
            if len(tasks) > 3:
                lines.append(f"  (+{len(tasks) - 3} more)")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_daily(arguments: dict) -> list[TextContent]:
    """Handle daily tool - update today's daily tracking."""
    date = arguments.get("date")

    # Build fields to update (only include provided values)
    fields = {}
    if "calendar" in arguments:
        fields["calendar"] = arguments["calendar"]
    if "fitness" in arguments:
        fields["fitness"] = arguments["fitness"]
    if "hindi" in arguments:
        fields["hindi"] = arguments["hindi"]
    if "mood" in arguments:
        fields["mood"] = arguments["mood"]
    if "notes" in arguments:
        fields["notes"] = arguments["notes"]

    if not fields:
        # No fields provided, just show current status
        entry = get_daily_entry(date)
        if entry:
            lines = [f"📅 **Daily Entry** ({entry['date']})", ""]
            lines.append(f"  Calendar: {'✓' if entry.get('calendar') else '✗'}")
            lines.append(f"  Fitness: {entry.get('fitness', 0)} min")
            lines.append(f"  Hindi: {entry.get('hindi', 0)} chapters")
            if entry.get('mood'):
                lines.append(f"  Mood: {entry['mood']}/5")
            if entry.get('notes'):
                lines.append(f"  Notes: {entry['notes']}")
            return [TextContent(type="text", text="\n".join(lines))]
        else:
            return [TextContent(type="text", text=f"No entry for {date or get_today()}. Provide fields to create one.")]

    # Update the entry
    entry = update_daily_entry(date, **fields)

    lines = [f"✅ **Daily Updated** ({entry['date']})", ""]
    lines.append(f"  Calendar: {'✓' if entry.get('calendar') else '✗'}")
    lines.append(f"  Fitness: {entry.get('fitness', 0)} min")
    lines.append(f"  Hindi: {entry.get('hindi', 0)} chapters")
    if entry.get('mood'):
        lines.append(f"  Mood: {entry['mood']}/5")
    if entry.get('notes'):
        lines.append(f"  Notes: {entry['notes']}")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_log(arguments: dict) -> list[TextContent]:
    """Handle log tool."""
    config = get_goals_config()
    goals = config.get("goals", {})

    goal_input = arguments.get("goal", "")
    goal_id = resolve_goal_id(goals, goal_input)

    if not goal_id:
        available = ", ".join(goals.keys())
        return [TextContent(type="text", text=f"Unknown goal: '{goal_input}'. Available: {available}")]

    # Check if we have meaningful log data (not just marking a todo done)
    has_log_data = any(k in arguments for k in ("value", "path", "notes"))

    # Only create log entry if we have actual progress to log
    entry = None
    if has_log_data or not (arguments.get("todo_unit") and arguments.get("todo_task")):
        logs = get_goal_logs(goal_id)
        entry = {"date": arguments.get("date", get_today())}

        if "path" in arguments:
            entry["path"] = arguments["path"]

        if "value" in arguments:
            if isinstance(arguments["value"], bool):
                entry["done"] = arguments["value"]
            else:
                entry["value"] = arguments["value"]
        else:
            entry["done"] = True

        if "notes" in arguments:
            entry["notes"] = arguments["notes"]

        logs.append(entry)
        save_goal_logs(goal_id, logs)

    goal_name = goals[goal_id].get("name", goal_id)
    result_lines = []
    if entry:
        result_lines.append(f"Logged to {goal_name}: {entry}")

    # Handle todo update if specified
    todo_unit = arguments.get("todo_unit")
    todo_task = arguments.get("todo_task")

    if todo_unit and todo_task:
        todo_notes = arguments.get("todo_notes")
        # Mark done AND clear any scheduling fields
        updated = update_todo_task(
            goal_id, todo_unit, todo_task,
            done=True, notes=todo_notes, clear_schedule=True
        )
        if updated:
            result_lines.append(f"Todo updated: {todo_task} marked done")
            if todo_notes:
                result_lines.append(f"Task notes: {todo_notes}")
            # If task had a calendar event, mark it complete
            cleared_event_id = updated.get("_cleared_event_id")
            if cleared_event_id:
                cal_result = calendar_service.mark_goal_complete(cleared_event_id)
                if cal_result.get("success"):
                    result_lines.append("Calendar event marked complete ✓")
        else:
            result_lines.append(f"Warning: Task '{todo_task}' not found in {todo_unit}")
    else:
        # No specific task - try to find any goal event today
        event_id = calendar_service.find_goal_event_today(goal_id)
        if event_id:
            cal_result = calendar_service.mark_goal_complete(event_id)
            if cal_result.get("success"):
                result_lines.append("Calendar event marked complete ✓")

    return [TextContent(type="text", text="\n".join(result_lines))]


def handle_edit(arguments: dict) -> list[TextContent]:
    """Handle edit tool."""
    config = get_goals_config()
    goals = config.get("goals", {})

    goal_input = arguments.get("goal", "")
    goal_id = resolve_goal_id(goals, goal_input)

    if not goal_id:
        return [TextContent(type="text", text=f"Unknown goal: '{goal_input}'")]

    logs = get_goal_logs(goal_id)
    target_date = arguments.get("date")
    target_path = arguments.get("path")

    found_idx = None
    for i, log in enumerate(logs):
        if to_date_str(log.get("date")) == target_date:
            if target_path:
                if log.get("path") == target_path:
                    found_idx = i
                    break
            else:
                found_idx = i
                break

    if found_idx is None:
        return [TextContent(type="text", text=f"No entry found for {target_date}" + (f" path={target_path}" if target_path else ""))]

    if arguments.get("delete"):
        deleted = logs.pop(found_idx)
        save_goal_logs(goal_id, logs)
        return [TextContent(type="text", text=f"Deleted: {deleted}")]

    if "value" in arguments:
        if isinstance(arguments["value"], bool):
            logs[found_idx]["done"] = arguments["value"]
        else:
            logs[found_idx]["value"] = arguments["value"]

    if "notes" in arguments:
        logs[found_idx]["notes"] = arguments["notes"]

    save_goal_logs(goal_id, logs)
    return [TextContent(type="text", text=f"Updated: {logs[found_idx]}")]


def handle_status(arguments: dict) -> list[TextContent]:
    """Handle status tool."""
    config = get_goals_config()
    goals = config.get("goals", {})

    goal_input = arguments.get("goal")
    period = arguments.get("period", "week")

    now = datetime.now()
    if period == "today":
        start_date = get_today()
    elif period == "week":
        start_date = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    elif period == "month":
        start_date = now.replace(day=1).strftime("%Y-%m-%d")
    else:
        start_date = "2000-01-01"

    target_goals = {}
    if goal_input:
        goal_id = resolve_goal_id(goals, goal_input)
        if goal_id:
            target_goals[goal_id] = goals[goal_id]
        else:
            return [TextContent(type="text", text=f"Unknown goal: '{goal_input}'")]
    else:
        target_goals = goals

    lines = [f"📊 **Status** ({period})", ""]

    # Include daily summary for this period
    daily_entries = get_daily_entries()
    period_daily = [d for d in daily_entries if to_date_str(d.get("date")) >= start_date]
    if period_daily:
        total_fitness = sum(d.get("fitness", 0) for d in period_daily)
        total_hindi = sum(d.get("hindi", 0) for d in period_daily)
        calendar_days = sum(1 for d in period_daily if d.get("calendar"))
        lines.append(f"**Daily totals ({len(period_daily)} days):**")
        lines.append(f"  Fitness: {total_fitness} min")
        lines.append(f"  Hindi: {total_hindi} chapters")
        lines.append(f"  Calendar: {calendar_days}/{len(period_daily)} days")
        lines.append("")

    for goal_id, goal_config in target_goals.items():
        logs = get_goal_logs(goal_id)
        period_logs = [l for l in logs if to_date_str(l.get("date")) >= start_date]
        progression = goal_config.get("progression")

        lines.append(f"**{goal_config.get('name', goal_id)}**")

        if progression:
            current_info = get_current(goal_config, logs)
            current = current_info.get("current")
            done = current_info.get("done", 0)
            total = current_info.get("total", 0)

            if progression == "sequential":
                if current:
                    lines.append(f"  Current: {current} ({done}/{total} complete)")
                elif total > 0:
                    lines.append(f"  All complete! ({done}/{total})")
            elif progression == "time-weekly":
                week = current_info.get("week", 1)
                if current:
                    lines.append(f"  Week {week}: {current}")
                else:
                    lines.append(f"  Week {week}")
            elif progression == "unordered":
                lines.append(f"  Progress: {done}/{total} done")

        if goal_config.get("unit"):
            total = sum(l.get("value", 0) for l in period_logs)
            lines.append(f"  This {period}: {total} {goal_config.get('unit')}")
        else:
            done_count = len([l for l in period_logs if l.get("done")])
            if done_count > 0:
                lines.append(f"  This {period}: {done_count} entries")

        if period_logs:
            lines.append("  Recent:")
            for log in period_logs[-3:]:
                entry_str = f"    - {log.get('date')}"
                if log.get("path"):
                    entry_str += f" [{log['path']}]"
                if log.get("value"):
                    entry_str += f": {log['value']}"
                if log.get("notes"):
                    entry_str += f" ({log['notes']})"
                lines.append(entry_str)

        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_read_todo(arguments: dict) -> list[TextContent]:
    """Handle read_todo tool."""
    config = get_goals_config()
    goals = config.get("goals", {})

    goal_input = arguments.get("goal", "")
    goal_id = resolve_goal_id(goals, goal_input)

    if not goal_id:
        return [TextContent(type="text", text=f"Unknown goal: '{goal_input}'")]

    unit = arguments.get("unit", "")
    if not unit:
        return [TextContent(type="text", text="Unit is required")]

    todo = get_unit_todo(goal_id, unit)
    tasks = todo.get("tasks", [])

    if not tasks:
        return [TextContent(type="text", text=f"No tasks found for {goal_id}/{unit}")]

    goal_name = goals[goal_id].get("name", goal_id)
    lines = [f"📝 **{goal_name}** - {unit}", ""]

    pending = [t for t in tasks if not t.get("done", False)]
    done = [t for t in tasks if t.get("done", False)]

    if pending:
        lines.append("**Pending:**")
        for t in pending:
            line = f"- [ ] {t.get('name', t.get('id'))}"
            if t.get("notes"):
                line += f" ({t['notes']})"
            lines.append(line)
        lines.append("")

    if done:
        lines.append("**Completed:**")
        for t in done:
            line = f"- [x] {t.get('name', t.get('id'))}"
            if t.get("notes"):
                line += f" ({t['notes']})"
            lines.append(line)

    return [TextContent(type="text", text="\n".join(lines))]


def handle_write_todo(arguments: dict) -> list[TextContent]:
    """Handle write_todo tool."""
    config = get_goals_config()
    goals = config.get("goals", {})

    goal_input = arguments.get("goal", "")
    goal_id = resolve_goal_id(goals, goal_input)

    if not goal_id:
        return [TextContent(type="text", text=f"Unknown goal: '{goal_input}'")]

    unit = arguments.get("unit", "")
    if not unit:
        return [TextContent(type="text", text="Unit is required")]

    tasks_input = arguments.get("tasks", [])
    if not tasks_input:
        return [TextContent(type="text", text="Tasks list is required")]

    # Normalize tasks
    tasks = []
    for t in tasks_input:
        task = {
            "id": t.get("id"),
            "name": t.get("name", t.get("id")),
            "done": t.get("done", False),
        }
        if t.get("notes"):
            task["notes"] = t["notes"]
        tasks.append(task)

    todo_data = {"unit": unit, "tasks": tasks}
    save_unit_todo(goal_id, unit, todo_data)

    goal_name = goals[goal_id].get("name", goal_id)
    return [TextContent(type="text", text=f"Created todo for {goal_name}/{unit} with {len(tasks)} tasks")]


def handle_schedule(arguments: dict) -> list[TextContent]:
    """Handle schedule tool - schedules a todo task."""
    config = get_goals_config()
    goals = config.get("goals", {})

    goal_input = arguments.get("goal", "")
    goal_id = resolve_goal_id(goals, goal_input)

    if not goal_id:
        available = ", ".join(goals.keys())
        return [TextContent(type="text", text=f"Unknown goal: '{goal_input}'. Available: {available}")]

    unit = arguments.get("unit", "")
    task_id = arguments.get("task", "")

    if not unit or not task_id:
        return [TextContent(type="text", text="Both 'unit' and 'task' are required to schedule a task")]

    # Verify task exists
    todo = get_unit_todo(goal_id, unit)
    task_info = None
    for t in todo.get("tasks", []):
        if t.get("id") == task_id:
            task_info = t
            break

    if not task_info:
        return [TextContent(type="text", text=f"Task '{task_id}' not found in {goal_id}/{unit}")]

    if task_info.get("done"):
        return [TextContent(type="text", text=f"Task '{task_id}' is already completed")]

    time_str = arguments.get("time", "")
    time = calendar_service.parse_time(time_str)
    if not time:
        return [TextContent(type="text", text=f"Could not parse time: '{time_str}'. Try 'today 4pm' or 'tomorrow 9am'")]

    # Check for conflicts
    duration = arguments.get("duration", 30)
    conflicts = calendar_service.check_conflicts(time, duration)
    conflict_warning = ""
    if conflicts:
        conflict_warning = f"\n⚠️ Conflicts with: {', '.join(c['title'] + ' at ' + c['time'] for c in conflicts)}"

    goal_config = goals[goal_id]
    goal_name = goal_config.get("name", goal_id)
    task_name = task_info.get("name", task_id)
    color_id = goal_config.get("color")

    # Resolve calendar name to ID
    calendar_name = arguments.get("calendar")
    calendar_id = calendar_service.resolve_calendar(calendar_name) if calendar_name else None

    result = calendar_service.schedule_goal(
        goal_id=goal_id,
        goal_name=goal_name,
        time=time,
        duration_min=duration,
        notes=task_name,
        invite_emails=arguments.get("invite", []),
        color_id=color_id,
        calendar_id=calendar_id,
    )

    if not result.get("success"):
        return [TextContent(type="text", text=result["message"] + conflict_warning)]

    # Sync to todo.yml
    event_id = result.get("event_id")
    scheduled_for = time.isoformat()

    updated = update_todo_task(
        goal_id, unit, task_id,
        scheduled_for=scheduled_for,
        event_id=event_id
    )

    message = result["message"] + conflict_warning
    if updated:
        message += f"\nSynced to todo: {goal_id}/{unit}/{task_id}"
    if event_id:
        message += f"\nEvent ID: {event_id}"

    return [TextContent(type="text", text=message)]


def handle_reschedule(arguments: dict) -> list[TextContent]:
    """Handle reschedule tool - syncs to todo.yml."""
    event_id = arguments.get("event_id", "")
    if not event_id:
        return [TextContent(type="text", text="event_id is required")]

    time_str = arguments.get("new_time", "")
    time = calendar_service.parse_time(time_str)
    if not time:
        return [TextContent(type="text", text=f"Could not parse time: '{time_str}'")]

    result = calendar_service.reschedule_goal(event_id, time)

    if not result.get("success"):
        return [TextContent(type="text", text=result["message"])]

    # Sync to todo.yml - find task by event_id and update scheduled_for
    task_info = find_task_by_event_id(event_id)
    message = result["message"]

    if task_info:
        updated = update_todo_task(
            task_info["goal_id"],
            task_info["unit"],
            task_info["task"]["id"],
            scheduled_for=time.isoformat()
        )
        if updated:
            message += f"\nSynced to todo: {task_info['goal_id']}/{task_info['unit']}/{task_info['task']['id']}"

    return [TextContent(type="text", text=message)]


def handle_unschedule(arguments: dict) -> list[TextContent]:
    """Handle unschedule tool - clears scheduling from todo.yml."""
    event_id = arguments.get("event_id", "")
    if not event_id:
        return [TextContent(type="text", text="event_id is required")]

    # Find task before deleting event (need event_id to look up)
    task_info = find_task_by_event_id(event_id)

    result = calendar_service.unschedule_goal(event_id)

    if not result.get("success"):
        return [TextContent(type="text", text=result["message"])]

    message = result["message"]

    # Clear scheduling fields from todo.yml
    if task_info:
        updated = update_todo_task(
            task_info["goal_id"],
            task_info["unit"],
            task_info["task"]["id"],
            clear_schedule=True
        )
        if updated:
            message += f"\nCleared from todo: {task_info['goal_id']}/{task_info['unit']}/{task_info['task']['id']}"

    return [TextContent(type="text", text=message)]


def handle_list_scheduled(arguments: dict) -> list[TextContent]:
    """Handle list_scheduled tool."""
    hours = arguments.get("hours", 24)
    events = calendar_service.get_upcoming_events(hours_ahead=hours)

    if not events:
        if not calendar_service.is_authenticated():
            return [TextContent(type="text", text="Not authenticated. Run: goals-mcp auth")]
        return [TextContent(type="text", text=f"No events in the next {hours} hours.")]

    lines = [f"📅 Upcoming ({hours}h):", ""]
    for e in events:
        prefix = "[Goal] " if e["is_goal"] else ""
        duration = f" ({e['duration_min']} min)" if e["duration_min"] != 30 else ""
        lines.append(f"  • {e['time']} - {prefix}{e['title']}{duration}")
        if e.get("event_id"):
            lines.append(f"    ID: {e['event_id']}")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_memory_save(arguments: dict) -> list[TextContent]:
    """Handle memory_save tool."""
    text = arguments.get("text", "")
    if not text:
        return [TextContent(type="text", text="text is required")]

    date = arguments.get("date")
    entry = add_memory_entry(text, date)

    return [TextContent(type="text", text=f"Saved to memory: [{entry['date']}] {entry['text']}")]


def handle_memory_read(arguments: dict) -> list[TextContent]:
    """Handle memory_read tool."""
    limit = arguments.get("limit", 10)
    entries = get_recent_memory(limit)

    if not entries:
        return [TextContent(type="text", text="No memory entries yet.")]

    lines = ["**Memory:**", ""]
    for entry in entries:
        lines.append(f"- [{entry.get('date', '?')}] {entry.get('text', '')}")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_memory_condense(arguments: dict) -> list[TextContent]:
    """Handle memory_condense tool."""
    condensed = arguments.get("condensed_entries", [])

    if not condensed:
        # Return current memory for review
        entries = get_memory_entries()
        if not entries:
            return [TextContent(type="text", text="No memory entries to condense.")]

        lines = ["**Current memory (provide condensed_entries to replace):**", ""]
        for entry in entries:
            lines.append(f"- [{entry.get('date', '?')}] {entry.get('text', '')}")
        lines.append("")
        lines.append(f"Total: {len(entries)} entries")
        return [TextContent(type="text", text="\n".join(lines))]

    # Save condensed entries
    old_count = len(get_memory_entries())
    save_memory_entries(condensed)

    return [TextContent(
        type="text",
        text=f"Memory condensed: {old_count} entries → {len(condensed)} entries"
    )]


def handle_add(arguments: dict) -> list[TextContent]:
    """Handle add tool - creates calendar event and optionally Google Task."""
    title = arguments.get("title", "")
    if not title:
        return [TextContent(type="text", text="title is required")]

    time_str = arguments.get("time", "")
    time = calendar_service.parse_time(time_str)
    if not time:
        return [TextContent(type="text", text=f"Could not parse time: '{time_str}'. Try 'today 4pm' or 'tomorrow 9am'")]

    item_type = arguments.get("type", "event")
    if item_type not in ("event", "task"):
        return [TextContent(type="text", text="type must be 'event' or 'task'")]

    duration = arguments.get("duration", 30)
    calendar_name = arguments.get("calendar")
    calendar_id = calendar_service.resolve_calendar(calendar_name) if calendar_name else None
    color_id = arguments.get("color")
    notes = arguments.get("notes", "")

    # Check for conflicts
    conflicts = calendar_service.check_conflicts(time, duration)
    conflict_warning = ""
    if conflicts:
        conflict_warning = f"\n⚠️ Conflicts with: {', '.join(c['title'] + ' at ' + c['time'] for c in conflicts)}"

    # Build description
    description = notes or ""

    # If task type, create Google Task first to get task_id
    task_id = None
    if item_type == "task":
        task_result = tasks_service.create_task(
            title=title,
            due_date=time.date(),
            notes=notes,
        )
        if task_result.get("success"):
            task_id = task_result.get("task_id")
            # Store task_id in calendar event description for sync
            description = f"TaskID: {task_id}\n{notes}" if notes else f"TaskID: {task_id}"
        else:
            # Task creation failed but continue with calendar
            conflict_warning += f"\n⚠️ Google Task creation failed: {task_result.get('message')}"

    # Create calendar event
    from gcsa.google_calendar import GoogleCalendar
    from gcsa.event import Event

    if calendar_id:
        try:
            gc = GoogleCalendar(
                default_calendar=calendar_id,
                credentials_path=str(calendar_service.CREDENTIALS_PATH),
                token_path=str(calendar_service.TOKEN_PATH),
            )
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to access calendar: {e}")]
    else:
        gc = calendar_service.get_calendar()

    if not gc:
        return [TextContent(type="text", text="Not authenticated. Run: goals-mcp auth")]

    end_time = time + timedelta(minutes=duration)

    try:
        event = Event(
            summary=title,
            start=time,
            end=end_time,
            description=description if description else None,
            color_id=str(color_id) if color_id else None,
        )

        created = gc.add_event(event)

        result_lines = [f"Created {item_type}: {title} at {time.strftime('%I:%M%p').lower().lstrip('0')}"]
        if item_type == "task" and task_id:
            result_lines.append(f"Google Task created (ID: {task_id})")
        if created.event_id:
            result_lines.append(f"Calendar event ID: {created.event_id}")
        if conflict_warning:
            result_lines.append(conflict_warning)

        return [TextContent(type="text", text="\n".join(result_lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Failed to create calendar event: {e}{conflict_warning}")]


async def handle_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls to handlers."""
    if name == "check_in":
        return handle_check_in()
    elif name == "daily":
        return handle_daily(arguments)
    elif name == "log":
        return handle_log(arguments)
    elif name == "edit":
        return handle_edit(arguments)
    elif name == "status":
        return handle_status(arguments)
    elif name == "read_todo":
        return handle_read_todo(arguments)
    elif name == "write_todo":
        return handle_write_todo(arguments)
    elif name == "schedule":
        return handle_schedule(arguments)
    elif name == "reschedule":
        return handle_reschedule(arguments)
    elif name == "unschedule":
        return handle_unschedule(arguments)
    elif name == "list_scheduled":
        return handle_list_scheduled(arguments)
    elif name == "memory_save":
        return handle_memory_save(arguments)
    elif name == "memory_read":
        return handle_memory_read(arguments)
    elif name == "memory_condense":
        return handle_memory_condense(arguments)
    elif name == "add":
        return handle_add(arguments)

    return [TextContent(type="text", text=f"Unknown tool: {name}")]
