"""MCP tool definitions and handlers."""

from datetime import datetime, timedelta

from mcp.types import TextContent, Tool

from .storage import (
    get_goals_config, get_goal_logs, save_goal_logs,
    get_unit_todo, save_unit_todo, update_todo_task, get_all_pending_tasks,
    get_all_scheduled_tasks, find_task_by_event_id,
    get_today, get_daily_entry, update_daily_entry,
    get_memory_entries, save_memory_entries, add_memory_entry, get_recent_memory,
    get_schedule, get_current_progress, update_current_goal, get_current_week, get_effective_week
)
from .goals import compute_todos, resolve_goal_id
from . import calendar_service
from . import wger_service


def get_tool_definitions(urgent_summary: str = "") -> list[Tool]:
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

    return [
        # ==================== CHECK-IN ====================
        Tool(
            name="check_in",
            description=check_in_desc,
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),

        # ==================== DONE ====================
        Tool(
            name="done",
            description="""Mark a goal task as done with automatic cascading updates.

Automatically:
- Marks the todo task done in current week
- Logs duration (if provided) to goal logs
- Updates daily.yml (calendar=true, fitness+=minutes, hindi+=1)
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Goal ID: fitness, calendar, work-boundaries, hindi, etc."
                    },
                    "task": {
                        "type": "string",
                        "description": "Exact task ID from todo list (e.g., 'tue-morning', 'run-session')"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Duration in minutes - logs to goal and syncs to daily.yml for fitness"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "ISO date, defaults to today"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional context"
                    }
                },
                "required": ["goal"]
            }
        ),

        # ==================== STATUS ====================
        Tool(
            name="status",
            description="""Get current status for goals - unified view of progress and pending tasks.

Shows:
- Today's progress (calendar, fitness, hindi)
- Pending tasks for today (with exact task IDs for use with done tool)
- Upcoming calendar events
- Overdue tasks
- Recent memory entries
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Filter to specific goal (optional, shows all if omitted)"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Date to show status for (defaults to today)"
                    }
                },
                "required": []
            }
        ),

        # ==================== REMEMBER ====================
        Tool(
            name="remember",
            description="""Save an observation or insight to memory for future reference.

Use for:
- Behavioral patterns ("Skipped fitness 3rd day - said 'too tired' but watched TV")
- User quotes/commitments ("Quote: 'I'll definitely finish tomorrow'")
- What works/doesn't ("Completed fitness despite resistance - felt great after")
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The observation, quote, or insight to remember"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Date (defaults to today)"
                    }
                },
                "required": ["text"]
            }
        ),

        # ==================== PLAN ====================
        Tool(
            name="plan",
            description="""Add a new task to a goal's todo list.

Adds a single task to the specified goal/unit. Unit defaults to current week.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Goal ID (fitness, calendar, hindi, etc.)"
                    },
                    "task": {
                        "type": "string",
                        "description": "Task ID (e.g., 'yoga-session', 'extra-run')"
                    },
                    "name": {
                        "type": "string",
                        "description": "Human-readable task name"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit (week-2, chapter-3). Defaults to current week."
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed instructions (shown in dashboard)"
                    }
                },
                "required": ["goal", "task", "name"]
            }
        ),

        # ==================== SCHEDULE ====================
        Tool(
            name="schedule",
            description="""Add calendar event - personal or goal-linked.

Default is personal (no tracking). Add 'goal' param to track.
Add 'task' param to link to specific todo task.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Event title"
                    },
                    "time": {
                        "type": "string",
                        "description": "When: 'today 4pm', 'tomorrow 9am', or ISO datetime"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Duration in minutes (default: 30)"
                    },
                    "goal": {
                        "type": "string",
                        "description": "Goal to link (adds [Goal] prefix, uses goal color)"
                    },
                    "task": {
                        "type": "string",
                        "description": "Task ID to link (syncs to todo.yml)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Event description"
                    }
                },
                "required": ["title", "time"]
            }
        ),

        # ==================== EDIT ====================
        Tool(
            name="edit",
            description="""Modify an existing goal task.

Use to update task properties, add notes, or delete tasks.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Goal ID"
                    },
                    "task": {
                        "type": "string",
                        "description": "Task ID to edit"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit (defaults to current week)"
                    },
                    "name": {
                        "type": "string",
                        "description": "New task name"
                    },
                    "notes": {
                        "type": "string",
                        "description": "New notes"
                    },
                    "done": {
                        "type": "boolean",
                        "description": "Override done status"
                    },
                    "delete": {
                        "type": "boolean",
                        "description": "Delete the task"
                    }
                },
                "required": ["goal", "task"]
            }
        ),

        # ==================== RESCHEDULE_EVENT ====================
        Tool(
            name="reschedule_event",
            description="Move a scheduled calendar event to a new time. Syncs changes to todo.yml if it's a goal task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "Calendar event ID (from list_calendar_events)"
                    },
                    "new_time": {
                        "type": "string",
                        "description": "New time: 'today 5pm', 'tomorrow 2pm', or ISO datetime"
                    }
                },
                "required": ["event_id", "new_time"]
            }
        ),

        # ==================== DELETE_EVENT ====================
        Tool(
            name="delete_event",
            description="Remove a calendar event. Clears scheduling info from todo.yml if it's a goal task.",
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

        # ==================== LIST_CALENDAR_EVENTS ====================
        Tool(
            name="list_calendar_events",
            description="Show calendar events from Google Calendar. Shows both goal events and personal events.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 168,
                        "description": "Hours ahead to look (default: 24, max: 1 week)"
                    },
                    "hours_back": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 168,
                        "description": "Hours back to look (default: 0, use to see past events)"
                    }
                },
                "required": []
            }
        ),

        # ==================== MEMORY_CONDENSE ====================
        Tool(
            name="memory_condense",
            description="""Condense memory by summarizing old entries. Use when memory gets long.
Provide condensed_entries to replace all existing memory. Keep key patterns and significant insights.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "condensed_entries": {
                        "type": "array",
                        "description": "The condensed list of memory entries to save",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string", "description": "Date or range (e.g., '2026-01-01 to 2026-01-15')"},
                                "text": {"type": "string", "description": "The condensed observation"}
                            },
                            "required": ["date", "text"]
                        }
                    }
                },
                "required": ["condensed_entries"]
            }
        ),

        # ==================== MANAGE_PROGRESS ====================
        Tool(
            name="manage_progress",
            description="""Manage learning progress and schedule adjustments for goals.

Actions:
- view: Show current status (learning, reviewing, completed chapters; week offsets)
- start: Start learning a new chapter (adds to learning array)
- review: Move chapter from learning to reviewing
- complete: Complete a chapter (move from reviewing to completed)
- focus: Set which chapters to show in dashboard focus
- offset: Adjust week offset for time-based goals (e.g., injury causing 2-week delay)
- override: Override current week entirely (ignores date calculation)
- clear: Clear offset/override to resume normal schedule

Examples:
- manage_progress goal=hindi action=view
- manage_progress goal=hindi action=start chapter=02-compound-postpositions
- manage_progress goal=fitness action=offset weeks=2 reason="Pulled muscle"
- manage_progress goal=fitness action=clear""",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Goal ID (hindi, fitness, calendar, work-boundaries, spend-less, trading)"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["view", "start", "review", "complete", "focus", "offset", "override", "clear"],
                        "description": "Action to perform"
                    },
                    "chapter": {
                        "type": "string",
                        "description": "Chapter ID for start/review/complete (e.g., '01-foundations-of-case')"
                    },
                    "chapters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of chapter IDs for focus action"
                    },
                    "weeks": {
                        "type": "integer",
                        "minimum": -52,
                        "maximum": 52,
                        "description": "Weeks to offset (positive = behind schedule)"
                    },
                    "week": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 52,
                        "description": "Week number to override to"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for offset/override (stored for reference)"
                    }
                },
                "required": ["goal", "action"]
            }
        ),

        # ==================== HINDI PRACTICE ====================

        Tool(
            name="push_hindi_practice",
            description="""Generate a Hindi practice prompt and push to phone via Pushover.
Uses Anki mastery data to weight vocabulary selection:
- 10% new words (introduce)
- 40% learning (active drilling)
- 35% young (reinforcement)
- 15% mature (keep fresh)
Includes dialogue context for voice practice with Gemini Live.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "unit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 18,
                        "description": "Unit to focus on (default: current from progress tracking)"
                    },
                    "word_count": {
                        "type": "integer",
                        "minimum": 5,
                        "maximum": 50,
                        "description": "Number of vocab words to include (default: 20)"
                    },
                    "include_dialogue": {
                        "type": "boolean",
                        "description": "Include dialogue context for conversation practice (default: true)"
                    }
                },
                "required": []
            }
        ),

        # ==================== WGER TOOLS ====================

        Tool(
            name="get_workout_context",
            description="""Get workout planning context: recent workouts, muscle fatigue, available exercises.
Returns RAW DATA for Claude to create intelligent workout recommendations.
Call this when user asks "what should I do today" or wants workout advice.
Claude should interpret this data considering user's current state (energy, time, goals).""",
            inputSchema={
                "type": "object",
                "properties": {
                    "equipment_set": {
                        "type": "string",
                        "enum": ["home", "gym", "travel"],
                        "description": "Equipment preset (default from config)"
                    },
                    "equipment": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Override with specific equipment list"
                    },
                    "days_history": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 30,
                        "description": "Days of history to include (default: 7)"
                    }
                },
                "required": []
            }
        ),

        Tool(
            name="log_workout",
            description="""Log a completed workout session to wger with exercise details.
Auto-syncs duration to daily.yml fitness tracking.
For quick "walked 30 min" without exercise details, use log_goal goal=fitness instead.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "exercises": {
                        "type": "array",
                        "description": "Array of exercises: [{name, sets, reps, weight}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Exercise name"},
                                "sets": {"type": "integer", "description": "Number of sets"},
                                "reps": {"type": "integer", "description": "Reps per set"},
                                "weight": {"type": "number", "description": "Weight in kg"}
                            },
                            "required": ["name"]
                        }
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Total workout minutes"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Session notes"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "YYYY-MM-DD (default: today)"
                    }
                },
                "required": ["exercises"]
            }
        ),

        Tool(
            name="search_exercise",
            description="""Search wger exercise database by name, muscle, or equipment.
Use to find exercise IDs for logging, or to explore available exercises.
Returns exercise details including muscles worked and required equipment.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search by name (e.g., 'bench', 'squat')"
                    },
                    "muscle": {
                        "type": "string",
                        "description": "Filter by muscle: Chest, Back, Legs, Shoulders, Biceps, Triceps, Abs, Calves"
                    },
                    "equipment": {
                        "type": "string",
                        "description": "Filter by equipment: Dumbbell, Barbell, Pull-up bar, etc."
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category: Chest, Arms, Back, Legs, Shoulders, Abs, Calves, Cardio"
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "description": "Max results (default: 10)"
                    }
                },
                "required": []
            }
        ),

        Tool(
            name="log_weight",
            description="""Log body weight to wger. Returns current weight with trend analysis.
Use for daily weigh-ins or periodic weight tracking.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "weight": {
                        "type": "number",
                        "description": "Weight value"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["kg", "lbs"],
                        "description": "Unit (default: kg)"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "YYYY-MM-DD (default: today)"
                    }
                },
                "required": ["weight"]
            }
        ),

        Tool(
            name="get_workout_history",
            description="""Get detailed workout history with exercises, sets, weights.
Use to review past workouts, track progress, or analyze patterns.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 90,
                        "description": "Days to look back (default: 7)"
                    }
                },
                "required": []
            }
        ),

        Tool(
            name="get_fitness_summary",
            description="""Get combined fitness dashboard: weight trend, workout stats, progress.
Use for weekly reviews or "how am I doing" questions.""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),

        Tool(
            name="log_meal",
            description="""Log food to wger nutrition diary. Searches ingredient database for macros.
For manual entry without lookup, provide calories/protein/carbs/fat directly.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Food description ('chicken breast 200g')"
                    },
                    "calories": {
                        "type": "integer",
                        "description": "Override calories"
                    },
                    "protein": {
                        "type": "number",
                        "description": "Override protein (g)"
                    },
                    "carbs": {
                        "type": "number",
                        "description": "Override carbs (g)"
                    },
                    "fat": {
                        "type": "number",
                        "description": "Override fat (g)"
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "snack"],
                        "description": "Meal type"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "YYYY-MM-DD (default: today)"
                    }
                },
                "required": ["description"]
            }
        ),

        Tool(
            name="get_nutrition_summary",
            description="""Get nutrition summary: calories, macros by day or period.
Use to review eating patterns or check daily intake.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "YYYY-MM-DD (default: today)"
                    },
                    "days": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 30,
                        "description": "Days for average (default: 1)"
                    }
                },
                "required": []
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

    # Show current week for time-based goals
    schedule = get_schedule()
    current_week_info = get_current_week(schedule)
    if current_week_info:
        week_num = current_week_info.get("number", "?")
        week_start = current_week_info.get("start", "")
        week_end = current_week_info.get("end", "")
        if week_start and week_end:
            # Format as "Jan 6-12" style
            from datetime import datetime as dt
            try:
                start_dt = dt.strptime(week_start, "%Y-%m-%d")
                end_dt = dt.strptime(week_end, "%Y-%m-%d")
                start_str = start_dt.strftime("%b %-d")
                end_str = end_dt.strftime("%-d")
                lines.append(f"**Week {week_num}** ({start_str}-{end_str})")
            except:
                lines.append(f"**Week {week_num}**")
        else:
            lines.append(f"**Week {week_num}**")
        lines.append("")

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
    # Filter to only show current week (or earlier) for time-weekly goals
    current_week_num = current_week_info.get("number") if current_week_info else None
    time_weekly_goals = {"fitness", "calendar", "work-boundaries"}

    def is_current_or_past_week(goal_id: str, unit: str) -> bool:
        """Check if task is from current week or earlier."""
        if goal_id not in time_weekly_goals:
            return True  # Non-weekly goals show all
        if not unit.startswith("week-"):
            return True
        if current_week_num is None:
            return True
        try:
            task_week = int(unit.split("-")[1])
            return task_week <= current_week_num
        except (ValueError, IndexError):
            return True

    filtered_tasks = [pt for pt in pending_tasks if is_current_or_past_week(pt["goal_id"], pt["unit"])]

    if filtered_tasks:
        lines.append("**Pending tasks:**")
        # Group by goal
        by_goal = {}
        for pt in filtered_tasks:
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


def handle_done(arguments: dict) -> list[TextContent]:
    """
    Handle done tool - unified completion action with cascading updates.

    Behavior:
    1. If task provided: mark it done in current week's todos
    2. If duration provided: log to goal logs
    3. Sync to daily.yml based on goal type
    """
    goal_input = arguments.get("goal", "")
    task_id = arguments.get("task")
    duration = arguments.get("duration")
    date = arguments.get("date", get_today())
    notes = arguments.get("notes")

    if not goal_input:
        return [TextContent(type="text", text="goal is required")]

    # Resolve goal ID
    config = get_goals_config()
    goals = config.get("goals", {})
    goal_id = resolve_goal_id(goals, goal_input)

    if not goal_id:
        available = ", ".join(goals.keys())
        return [TextContent(type="text", text=f"Unknown goal: '{goal_input}'. Available: {available}")]

    # Get current week for this date
    schedule = get_schedule()
    week_info = get_current_week(schedule)
    week_num = week_info.get("number", 1)

    # Check if the date falls in a different week
    for week in schedule.get("weeks", []):
        if week["start"] <= date <= week["end"]:
            week_num = week["number"]
            break

    unit = f"week-{week_num}"

    result_lines = []
    daily_updated = {}

    # Mark task done if provided
    if task_id:
        updated = update_todo_task(
            goal_id, unit, task_id,
            done=True, notes=notes, clear_schedule=True
        )

        if updated:
            result_lines.append(f"Marked {task_id} done in {unit}")
            if notes:
                result_lines.append(f"Notes: {notes}")

            # If task had a calendar event, mark it complete
            cleared_event_id = updated.get("_cleared_event_id")
            if cleared_event_id:
                cal_result = calendar_service.mark_goal_complete(cleared_event_id)
                if cal_result.get("success"):
                    result_lines.append("Calendar event marked complete")
        else:
            return [TextContent(type="text", text=f"Task '{task_id}' not found in {goal_id}/{unit}")]

    # Log duration if provided
    if duration:
        logs = get_goal_logs(goal_id)

        # Find or create day entry
        day_entry = None
        for d in logs:
            if d.get("date") == date:
                day_entry = d
                break

        if not day_entry:
            day_entry = {"date": date, "entries": []}
            logs.append(day_entry)

        if "entries" not in day_entry:
            day_entry["entries"] = []

        entry = {"value": duration}
        if notes:
            entry["notes"] = notes

        day_entry["entries"].append(entry)

        # Update total
        total = sum(e.get("value", 0) for e in day_entry["entries"] if isinstance(e.get("value"), (int, float)))
        day_entry["total"] = total

        save_goal_logs(goal_id, logs)
        result_lines.append(f"Logged {duration} min to {goal_id}")

    # Sync to daily.yml based on goal type
    if goal_id == "fitness" and duration:
        current_daily = get_daily_entry(date)
        current_fitness = current_daily.get("fitness", 0) if current_daily else 0
        new_fitness = current_fitness + duration
        update_daily_entry(date, fitness=new_fitness)
        daily_updated["fitness"] = new_fitness

    elif goal_id == "calendar":
        update_daily_entry(date, calendar=True)
        daily_updated["calendar"] = True

    elif goal_id == "hindi":
        current_daily = get_daily_entry(date)
        current_hindi = current_daily.get("hindi", 0) if current_daily else 0
        new_hindi = current_hindi + 1
        update_daily_entry(date, hindi=new_hindi)
        daily_updated["hindi"] = new_hindi

    if daily_updated:
        updates_str = ", ".join(f"{k}={v}" for k, v in daily_updated.items())
        result_lines.append(f"Daily updated: {updates_str}")

    if not result_lines:
        return [TextContent(type="text", text="No action taken. Provide task and/or duration.")]

    return [TextContent(type="text", text="\n".join(result_lines))]


def handle_status(arguments: dict) -> list[TextContent]:
    """
    Handle status tool - unified view of goal progress and pending tasks.

    Shows exact task IDs so the AI can use done(goal, task=...) directly.
    """
    goal_filter = arguments.get("goal")
    date = arguments.get("date", get_today())

    config = get_goals_config()
    goals = config.get("goals", {})

    # Resolve goal filter if provided
    if goal_filter:
        goal_filter = resolve_goal_id(goals, goal_filter)
        if not goal_filter:
            available = ", ".join(goals.keys())
            return [TextContent(type="text", text=f"Unknown goal. Available: {available}")]

    # Get current time and day info
    now = datetime.now()
    time_str = now.strftime("%I:%M%p").lower().lstrip("0")

    # Get day abbreviation for filtering today's tasks
    from datetime import datetime as dt
    date_obj = dt.strptime(date, "%Y-%m-%d")
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_abbrev = days[date_obj.weekday()]

    # Get current week
    schedule = get_schedule()
    week_info = get_current_week(schedule)
    week_num = week_info.get("number", 1) if week_info else 1

    # Check if date falls in a different week
    for week in schedule.get("weeks", []):
        if week["start"] <= date <= week["end"]:
            week_num = week["number"]
            break

    lines = [f"Status ({date}, {time_str})", ""]

    # Week info
    if week_info:
        week_start = week_info.get("start", "")
        week_end = week_info.get("end", "")
        if week_start and week_end:
            try:
                start_dt = dt.strptime(week_start, "%Y-%m-%d")
                end_dt = dt.strptime(week_end, "%Y-%m-%d")
                lines.append(f"**Week {week_num}** ({start_dt.strftime('%b %-d')}-{end_dt.strftime('%-d')})")
            except:
                lines.append(f"**Week {week_num}**")
        lines.append("")

    # Today's progress from daily.yml
    daily_entry = get_daily_entry(date)
    if daily_entry:
        lines.append("**Today's Progress:**")
        lines.append(f"  Calendar: {'✓' if daily_entry.get('calendar') else '✗'}")
        lines.append(f"  Fitness: {daily_entry.get('fitness', 0)} min")
        lines.append(f"  Hindi: {daily_entry.get('hindi', 0)} sessions")
        lines.append("")

    # Get all pending tasks
    pending_tasks = get_all_pending_tasks()

    # Filter by goal if specified
    if goal_filter:
        pending_tasks = [pt for pt in pending_tasks if pt["goal_id"] == goal_filter]

    # Filter to current week or earlier for time-weekly goals
    time_weekly_goals = {"fitness", "calendar", "work-boundaries"}

    def is_current_or_past_week(goal_id: str, task_unit: str) -> bool:
        if goal_id not in time_weekly_goals:
            return True
        if not task_unit.startswith("week-"):
            return True
        try:
            task_week = int(task_unit.split("-")[1])
            return task_week <= week_num
        except (ValueError, IndexError):
            return True

    pending_tasks = [pt for pt in pending_tasks if is_current_or_past_week(pt["goal_id"], pt["unit"])]

    # Separate today's tasks (day-prefixed) from others
    today_tasks = []
    other_tasks = []

    for pt in pending_tasks:
        task = pt["task"]
        task_id = task.get("id", "")
        if task_id.startswith(f"{day_abbrev}-"):
            today_tasks.append(pt)
        else:
            other_tasks.append(pt)

    # Show today's tasks with exact IDs
    if today_tasks:
        lines.append(f"**Pending Today ({day_abbrev.capitalize()}):**")
        for pt in today_tasks:
            task = pt["task"]
            task_id = task.get("id", "")
            task_name = task.get("name", task_id)
            lines.append(f"  - {pt['goal_id']}: `{task_id}` - {task_name}")
        lines.append("")

    # Show other pending tasks (grouped by goal)
    if other_tasks and not goal_filter:
        lines.append("**Other Pending:**")
        by_goal = {}
        for pt in other_tasks:
            gid = pt["goal_id"]
            if gid not in by_goal:
                by_goal[gid] = []
            by_goal[gid].append(pt)

        for gid, tasks in by_goal.items():
            shown = tasks[:3]
            for pt in shown:
                task = pt["task"]
                task_id = task.get("id", "")
                lines.append(f"  - {gid}: `{task_id}`")
            if len(tasks) > 3:
                lines.append(f"    (+{len(tasks) - 3} more)")
        lines.append("")
    elif other_tasks and goal_filter:
        lines.append(f"**Pending ({goal_filter}):**")
        for pt in other_tasks[:10]:
            task = pt["task"]
            task_id = task.get("id", "")
            task_name = task.get("name", task_id)
            lines.append(f"  - `{task_id}`: {task_name}")
        if len(other_tasks) > 10:
            lines.append(f"  (+{len(other_tasks) - 10} more)")
        lines.append("")

    # Upcoming calendar events
    upcoming_events = calendar_service.get_upcoming_events(hours_ahead=4)
    if upcoming_events:
        lines.append("**Coming Up:**")
        for e in upcoming_events:
            prefix = "[Goal] " if e["is_goal"] else ""
            lines.append(f"  - {e['time']}: {prefix}{e['title']}")
        lines.append("")

    # Recent memory
    recent_memory = get_recent_memory(limit=3)
    if recent_memory:
        lines.append("**Recent Memory:**")
        for entry in recent_memory:
            lines.append(f"  - [{entry.get('date', '?')}] {entry.get('text', '')[:60]}...")
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_remember(arguments: dict) -> list[TextContent]:
    """Handle remember tool - save observation/insight to memory."""
    text = arguments.get("text", "")
    date = arguments.get("date", get_today())

    if not text:
        return [TextContent(type="text", text="text is required")]

    add_memory_entry(text, date)
    return [TextContent(type="text", text=f"Remembered: {text[:50]}{'...' if len(text) > 50 else ''}")]


def handle_plan(arguments: dict) -> list[TextContent]:
    """Handle plan tool - add a single task to a goal's todo list."""
    goal_input = arguments.get("goal", "")
    task_id = arguments.get("task", "")
    name = arguments.get("name", "")
    unit = arguments.get("unit")
    description = arguments.get("description")

    if not goal_input or not task_id or not name:
        return [TextContent(type="text", text="goal, task, and name are required")]

    # Resolve goal
    config = get_goals_config()
    goals = config.get("goals", {})
    goal_id = resolve_goal_id(goals, goal_input)

    if not goal_id:
        available = ", ".join(goals.keys())
        return [TextContent(type="text", text=f"Unknown goal: '{goal_input}'. Available: {available}")]

    # Default to current week if no unit specified
    if not unit:
        schedule = get_schedule()
        week_info = get_current_week(schedule)
        week_num = week_info.get("number", 1) if week_info else 1
        unit = f"week-{week_num}"

    # Load existing todo or create new
    todo = get_unit_todo(goal_id, unit)
    tasks = todo.get("tasks", [])

    # Check if task already exists
    for t in tasks:
        if t.get("id") == task_id:
            return [TextContent(type="text", text=f"Task '{task_id}' already exists in {goal_id}/{unit}")]

    # Add new task
    new_task = {"id": task_id, "name": name, "done": False}
    if description:
        new_task["description"] = description

    tasks.append(new_task)
    todo["tasks"] = tasks
    save_unit_todo(goal_id, unit, todo)

    return [TextContent(type="text", text=f"Added task '{task_id}' to {goal_id}/{unit}")]


def handle_schedule(arguments: dict) -> list[TextContent]:
    """Handle schedule tool - add calendar event (personal or goal-linked)."""
    title = arguments.get("title", "")
    time_str = arguments.get("time", "")

    if not title or not time_str:
        return [TextContent(type="text", text="title and time are required")]

    # Parse time
    time = calendar_service.parse_time(time_str)
    if not time:
        return [TextContent(type="text", text=f"Could not parse time: '{time_str}'. Try 'today 4pm' or 'tomorrow 9am'")]

    duration = arguments.get("duration", 30)
    goal_input = arguments.get("goal")
    task_id = arguments.get("task")
    notes = arguments.get("notes", "")

    # Check for conflicts
    conflicts = calendar_service.check_conflicts(time, duration)
    conflict_warning = ""
    if conflicts:
        conflict_warning = f"\nConflicts with: {', '.join(c['title'] for c in conflicts)}"

    # Handle goal linking
    goal_id = None
    color_id = None

    if goal_input:
        config = get_goals_config()
        goals = config.get("goals", {})
        goal_id = resolve_goal_id(goals, goal_input)
        if goal_id:
            goal_config = goals[goal_id]
            goal_name = goal_config.get("name", goal_id)
            color_id = goal_config.get("color")
            # Prefix title with [Goal]
            title = f"[Goal] {goal_name} - {title}"

    # Create calendar event using gcsa
    from gcsa.event import Event

    gc = calendar_service.get_calendar()
    if not gc:
        return [TextContent(type="text", text="Calendar not authenticated. Run calendar auth first.")]

    end_time = time + timedelta(minutes=duration)
    event = Event(
        title,
        start=time,
        end=end_time,
        description=notes if notes else None,
        color_id=str(color_id) if color_id else None,
    )

    try:
        created = gc.add_event(event)
        event_id = created.event_id
    except Exception as e:
        return [TextContent(type="text", text=f"Failed to create event: {e}")]

    time_formatted = time.strftime("%I:%M%p").lower().lstrip("0")
    date_formatted = time.strftime("%a %b %-d")
    result_lines = [f"Scheduled '{title}' for {date_formatted} at {time_formatted}"]

    # If task specified, link to todo
    if goal_id and task_id:
        schedule = get_schedule()
        week_info = get_current_week(schedule)
        week_num = week_info.get("number", 1) if week_info else 1
        unit = f"week-{week_num}"

        updated = update_todo_task(
            goal_id, unit, task_id,
            scheduled_for=time.isoformat(),
            event_id=event_id
        )
        if updated:
            result_lines.append(f"Linked to {goal_id}/{unit}/{task_id}")
        else:
            result_lines.append(f"Warning: Task '{task_id}' not found in {goal_id}/{unit}")

    if conflict_warning:
        result_lines.append(conflict_warning)

    return [TextContent(type="text", text="\n".join(result_lines))]


def handle_edit(arguments: dict) -> list[TextContent]:
    """Handle edit tool - modify an existing goal task."""
    goal_input = arguments.get("goal", "")
    task_id = arguments.get("task", "")

    if not goal_input or not task_id:
        return [TextContent(type="text", text="goal and task are required")]

    # Resolve goal
    config = get_goals_config()
    goals = config.get("goals", {})
    goal_id = resolve_goal_id(goals, goal_input)

    if not goal_id:
        available = ", ".join(goals.keys())
        return [TextContent(type="text", text=f"Unknown goal: '{goal_input}'. Available: {available}")]

    # Get unit (default to current week)
    unit = arguments.get("unit")
    if not unit:
        schedule = get_schedule()
        week_info = get_current_week(schedule)
        week_num = week_info.get("number", 1) if week_info else 1
        unit = f"week-{week_num}"

    # Handle delete
    if arguments.get("delete"):
        todo = get_unit_todo(goal_id, unit)
        tasks = todo.get("tasks", [])
        original_len = len(tasks)
        tasks = [t for t in tasks if t.get("id") != task_id]

        if len(tasks) == original_len:
            return [TextContent(type="text", text=f"Task '{task_id}' not found in {goal_id}/{unit}")]

        todo["tasks"] = tasks
        save_unit_todo(goal_id, unit, todo)
        return [TextContent(type="text", text=f"Deleted task '{task_id}' from {goal_id}/{unit}")]

    # Handle updates
    updates = {}
    if "name" in arguments:
        updates["name"] = arguments["name"]
    if "notes" in arguments:
        updates["notes"] = arguments["notes"]
    if "done" in arguments:
        updates["done"] = arguments["done"]

    if not updates:
        return [TextContent(type="text", text="No updates specified. Provide name, notes, done, or delete.")]

    # Apply updates
    todo = get_unit_todo(goal_id, unit)
    tasks = todo.get("tasks", [])
    found = False

    for t in tasks:
        if t.get("id") == task_id:
            t.update(updates)
            found = True
            break

    if not found:
        return [TextContent(type="text", text=f"Task '{task_id}' not found in {goal_id}/{unit}")]

    todo["tasks"] = tasks
    save_unit_todo(goal_id, unit, todo)

    updates_str = ", ".join(f"{k}={v}" for k, v in updates.items())
    return [TextContent(type="text", text=f"Updated {task_id}: {updates_str}")]


def handle_reschedule_event(arguments: dict) -> list[TextContent]:
    """Handle reschedule_event tool - move a calendar event to a new time."""
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


def handle_delete_event(arguments: dict) -> list[TextContent]:
    """Handle delete_event tool - remove a calendar event."""
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


def handle_list_calendar_events(arguments: dict) -> list[TextContent]:
    """Handle list_calendar_events tool - show calendar events."""
    hours = arguments.get("hours", 24)
    hours_back = arguments.get("hours_back", 0)
    events = calendar_service.get_upcoming_events(hours_ahead=hours, hours_back=hours_back)

    if not events:
        if not calendar_service.is_authenticated():
            return [TextContent(type="text", text="Not authenticated. Run: goals-mcp auth")]
        return [TextContent(type="text", text=f"No events in the next {hours} hours.")]

    # Group events by date
    from collections import defaultdict
    events_by_date = defaultdict(list)
    for e in events:
        date_key = e.get("date") or "Unknown"
        events_by_date[date_key].append(e)

    lines = [f"📅 Calendar ({hours}h):", ""]
    for date in sorted(events_by_date.keys()):
        day_events = events_by_date[date]
        # Get weekday from first event of the day
        weekday = day_events[0].get("weekday", "")
        lines.append(f"**{weekday} {date}**")
        for e in day_events:
            prefix = "[Goal] " if e["is_goal"] else ""
            duration = f" ({e['duration_min']} min)" if e["duration_min"] != 30 else ""
            lines.append(f"  • {e['time']} - {prefix}{e['title']}{duration}")
            if e.get("event_id"):
                lines.append(f"    ID: {e['event_id']}")
        lines.append("")  # Blank line between days

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


def handle_manage_progress(arguments: dict) -> list[TextContent]:
    """Handle manage_progress tool - manage learning progress and schedule adjustments."""
    goal = arguments.get("goal", "").lower()
    action = arguments.get("action", "")

    if not goal:
        return [TextContent(type="text", text="goal is required")]
    if not action:
        return [TextContent(type="text", text="action is required")]

    # Normalize goal aliases
    goal_map = {
        "hindi": "hindi",
        "fitness": "fitness",
        "gym": "fitness",
        "calendar": "calendar",
        "work-boundaries": "work-boundaries",
        "work": "work-boundaries",
        "spend-less": "spend-less",
        "spending": "spend-less",
        "trading": "trading",
    }
    goal_id = goal_map.get(goal, goal)

    current = get_current_progress()
    schedule = get_schedule()

    # Handle VIEW action
    if action == "view":
        lines = [f"**Progress: {goal_id}**", ""]

        if goal_id == "hindi":
            hindi = current.get("hindi", {})
            focus = hindi.get("focus", [])
            learning = hindi.get("learning", [])
            reviewing = hindi.get("reviewing", [])
            completed = hindi.get("completed", [])

            lines.append(f"**Focus:** {', '.join(focus) if focus else 'None set'}")
            lines.append(f"**Learning:** {', '.join(learning) if learning else 'None'}")
            lines.append(f"**Reviewing:** {', '.join(reviewing) if reviewing else 'None'}")
            lines.append(f"**Completed:** {len(completed)} chapters")
            if completed:
                lines.append(f"  {', '.join(completed)}")

        elif goal_id in ("fitness", "calendar", "work-boundaries"):
            goal_data = current.get(goal_id, {})
            current_week_info = get_current_week(schedule)
            effective = get_effective_week(goal_id, schedule, current)

            lines.append(f"**Schedule week:** {current_week_info.get('number', '?')}")
            lines.append(f"**Effective week:** {effective.get('number', '?')}")

            if goal_data.get("offset_weeks"):
                lines.append(f"**Offset:** {goal_data['offset_weeks']} weeks")
            if goal_data.get("override_week"):
                lines.append(f"**Override:** Week {goal_data['override_week']}")
            if goal_data.get("paused_until"):
                lines.append(f"**Paused until:** {goal_data['paused_until']}")
            if goal_data.get("adjustment_reason"):
                lines.append(f"**Reason:** {goal_data['adjustment_reason']}")

        elif goal_id == "spend-less":
            goal_data = current.get("spend-less", {})
            lines.append(f"**Offset phases:** {goal_data.get('offset_phases', 0)}")
            if goal_data.get("override_phase"):
                lines.append(f"**Override phase:** {goal_data['override_phase']}")

        elif goal_id == "trading":
            goal_data = current.get("trading", {})
            lines.append(f"**Offset periods:** {goal_data.get('offset_periods', 0)}")

        else:
            lines.append(f"No progress tracking for {goal_id}")

        return [TextContent(type="text", text="\n".join(lines))]

    # Handle START action (Hindi only)
    if action == "start":
        if goal_id != "hindi":
            return [TextContent(type="text", text="'start' action only applies to hindi goal")]

        chapter = arguments.get("chapter", "")
        if not chapter:
            return [TextContent(type="text", text="chapter is required for start action")]

        hindi = current.get("hindi", {})
        learning = hindi.get("learning", [])
        reviewing = hindi.get("reviewing", [])
        completed = hindi.get("completed", [])

        if chapter in learning:
            return [TextContent(type="text", text=f"'{chapter}' is already in learning")]
        if chapter in reviewing:
            return [TextContent(type="text", text=f"'{chapter}' is already in reviewing (use 'complete' to finish it)")]
        if chapter in completed:
            return [TextContent(type="text", text=f"'{chapter}' is already completed")]

        learning.append(chapter)
        # Auto-add to focus if focus is empty or has only this chapter
        focus = hindi.get("focus", [])
        if not focus or (len(focus) == 1 and focus[0] == learning[0] if len(learning) > 0 else True):
            focus = [chapter]

        update_current_goal("hindi", {
            "learning": learning,
            "focus": focus
        })

        return [TextContent(type="text", text=f"Started learning: {chapter}\nFocus: {', '.join(focus)}")]

    # Handle REVIEW action (Hindi only)
    if action == "review":
        if goal_id != "hindi":
            return [TextContent(type="text", text="'review' action only applies to hindi goal")]

        chapter = arguments.get("chapter", "")
        if not chapter:
            return [TextContent(type="text", text="chapter is required for review action")]

        hindi = current.get("hindi", {})
        learning = hindi.get("learning", [])
        reviewing = hindi.get("reviewing", [])

        if chapter not in learning:
            return [TextContent(type="text", text=f"'{chapter}' is not in learning (add it first with 'start')")]

        learning.remove(chapter)
        reviewing.append(chapter)

        update_current_goal("hindi", {
            "learning": learning,
            "reviewing": reviewing
        })

        return [TextContent(type="text", text=f"Moved to reviewing: {chapter}\nLearning: {', '.join(learning) if learning else 'None'}\nReviewing: {', '.join(reviewing)}")]

    # Handle COMPLETE action (Hindi only)
    if action == "complete":
        if goal_id != "hindi":
            return [TextContent(type="text", text="'complete' action only applies to hindi goal")]

        chapter = arguments.get("chapter", "")
        if not chapter:
            return [TextContent(type="text", text="chapter is required for complete action")]

        hindi = current.get("hindi", {})
        learning = hindi.get("learning", [])
        reviewing = hindi.get("reviewing", [])
        completed = hindi.get("completed", [])

        if chapter in learning:
            learning.remove(chapter)
        elif chapter in reviewing:
            reviewing.remove(chapter)
        else:
            return [TextContent(type="text", text=f"'{chapter}' is not in learning or reviewing")]

        completed.append(chapter)

        # Update focus if the completed chapter was in focus
        focus = hindi.get("focus", [])
        if chapter in focus:
            focus.remove(chapter)
            # Set focus to first learning chapter if available
            if learning:
                focus = [learning[0]]
            elif reviewing:
                focus = [reviewing[0]]

        update_current_goal("hindi", {
            "learning": learning,
            "reviewing": reviewing,
            "completed": completed,
            "focus": focus
        })

        return [TextContent(type="text", text=f"Completed: {chapter}\nTotal completed: {len(completed)}")]

    # Handle FOCUS action (Hindi only)
    if action == "focus":
        if goal_id != "hindi":
            return [TextContent(type="text", text="'focus' action only applies to hindi goal")]

        chapters = arguments.get("chapters", [])
        chapter = arguments.get("chapter")

        # Allow single chapter via 'chapter' param
        if chapter and not chapters:
            chapters = [chapter]

        if not chapters:
            return [TextContent(type="text", text="chapters array (or chapter) is required for focus action")]

        update_current_goal("hindi", {"focus": chapters})

        return [TextContent(type="text", text=f"Focus set to: {', '.join(chapters)}")]

    # Handle OFFSET action (time-based goals)
    if action == "offset":
        if goal_id not in ("fitness", "calendar", "work-boundaries", "spend-less", "trading"):
            return [TextContent(type="text", text=f"'offset' action not applicable to {goal_id}")]

        weeks = arguments.get("weeks")
        reason = arguments.get("reason", "")

        if weeks is None:
            return [TextContent(type="text", text="weeks is required for offset action")]

        if goal_id in ("fitness", "calendar", "work-boundaries"):
            updates = {"offset_weeks": int(weeks)}
            if reason:
                updates["adjustment_reason"] = reason
            # Clear override if setting offset
            updates["override_week"] = None
            update_current_goal(goal_id, updates)

            effective = get_effective_week(goal_id, schedule)
            return [TextContent(type="text", text=f"Offset set: {weeks} weeks\nEffective week: {effective.get('number', '?')}" + (f"\nReason: {reason}" if reason else ""))]

        elif goal_id == "spend-less":
            update_current_goal("spend-less", {"offset_phases": int(weeks)})
            return [TextContent(type="text", text=f"Phase offset set: {weeks}")]

        elif goal_id == "trading":
            update_current_goal("trading", {"offset_periods": int(weeks)})
            return [TextContent(type="text", text=f"Period offset set: {weeks}")]

    # Handle OVERRIDE action (time-based goals)
    if action == "override":
        if goal_id not in ("fitness", "calendar", "work-boundaries", "spend-less"):
            return [TextContent(type="text", text=f"'override' action not applicable to {goal_id}")]

        week = arguments.get("week")
        reason = arguments.get("reason", "")

        if goal_id in ("fitness", "calendar", "work-boundaries"):
            if week is None:
                return [TextContent(type="text", text="week is required for override action")]

            updates = {"override_week": int(week)}
            if reason:
                updates["adjustment_reason"] = reason
            # Clear offset if setting override
            updates["offset_weeks"] = 0
            update_current_goal(goal_id, updates)

            return [TextContent(type="text", text=f"Week override set: {week}" + (f"\nReason: {reason}" if reason else ""))]

        elif goal_id == "spend-less":
            phase = arguments.get("chapter", "")  # reuse chapter param for phase
            if not phase:
                return [TextContent(type="text", text="Use chapter param for phase ID (e.g., 'phase-2')")]
            update_current_goal("spend-less", {"override_phase": phase})
            return [TextContent(type="text", text=f"Phase override set: {phase}")]

    # Handle CLEAR action
    if action == "clear":
        if goal_id in ("fitness", "calendar", "work-boundaries"):
            update_current_goal(goal_id, {
                "offset_weeks": 0,
                "override_week": None,
                "paused_until": None,
                "adjustment_reason": None
            })
            current_week_info = get_current_week(schedule)
            return [TextContent(type="text", text=f"Cleared all adjustments for {goal_id}\nNow on schedule week: {current_week_info.get('number', '?')}")]

        elif goal_id == "spend-less":
            update_current_goal("spend-less", {
                "offset_phases": 0,
                "override_phase": None
            })
            return [TextContent(type="text", text=f"Cleared all adjustments for spend-less")]

        elif goal_id == "trading":
            update_current_goal("trading", {"offset_periods": 0})
            return [TextContent(type="text", text=f"Cleared offset for trading")]

        else:
            return [TextContent(type="text", text=f"No adjustments to clear for {goal_id}")]

    return [TextContent(type="text", text=f"Unknown action: {action}")]


# ==================== HINDI PRACTICE HANDLERS ====================

def handle_push_hindi_practice(arguments: dict) -> list[TextContent]:
    """Handle push_hindi_practice tool - generate comprehensive practice prompt."""
    from . import anki
    from . import pushover
    from . import gist
    import json
    import re
    from pathlib import Path

    unit = arguments.get("unit")
    word_count = arguments.get("word_count", 100)  # Default to 100 words
    include_dialogue = arguments.get("include_dialogue", True)

    # Get current unit from progress if not specified
    if unit is None:
        current = get_current_progress()
        hindi_progress = current.get("hindi", {})
        focus = hindi_progress.get("focus", [])
        learning = hindi_progress.get("learning", [])

        for chapter_list in [focus, learning]:
            for chapter in chapter_list:
                match = re.search(r'(\d+)', chapter)
                if match:
                    unit = int(match.group(1))
                    break
            if unit:
                break

        if not unit:
            unit = 1

    # Load Anki mastery cache
    cache = anki.get_mastery_cache()
    if not cache:
        try:
            cache = anki._load_mastery_sync()
            anki._mastery_cache = cache
            anki._cache_loaded = True
        except Exception:
            cache = {}

    # Get vocab with tier-based selection (scales if not enough in one tier)
    vocab_items = anki.get_vocab_for_practice(current_unit=unit, count=word_count)

    # Load unit data for grammar and dialogues
    extracted_dir = Path(__file__).parent.parent.parent.parent.parent / "study-materials" / "extracted" / "raw"
    json_path = extracted_dir / f"{unit:02d}.json"

    unit_data = None
    if json_path.exists():
        with open(json_path) as f:
            unit_data = json.load(f)

    # ==================== BUILD COMPREHENSIVE PROMPT ====================

    # Get unit title
    unit_title = unit_data.get("unit_title", f"Unit {unit}") if unit_data else f"Unit {unit}"

    # Get grammar section titles for context
    grammar_topics = []
    if unit_data and unit_data.get("grammar_sections"):
        grammar_topics = [gs.get("title", "") for gs in unit_data["grammar_sections"][:3]]

    prompt_parts = []

    # 1. CONVERSATION FRAMEWORK - optimized for A2 learner based on real feedback
    prompt_parts.append(f"""# Hindi Conversation Practice

You are Arjun (male) or Priya (female), a Hindi conversation partner.

## ABOUT THE LEARNER
- **Name:** Mark (male - use masculine forms: karta, gaya, accha)
- **Level:** A2 (early intermediate)
- **Use "tum" not "aap"** - we're friends, keep it casual
- **Learning style:** Needs word-by-word breakdowns, appreciates when you acknowledge his corrections

## CRITICAL RULES - READ CAREFULLY

### Don't Interrupt
- **Let the learner finish speaking** - even if they pause or struggle
- Wait for them to complete their thought before responding
- If they trail off with "..." or pause, wait - don't jump in

### Correct Mistakes IMMEDIATELY
- **If you hear a mistake, correct it RIGHT THEN** - don't wait
- Short correction: "Small fix: X should be Y"
- Don't let mistakes pass uncorrected - that's your job

### No Excessive Validation
- **NEVER say "You're absolutely right" or "That's a great question"**
- Be direct and concise, not sycophantic
- If they correct you, just say "Got it" and move on
- Skip the praise-heavy language - it's annoying

### Speed & Pacing
- **Hindi: Speak at 70% of natural speed** - the learner needs time to process
- **English: Speak at 110% speed** - no need to slow down for explanations
- Pause briefly between Hindi sentences

### Response Length
- **Maximum 2 Hindi sentences per response** (occasionally 3 if simple)
- **English explanations: 1-2 sentences MAX** - be concise
- Always end with ONE simple question
- Less is more - if you can say it shorter, do

### Language Mirroring (SIMPLE RULE)
- **Learner speaks Hindi → You speak Hindi**
- **Learner speaks English → You speak 100% English**
- **Learner asks a question in English → Answer ENTIRELY in English, zero Hindi**
- ❌ WRONG: User asks "What does X mean?" → "X ka matlab hai..."
- ✅ CORRECT: User asks "What does X mean?" → "X means [English explanation]."

### When Learner is Confused - SIMPLIFY, DON'T ELABORATE
- **NEVER add more Hindi when they don't understand**
- **NEVER repeat the same complex phrase**
- Switch to English, explain simply, then try a DIFFERENT simpler Hindi sentence
- ❌ WRONG: They don't understand → You explain with MORE Hindi
- ✅ CORRECT: They don't understand → Full English explanation, then new simple topic

### Acknowledge Self-Corrections
- When learner corrects themselves, praise it: "Good catch!" or "Yes, that's right!"
- This reinforces their learning

### Incorporate Feedback
- If learner says "that's too complex" or "slow down" → adjust immediately
- If learner gives ANY meta-feedback about the conversation → follow it
- Remember their preferences throughout the session

### STAY ON TOPIC (CRITICAL)
- **Keep asking follow-up questions about what THEY just said**
- **Do NOT change topics unless learner says "next topic" or similar**
- If they mention a museum → ask more about the museum
- If they mention their girlfriend → ask about her
- ❌ WRONG: They talk about airplanes → You ask about favorite color
- ✅ CORRECT: They talk about airplanes → "Which airplane was coolest?" or "Do you like flying?"
- The vocab list is for WEAVING INTO conversation, NOT for choosing topics

---

## Current Session

**Unit {unit}: {unit_title}**

**Grammar Focus:**
{chr(10).join('- ' + t for t in grammar_topics) if grammar_topics else '- Basic conversation'}

## Learner's Current Level (A2 - Early Intermediate)

**KNOWS:**
- Present tense (simple: hai/hain/ho/hoon)
- Basic postpositions (mein, pe, ko, se, ke liye)
- Basic pronouns (main, tum, aap, yeh, voh)
- Question words (kya, kaun, kahan, kyun, kaise)
- Common adjectives (accha, bura, bada, chhota)

**DOES NOT KNOW YET (avoid these):**
- Past tense (except basic tha/thi/the)
- Future tense
- Subjunctive
- Causatives
- Ne-construction
- Complex compound verbs
""")

    # 2. VOCABULARY SECTION (100 words with tiers)
    prompt_parts.append("\n---\n\n# VOCABULARY TO PRACTICE\n")
    prompt_parts.append("*Work these words into the conversation naturally. Don't drill - use them in context.*\n")

    if vocab_items:
        # Group by tier for clarity
        by_tier = {"new": [], "learning": [], "young": [], "mature": []}
        for v in vocab_items:
            tier_name = v.tier.value if v.tier else "new"
            by_tier[tier_name].append(v)

        for tier_name, tier_label in [("new", "Priority: New Words (introduce these)"), ("learning", "Reinforce: Learning"), ("young", "Practice: Getting Stronger"), ("mature", "Review: Known Words")]:
            if by_tier[tier_name]:
                prompt_parts.append(f"\n## {tier_label} ({len(by_tier[tier_name])})")
                for v in by_tier[tier_name]:
                    prompt_parts.append(f"- {v.transliteration} = {v.meaning}")
    else:
        prompt_parts.append("\n(No Anki vocab loaded)")

    # 3. GRAMMAR RULES FROM UNIT
    if unit_data and unit_data.get("grammar_sections"):
        prompt_parts.append("\n---\n\n# GRAMMAR FROM THIS UNIT\n")
        prompt_parts.append("*Use these patterns in conversation. When learner struggles, explain in English.*\n")
        for gs in unit_data["grammar_sections"][:3]:
            prompt_parts.append(f"\n## {gs.get('title', 'Grammar')}")
            if gs.get("key_points"):
                for kp in gs["key_points"][:3]:
                    prompt_parts.append(f"- {kp}")
            if gs.get("rules"):
                for rule in gs["rules"][:2]:
                    prompt_parts.append(f"\n**Pattern:** {rule.get('rule', '')}")
                    if rule.get("examples"):
                        ex = rule["examples"][0]
                        prompt_parts.append(f"  → {ex.get('transliteration', '')} = \"{ex.get('english', '')}\"")

    # 4. DIALOGUE EXAMPLES
    if unit_data and unit_data.get("dialogues") and include_dialogue:
        prompt_parts.append("\n---\n\n# EXAMPLE DIALOGUES FROM UNIT\n")
        prompt_parts.append("*These show the target patterns. Use similar structures.*\n")
        for dlg in unit_data["dialogues"][:1]:  # Just first dialogue
            prompt_parts.append(f"\n**{dlg.get('title', 'Dialogue')}**")
            if dlg.get("context"):
                prompt_parts.append(f"*{dlg['context']}*\n")
            for turn in dlg.get("turns", [])[:4]:  # First 4 turns only
                prompt_parts.append(f"**{turn.get('speaker', '?')}:** {turn.get('transliteration', '')}")
                prompt_parts.append(f"  → {turn.get('english', '')}")

    # 5. CONVERSATION TOPICS - make it interesting!
    prompt_parts.append("""
---

# CONVERSATION TOPICS

**IMPORTANT:** These are STARTING points only. Once a topic begins, STAY ON IT until learner says "next topic."
The vocab list is for weaving into ANY topic - don't let it drive topic choice.

## Weird Hypotheticals
- "If you could delete one invention from history, what?"
- "If animals could talk, which would be rudest?"
- "If you were a ghost, who would you haunt?"
- "What conspiracy theory do you kind of believe?"
- "If you had no fear, what would you do?"

## Opinions & Debates
- "What's something everyone loves but you hate?"
- "What's overrated? What's underrated?"
- "Spicy food vs sweet food - which is better?"
- "Home cooking vs restaurants?"
- "What hill would you die on that nobody cares about?"

## Stories & Experiences
- "Most embarrassing moment?"
- "Strangest thing that happened recently?"
- "Worst date or awkward situation?"
- "A time you were completely wrong?"
- "Funniest misunderstanding?"

## Travel & Places
- "Best place you've traveled?"
- "Dream destination - mountains or beaches?"
- "Weirdest food you've tried somewhere?"
- "A place that surprised you?"

## People & Relationships
- "Who's the weirdest person in your family?"
- "What's your friend group like?"
- "Pettiest reason you stopped being friends with someone?"
- "Celebrity you'd want to meet?"

## Science & Big Questions
- "Do you think aliens exist?"
- "What would you ask if you could know ONE truth?"
- "Climate change - are we screwed?"
- "AI - exciting or scary?"

## Hobbies & Skills
- "What's your most useless skill?"
- "Gaming, reading, sports - what do you do for fun?"
- "What do you want to learn?"
- "Weird hobby you have or want?"

## Whatever They Bring Up
- If they mention ANYTHING → dig deeper into THAT
- Ask "why?", "what happened next?", "how did that feel?"
- Don't jump to a new topic - explore what they said

---

# HOW TO KEEP IT FLOWING

**Conversation Techniques:**
- React with emotion: "Sach mein?!", "Kya baat hai!", "Pagal hai kya!"
- Use fillers naturally: "Arey", "Yaar", "Accha", "Hmm"
- Share your own (made up) opinions to model sentences
- Disagree sometimes to create discussion: "Main agree nahi karta..."
- Ask follow-ups: "Kyun?", "Aur phir?", "Kaisa laga?"

**If conversation stalls:**
- Switch topics: "Accha, ek aur baat..."
- Ask a random question: "Ek random sawaal - tumhari favorite color kya hai?"
- Relate to something they said earlier

---

# HOW TO HANDLE COMMON SITUATIONS

**When learner asks "How do I say X?"**
→ Answer in English: "You say [word]. It means [meaning]."
→ Keep it simple. Don't over-explain.

**When learner makes a grammar mistake:**
→ In English: "Small fix: [explanation]. Try: [correct form]"

**When learner says "I don't understand":**
→ STOP using Hindi. Switch to full English.
→ Explain the concept simply.
→ Then ask a NEW, SIMPLER question - don't repeat the confusing one.

**When learner asks to break down a sentence:**
→ Go word by word in English: "'Mujhe' = 'to me'. 'Pasand' = 'liking'. 'Hai' = 'is'."

**When learner corrects themselves:**
→ "Good catch!" or "Exactly!" - acknowledge it before continuing.

**When learner gives feedback about the conversation:**
→ Say "Got it!" and immediately adjust your approach.
→ Don't defend or explain - just adapt.

---

# START THE CONVERSATION

Begin with a simple greeting (2 sentences max):
- "Namaste! Main [Arjun/Priya] hoon. Tum kaise ho?"

Then ask ONE simple question about their day or pick a random topic.

**Remember: 70% speed, 2 sentences max, English corrections!**
""")

    full_prompt = "\n".join(prompt_parts)

    # ==================== CREATE GIST AND PUSH ====================

    gist_result = gist.create_gist(
        content=full_prompt,
        description=f"Hindi Practice - Unit {unit}",
    )

    if not gist_result.success:
        return [TextContent(type="text", text=f"Failed to create gist: {gist_result.message}")]

    # Push URL to phone
    push_result = pushover.push_notification(
        title=f"Hindi Practice - Unit {unit}",
        message=f"{len(vocab_items)} words ready!\nTap to open prompt.",
        url=gist_result.url,
        url_title="Open Practice Prompt",
    )

    if push_result.success:
        return [TextContent(
            type="text",
            text=f"Practice prompt created and pushed!\n\nUnit: {unit}\nWords: {len(vocab_items)}\nGist: {gist_result.url}\n\nPreview:\n{full_prompt[:800]}..."
        )]
    else:
        return [TextContent(type="text", text=f"Gist created but push failed: {push_result.message}\n\nGist URL: {gist_result.url}")]


# ==================== WGER HANDLERS ====================

def handle_get_workout_context(arguments: dict) -> list[TextContent]:
    """Handle get_workout_context tool - get data for workout planning."""
    equipment_set = arguments.get("equipment_set")
    equipment = arguments.get("equipment")
    days_history = arguments.get("days_history", 7)

    result = wger_service.get_workout_context(
        equipment_set=equipment_set,
        equipment=equipment,
        days_history=days_history
    )

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    import json
    lines = ["**Workout Context**", ""]

    # Recent workouts
    workouts = result.get("recent_workouts", [])
    if workouts:
        lines.append("**Recent Workouts:**")
        for w in workouts[-5:]:  # Last 5
            exercises_str = ", ".join(w.get("exercises", [])[:3])
            if len(w.get("exercises", [])) > 3:
                exercises_str += f" +{len(w['exercises']) - 3} more"
            lines.append(f"  • {w['date']} ({w['focus']}): {exercises_str}")
        lines.append("")

    # Muscle fatigue
    fatigue = result.get("muscle_fatigue", {})
    if fatigue:
        lines.append("**Muscle Recovery:**")
        sorted_fatigue = sorted(fatigue.items(), key=lambda x: x[1], reverse=True)
        for muscle, level in sorted_fatigue:
            if level > 0:
                status = "🔴 fatigued" if level > 0.6 else "🟡 recovering" if level > 0.3 else "🟢 ready"
                lines.append(f"  • {muscle}: {int(level * 100)}% {status}")
            else:
                lines.append(f"  • {muscle}: ✓ recovered")
        lines.append("")

    # Equipment
    equipment_list = result.get("equipment_available", [])
    if equipment_list:
        lines.append(f"**Equipment:** {', '.join(equipment_list)}")
        lines.append("")

    # Available exercises summary
    exercises = result.get("available_exercises", [])
    if exercises:
        # Group by category
        by_category = {}
        for ex in exercises:
            cat = ex.get("category", "Other")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(ex["name"])

        lines.append("**Available Exercises:**")
        for cat, ex_list in sorted(by_category.items()):
            preview = ", ".join(ex_list[:3])
            if len(ex_list) > 3:
                preview += f" +{len(ex_list) - 3}"
            lines.append(f"  • {cat}: {preview}")
        lines.append("")

    # Exercise history (PRs, last weights)
    history = result.get("exercise_history", {})
    if history:
        lines.append("**Recent Performance:**")
        for name, data in list(history.items())[:5]:
            weight = data.get("last_weight", 0)
            reps = data.get("last_reps", 0)
            if weight > 0:
                lines.append(f"  • {name}: {weight}kg x {reps}")
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_log_workout(arguments: dict) -> list[TextContent]:
    """Handle log_workout tool - log a workout session to wger."""
    exercises = arguments.get("exercises", [])
    duration = arguments.get("duration")
    notes = arguments.get("notes", "")
    date = arguments.get("date")

    if not exercises:
        return [TextContent(type="text", text="exercises array is required")]

    result = wger_service.log_workout(
        exercises=exercises,
        duration=duration,
        notes=notes,
        date=date
    )

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    lines = [f"✓ {result['message']}", ""]

    for ex in result.get("exercises", []):
        status = "✓" if ex.get("status") == "logged" else "✗"
        if ex.get("weight"):
            lines.append(f"  {status} {ex['name']}: {ex['sets']}x{ex['reps']} @ {ex['weight']}kg")
        else:
            lines.append(f"  {status} {ex['name']}: {ex.get('sets', 1)}x{ex.get('reps', 0)}")

    if duration:
        lines.append("")
        lines.append(f"Duration: {duration} min")

        # Sync to daily.yml fitness tracking
        try:
            current_daily = get_daily_entry(result.get("date", get_today()))
            current_fitness = current_daily.get("fitness", 0) if current_daily else 0
            update_daily_entry(result.get("date", get_today()), fitness=current_fitness + duration)
            lines.append("Daily fitness synced ✓")
        except Exception as e:
            lines.append(f"Daily sync failed: {e}")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_search_exercise(arguments: dict) -> list[TextContent]:
    """Handle search_exercise tool - search exercise database."""
    query = arguments.get("query")
    muscle = arguments.get("muscle")
    equipment = arguments.get("equipment")
    category = arguments.get("category")
    limit = arguments.get("limit", 10)

    result = wger_service.search_exercise(
        query=query,
        muscle=muscle,
        equipment=equipment,
        category=category,
        limit=limit
    )

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    exercises = result.get("exercises", [])
    if not exercises:
        return [TextContent(type="text", text="No exercises found matching criteria.")]

    lines = [f"**Found {len(exercises)} exercises:**", ""]

    for ex in exercises:
        muscles = ", ".join(ex.get("muscles", [])[:3]) or "N/A"
        equip = ", ".join(ex.get("equipment", [])) or "Bodyweight"
        lines.append(f"**{ex['name']}** (ID: {ex['id']})")
        lines.append(f"  Category: {ex.get('category', 'N/A')} | Muscles: {muscles}")
        lines.append(f"  Equipment: {equip}")
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_log_weight(arguments: dict) -> list[TextContent]:
    """Handle log_weight tool - log body weight."""
    weight = arguments.get("weight")
    unit = arguments.get("unit", "kg")
    date = arguments.get("date")

    if weight is None:
        return [TextContent(type="text", text="weight is required")]

    result = wger_service.log_weight(weight=weight, unit=unit, date=date)

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    lines = [f"✓ {result['message']}", ""]

    if result.get("avg_7d"):
        lines.append(f"  7-day avg: {result['avg_7d']} kg")
    if result.get("avg_30d"):
        lines.append(f"  30-day avg: {result['avg_30d']} kg")
    if result.get("change") is not None:
        direction = "↑" if result["change"] > 0 else "↓" if result["change"] < 0 else "→"
        lines.append(f"  Change: {direction} {abs(result['change'])} kg from last")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_get_workout_history(arguments: dict) -> list[TextContent]:
    """Handle get_workout_history tool - get workout history."""
    days = arguments.get("days", 7)

    result = wger_service.get_workout_history(days=days)

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    workouts = result.get("workouts", [])
    if not workouts:
        return [TextContent(type="text", text=f"No workouts in the last {days} days.")]

    lines = [f"**Workout History ({days} days, {len(workouts)} sessions):**", ""]

    for w in workouts:
        lines.append(f"**{w['date']}** - {w['focus']}")
        for ex in w.get("exercises", [])[:5]:
            lines.append(f"  • {ex}")
        if len(w.get("exercises", [])) > 5:
            lines.append(f"  • +{len(w['exercises']) - 5} more")
        if w.get("notes"):
            lines.append(f"  Notes: {w['notes']}")
        lines.append("")

    # Muscle fatigue summary
    fatigue = result.get("muscle_fatigue", {})
    fatigued = [(m, f) for m, f in fatigue.items() if f > 0.3]
    if fatigued:
        lines.append("**Current Fatigue:**")
        for muscle, level in sorted(fatigued, key=lambda x: x[1], reverse=True):
            lines.append(f"  • {muscle}: {int(level * 100)}%")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_get_fitness_summary(arguments: dict) -> list[TextContent]:
    """Handle get_fitness_summary tool - get fitness dashboard."""
    result = wger_service.get_fitness_summary()

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    lines = ["**Fitness Summary**", ""]

    # Weight
    weight = result.get("weight")
    if weight:
        lines.append("**Weight:**")
        if weight.get("current"):
            lines.append(f"  Current: {weight['current']} kg")
        if weight.get("avg_7d"):
            lines.append(f"  7-day avg: {weight['avg_7d']} kg")
        if weight.get("change_7d") is not None:
            direction = "↑" if weight["change_7d"] > 0 else "↓" if weight["change_7d"] < 0 else "→"
            lines.append(f"  7-day change: {direction} {abs(weight['change_7d'])} kg")
        lines.append("")

    # Workouts
    workouts = result.get("workouts", {})
    if workouts:
        lines.append("**Activity:**")
        lines.append(f"  This week: {workouts.get('workouts_7d', 0)} workouts")
        lines.append(f"  This month: {workouts.get('workouts_30d', 0)} workouts")
        lines.append("")

    # Muscle balance
    balance = result.get("muscle_balance", {})
    if balance:
        worked = [(m, f) for m, f in balance.items() if f > 0]
        rested = [m for m, f in balance.items() if f == 0]

        if worked:
            lines.append("**Recently Worked:**")
            for muscle, level in sorted(worked, key=lambda x: x[1], reverse=True)[:4]:
                lines.append(f"  • {muscle}")

        if rested:
            lines.append("**Ready to Train:**")
            lines.append(f"  {', '.join(rested)}")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_log_meal(arguments: dict) -> list[TextContent]:
    """Handle log_meal tool - log food to nutrition diary."""
    description = arguments.get("description", "")
    if not description:
        return [TextContent(type="text", text="description is required")]

    calories = arguments.get("calories")
    protein = arguments.get("protein")
    carbs = arguments.get("carbs")
    fat = arguments.get("fat")
    meal_type = arguments.get("meal_type")
    date = arguments.get("date")

    result = wger_service.log_meal(
        description=description,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat,
        meal_type=meal_type,
        date=date
    )

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    if not result.get("success"):
        return [TextContent(type="text", text=result.get("message", "Failed to log meal"))]

    lines = [f"✓ {result['message']}", ""]

    if result.get("ingredient_matched"):
        lines.append(f"Matched: {result['ingredient_matched']}")

    if result.get("calories"):
        lines.append(f"  Calories: {result['calories']}")
    if result.get("protein"):
        lines.append(f"  Protein: {result['protein']}g")
    if result.get("carbs"):
        lines.append(f"  Carbs: {result['carbs']}g")
    if result.get("fat"):
        lines.append(f"  Fat: {result['fat']}g")

    return [TextContent(type="text", text="\n".join(lines))]


def handle_get_nutrition_summary(arguments: dict) -> list[TextContent]:
    """Handle get_nutrition_summary tool - get nutrition summary."""
    date = arguments.get("date")
    days = arguments.get("days", 1)

    result = wger_service.get_nutrition_summary(date=date, days=days)

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    lines = [f"**Nutrition Summary ({result.get('date', 'today')})**", ""]

    entries = result.get("entries", 0)
    if entries == 0:
        lines.append("No food logged yet today.")
    else:
        lines.append(f"**{entries} entries:**")
        lines.append(f"  Calories: {result.get('calories', 0)}")
        lines.append(f"  Protein: {result.get('protein', 0)}g")
        lines.append(f"  Carbs: {result.get('carbs', 0)}g")
        lines.append(f"  Fat: {result.get('fat', 0)}g")

    return [TextContent(type="text", text="\n".join(lines))]


async def handle_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls to handlers."""
    # Core tools
    if name == "check_in":
        return handle_check_in()
    elif name == "done":
        return handle_done(arguments)
    elif name == "status":
        return handle_status(arguments)
    elif name == "remember":
        return handle_remember(arguments)
    elif name == "plan":
        return handle_plan(arguments)
    elif name == "schedule":
        return handle_schedule(arguments)
    elif name == "edit":
        return handle_edit(arguments)

    # Calendar tools
    elif name == "reschedule_event":
        return handle_reschedule_event(arguments)
    elif name == "delete_event":
        return handle_delete_event(arguments)
    elif name == "list_calendar_events":
        return handle_list_calendar_events(arguments)

    # Memory tools
    elif name == "memory_condense":
        return handle_memory_condense(arguments)

    # Progress tools
    elif name == "manage_progress":
        return handle_manage_progress(arguments)

    # Hindi practice
    elif name == "push_hindi_practice":
        return handle_push_hindi_practice(arguments)

    # Wger tools
    elif name == "get_workout_context":
        return handle_get_workout_context(arguments)
    elif name == "log_workout":
        return handle_log_workout(arguments)
    elif name == "search_exercise":
        return handle_search_exercise(arguments)
    elif name == "log_weight":
        return handle_log_weight(arguments)
    elif name == "get_workout_history":
        return handle_get_workout_history(arguments)
    elif name == "get_fitness_summary":
        return handle_get_fitness_summary(arguments)
    elif name == "log_meal":
        return handle_log_meal(arguments)
    elif name == "get_nutrition_summary":
        return handle_get_nutrition_summary(arguments)

    return [TextContent(type="text", text=f"Unknown tool: {name}")]
