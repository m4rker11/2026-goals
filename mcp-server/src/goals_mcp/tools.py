"""MCP tool definitions and handlers."""

from datetime import datetime, timedelta

from mcp.types import TextContent, Tool

from .storage import (
    get_goals_config, get_goal_logs, save_goal_logs,
    get_unit_todo, save_unit_todo, update_todo_task, get_all_pending_tasks,
    get_all_scheduled_tasks, find_task_by_event_id,
    get_today, get_daily_entry, update_daily_entry, get_daily_entries, to_date_str,
    get_memory_entries, save_memory_entries, add_memory_entry, get_recent_memory,
    get_schedule, get_current_progress, update_current_goal, get_current_week, get_effective_week
)
from .goals import get_current, compute_todos, resolve_goal_id
from . import calendar_service
from . import tasks_service
from . import wger_service


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

    # Dynamic log_goal description with available goals
    log_goal_desc = f"""Log progress on a goal. Available goals: {goals_list or 'hindi, fitness, calendar, brother, trading, sell, spend-less, work-boundaries'}.
Auto-syncs to daily.yml for fitness/calendar/hindi. Use path for subgoals. Optionally mark a todo task done."""

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

        # ==================== LOG_GOAL ====================
        Tool(
            name="log_goal",
            description=log_goal_desc,
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Goal ID or alias (e.g., 'fitness', 'hindi', 'calendar')"
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
                        "description": "Notes about what was accomplished"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
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
                        "description": "Notes to add to the todo task (learnings, context)"
                    }
                },
                "required": ["goal"]
            }
        ),

        # ==================== LOG_DAILY ====================
        Tool(
            name="log_daily",
            description="Record daily mood and reflection notes. Updates _data/daily.yml for the Jekyll dashboard.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mood": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "Energy/motivation level (1=low, 5=high)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Brief reflection on the day"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Date in YYYY-MM-DD format (defaults to today)"
                    }
                },
                "required": []
            }
        ),

        # ==================== EDIT_GOAL_LOG ====================
        Tool(
            name="edit_goal_log",
            description="Edit or delete a specific log entry. Use index to target entries within the same day (0=first, -1=last).",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Goal ID or alias (e.g., 'fitness', 'hindi')"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Date of entry to edit (YYYY-MM-DD)"
                    },
                    "index": {
                        "type": "integer",
                        "description": "Entry index within the day (0=first, -1=last). Defaults to 0."
                    },
                    "path": {
                        "type": "string",
                        "description": "Path of entry to edit (if applicable)"
                    },
                    "value": {
                        "type": ["number", "boolean"],
                        "description": "New value to set"
                    },
                    "notes": {
                        "type": "string",
                        "description": "New notes to set"
                    },
                    "delete": {
                        "type": "boolean",
                        "description": "Set to true to delete the entry entirely"
                    }
                },
                "required": ["goal", "date"]
            }
        ),

        # ==================== GET_GOAL_STATUS ====================
        Tool(
            name="get_goal_status",
            description="Get detailed status and recent activity for a goal or all goals.",
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

        # ==================== READ_TODO ====================
        Tool(
            name="read_todo",
            description="Read todo tasks for a specific unit (week/chapter). Returns task list with completion status and notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Goal ID or alias (e.g., 'fitness', 'hindi')"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit identifier (e.g., 'week-1', '01-foundations-of-case')"
                    }
                },
                "required": ["goal", "unit"]
            }
        ),

        # ==================== WRITE_TODO ====================
        Tool(
            name="write_todo",
            description="Create or overwrite the todo list for a unit. Use when setting up tasks for a new week/chapter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Goal ID or alias (e.g., 'fitness', 'hindi')"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit identifier (e.g., 'week-1', '01-foundations-of-case')"
                    },
                    "tasks": {
                        "type": "array",
                        "description": "List of tasks to create",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "Task identifier (e.g., 'vocab', 'synopsis')"},
                                "name": {"type": "string", "description": "Human-readable task name"},
                                "done": {"type": "boolean", "description": "Whether task is complete (default: false)"},
                                "notes": {"type": "string", "description": "Optional notes about the task"},
                                "description": {"type": "string", "description": "Detailed instructions (shown in dashboard, calendar)"}
                            },
                            "required": ["id", "name"]
                        }
                    }
                },
                "required": ["goal", "unit", "tasks"]
            }
        ),

        # ==================== SCHEDULE_GOAL_TASK ====================
        Tool(
            name="schedule_goal_task",
            description="Schedule a goal todo task on Google Calendar. Creates [Goal] prefixed event and syncs to todo.yml.",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Goal ID or alias (e.g., 'fitness', 'hindi')"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit identifier (e.g., 'week-1', '01-foundations-of-case')"
                    },
                    "task": {
                        "type": "string",
                        "description": "Task ID to schedule (from todo.yml)"
                    },
                    "time": {
                        "type": "string",
                        "description": "When to schedule: 'today 4pm', 'tomorrow 9am', or ISO datetime"
                    },
                    "duration": {
                        "type": "integer",
                        "minimum": 5,
                        "maximum": 480,
                        "description": "Duration in minutes (default: 30, max: 8 hours)"
                    },
                    "calendar": {
                        "type": "string",
                        "description": "Calendar name (e.g., 'Personal', 'Work'). Defaults to primary."
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes for the calendar event"
                    },
                    "invite": {
                        "type": "array",
                        "items": {"type": "string", "format": "email"},
                        "description": "Email addresses to invite"
                    }
                },
                "required": ["goal", "unit", "task", "time"]
            }
        ),

        # ==================== ADD_CALENDAR_EVENT ====================
        Tool(
            name="add_calendar_event",
            description="Add an event to Google Calendar. Use 'goal' param to link to a goal (adds [Goal] prefix and uses goal's color).",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Event title"
                    },
                    "time": {
                        "type": "string",
                        "description": "When to schedule: 'today 4pm', 'tomorrow 9am', or ISO datetime"
                    },
                    "duration": {
                        "type": "integer",
                        "minimum": 5,
                        "maximum": 480,
                        "description": "Duration in minutes (default: 30, max: 8 hours)"
                    },
                    "goal": {
                        "type": "string",
                        "description": "Goal to link this event to (e.g., 'hindi', 'fitness'). Adds [Goal] prefix and uses goal's color."
                    },
                    "calendar": {
                        "type": "string",
                        "description": "Calendar name (e.g., 'Personal', 'Work'). Defaults to primary."
                    },
                    "notes": {
                        "type": "string",
                        "description": "Event description/notes"
                    },
                    "color": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 11,
                        "description": "Color ID: 9=blue(Work), 2=green(Personal), 3=purple(Social), 11=red(Health), 6=orange. Overrides goal color if set."
                    },
                    "create_task": {
                        "type": "boolean",
                        "description": "Also create Google Task (default: false)"
                    }
                },
                "required": ["title", "time"]
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

        # ==================== MEMORY_SAVE ====================
        Tool(
            name="memory_save",
            description="""Save an observation to memory. Call when you notice:
- Behavioral patterns (e.g., "Skipped fitness 3rd day - said 'too tired' but watched TV")
- User quotes/commitments (e.g., "Quote: 'I'll definitely finish chapter 5 tomorrow'")
- Insights about what works/doesn't (e.g., "Completed fitness despite resistance - felt great after")
Memory is reviewed during check_in to surface patterns over time.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 500,
                        "description": "The observation, quote, or insight to remember"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Date in YYYY-MM-DD format (defaults to today)"
                    }
                },
                "required": ["text"]
            }
        ),

        # ==================== MEMORY_READ ====================
        Tool(
            name="memory_read",
            description="Read memory entries. Returns recent observations, quotes, and insights.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Number of entries to return (default: 10, max: 100)"
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


def handle_log_goal(arguments: dict) -> list[TextContent]:
    """Handle log_goal tool - logs progress on a specific goal."""
    goal_input = arguments.get("goal", "")
    log_date = arguments.get("date", get_today())

    if not goal_input:
        return [TextContent(type="text", text="goal is required. Use log_daily for mood/notes.")]

    config = get_goals_config()
    goals = config.get("goals", {})
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

        # Build the session entry
        entry = {}
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

        # Find or create day entry (nested format: {date, entries[], total})
        day_entry = None
        for d in logs:
            if d.get("date") == log_date:
                day_entry = d
                break

        if not day_entry:
            day_entry = {"date": log_date, "entries": []}
            logs.append(day_entry)

        # Ensure entries array exists (migrate old format)
        if "entries" not in day_entry:
            day_entry["entries"] = []

        day_entry["entries"].append(entry)

        # Update total for numeric values
        if "value" in entry and isinstance(entry["value"], (int, float)):
            total = sum(e.get("value", 0) for e in day_entry["entries"] if isinstance(e.get("value"), (int, float)))
            day_entry["total"] = total

        save_goal_logs(goal_id, logs)

        # Auto-sync to daily.yml for fitness, calendar, hindi
        log_date = entry.get("date", get_today())
        daily_synced = False

        if goal_id == "fitness" and "value" in entry:
            # Add fitness minutes to daily total
            current_daily = get_daily_entry(log_date)
            current_fitness = current_daily.get("fitness", 0) if current_daily else 0
            update_daily_entry(log_date, fitness=current_fitness + entry["value"])
            daily_synced = True

        elif goal_id == "calendar":
            # Mark calendar as done for the day
            update_daily_entry(log_date, calendar=True)
            daily_synced = True

        elif goal_id == "hindi":
            # Increment hindi chapter count
            current_daily = get_daily_entry(log_date)
            current_hindi = current_daily.get("hindi", 0) if current_daily else 0
            update_daily_entry(log_date, hindi=current_hindi + 1)
            daily_synced = True

    goal_name = goals[goal_id].get("name", goal_id)
    result_lines = []
    if entry:
        result_lines.append(f"Logged to {goal_name}: {entry}")
        if daily_synced:
            result_lines.append("Daily tracking synced ✓")

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


def handle_log_daily(arguments: dict) -> list[TextContent]:
    """Handle log_daily tool - records daily mood and reflection notes."""
    date = arguments.get("date", get_today())
    mood = arguments.get("mood")
    notes = arguments.get("notes")

    if mood is None and notes is None:
        # No input - show current daily status
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
            return [TextContent(type="text", text=f"No daily entry for {date}. Provide mood or notes to create one.")]

    # Update mood/notes in daily.yml
    fields = {}
    if mood is not None:
        fields["mood"] = mood
    if notes is not None:
        fields["notes"] = notes

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


def handle_edit_goal_log(arguments: dict) -> list[TextContent]:
    """Handle edit_goal_log tool - edit or delete existing log entries (nested format)."""
    config = get_goals_config()
    goals = config.get("goals", {})

    goal_input = arguments.get("goal", "")
    goal_id = resolve_goal_id(goals, goal_input)

    if not goal_id:
        return [TextContent(type="text", text=f"Unknown goal: '{goal_input}'")]

    logs = get_goal_logs(goal_id)
    target_date = arguments.get("date")
    entry_index = arguments.get("index", 0)  # Default to first entry
    target_path = arguments.get("path")

    # Find the day entry (nested format: {date, entries[], total})
    day_entry = None
    day_idx = None
    for i, d in enumerate(logs):
        if to_date_str(d.get("date")) == target_date:
            day_entry = d
            day_idx = i
            break

    if day_entry is None:
        return [TextContent(type="text", text=f"No entries found for {target_date}")]

    # Get entries array (support both old flat format and new nested format)
    entries = day_entry.get("entries", [])
    if not entries:
        # Old flat format - treat the day entry itself as the single entry
        entries = [day_entry]
        is_flat = True
    else:
        is_flat = False

    # Handle negative index
    if entry_index < 0:
        entry_index = len(entries) + entry_index

    if entry_index < 0 or entry_index >= len(entries):
        return [TextContent(type="text", text=f"Invalid index {arguments.get('index', 0)}. Day has {len(entries)} entries (use 0-{len(entries)-1})")]

    # Filter by path if specified
    if target_path:
        matching = [(i, e) for i, e in enumerate(entries) if e.get("path") == target_path]
        if not matching:
            return [TextContent(type="text", text=f"No entry with path={target_path} on {target_date}")]
        entry_index = matching[0][0]

    if arguments.get("delete"):
        if is_flat:
            # Delete the entire day entry for old format
            deleted = logs.pop(day_idx)
            save_goal_logs(goal_id, logs)
            return [TextContent(type="text", text=f"Deleted day entry: {deleted}")]
        else:
            deleted = entries.pop(entry_index)
            # Recalculate total
            if entries:
                total = sum(e.get("value", 0) for e in entries if isinstance(e.get("value"), (int, float)))
                day_entry["total"] = total
                day_entry["entries"] = entries
            else:
                # No entries left, remove the day
                logs.pop(day_idx)
            save_goal_logs(goal_id, logs)
            return [TextContent(type="text", text=f"Deleted entry: {deleted}")]

    # Update the entry
    entry = entries[entry_index]
    if "value" in arguments:
        if isinstance(arguments["value"], bool):
            entry["done"] = arguments["value"]
        else:
            entry["value"] = arguments["value"]

    if "notes" in arguments:
        entry["notes"] = arguments["notes"]

    # For nested format, update total
    if not is_flat:
        total = sum(e.get("value", 0) for e in entries if isinstance(e.get("value"), (int, float)))
        day_entry["total"] = total
        day_entry["entries"] = entries

    save_goal_logs(goal_id, logs)
    return [TextContent(type="text", text=f"Updated entry {entry_index}: {entry}")]


def handle_get_goal_status(arguments: dict) -> list[TextContent]:
    """Handle get_goal_status tool - get detailed status for goals."""
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

    # Check if this is a week-based unit and show current week context
    if unit.startswith("week-"):
        schedule = get_schedule()
        current_week_info = get_current_week(schedule)
        if current_week_info:
            current_week = current_week_info.get("number")
            try:
                requested_week = int(unit.split("-")[1])
                if requested_week != current_week:
                    lines.insert(1, f"⚠️ Note: Current week is {current_week}, showing {unit}")
                    lines.insert(2, "")
            except (ValueError, IndexError):
                pass

    pending = [t for t in tasks if not t.get("done", False)]
    done = [t for t in tasks if t.get("done", False)]

    if pending:
        lines.append("**Pending:**")
        for t in pending:
            line = f"- [ ] {t.get('name', t.get('id'))}"
            if t.get("notes"):
                line += f" ({t['notes']})"
            lines.append(line)
            if t.get("description"):
                # Indent description under task
                for desc_line in t["description"].strip().split("\n"):
                    lines.append(f"      {desc_line}")
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
        if t.get("description"):
            task["description"] = t["description"]
        tasks.append(task)

    todo_data = {"unit": unit, "tasks": tasks}
    save_unit_todo(goal_id, unit, todo_data)

    goal_name = goals[goal_id].get("name", goal_id)
    return [TextContent(type="text", text=f"Created todo for {goal_name}/{unit} with {len(tasks)} tasks")]


def handle_schedule_goal_task(arguments: dict) -> list[TextContent]:
    """Handle schedule_goal_task tool - schedule a goal todo task on calendar."""
    time_str = arguments.get("time", "")
    time = calendar_service.parse_time(time_str)
    if not time:
        return [TextContent(type="text", text=f"Could not parse time: '{time_str}'. Try 'today 4pm' or 'tomorrow 9am'")]

    duration = arguments.get("duration", 30)
    calendar_name = arguments.get("calendar")
    calendar_id = calendar_service.resolve_calendar(calendar_name) if calendar_name else None

    # Check for conflicts
    conflicts = calendar_service.check_conflicts(time, duration)
    conflict_warning = ""
    if conflicts:
        conflict_warning = f"\n⚠️ Conflicts with: {', '.join(c['title'] + ' at ' + c['time'] for c in conflicts)}"

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
        return [TextContent(type="text", text="unit and task are required")]

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

    goal_config = goals[goal_id]
    goal_name = goal_config.get("name", goal_id)
    task_name = task_info.get("name", task_id)
    task_description = task_info.get("description", "")
    color_id = goal_config.get("color")

    # Build notes: user notes or task name, plus description if available
    event_notes = arguments.get("notes") or task_name
    if task_description:
        event_notes = f"{event_notes}\n\n{task_description}"

    result = calendar_service.schedule_goal(
        goal_id=goal_id,
        goal_name=goal_name,
        time=time,
        duration_min=duration,
        notes=event_notes,
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


def handle_add_calendar_event(arguments: dict) -> list[TextContent]:
    """Handle add_calendar_event tool - add an event to calendar, optionally linked to a goal."""
    title = arguments.get("title", "")
    if not title:
        return [TextContent(type="text", text="title is required")]

    time_str = arguments.get("time", "")
    time = calendar_service.parse_time(time_str)
    if not time:
        return [TextContent(type="text", text=f"Could not parse time: '{time_str}'. Try 'today 4pm' or 'tomorrow 9am'")]

    duration = arguments.get("duration", 30)
    calendar_name = arguments.get("calendar")
    calendar_id = calendar_service.resolve_calendar(calendar_name) if calendar_name else None

    # Check for conflicts
    conflicts = calendar_service.check_conflicts(time, duration)
    conflict_warning = ""
    if conflicts:
        conflict_warning = f"\n⚠️ Conflicts with: {', '.join(c['title'] + ' at ' + c['time'] for c in conflicts)}"

    color_id = arguments.get("color")
    notes = arguments.get("notes", "")
    create_task = arguments.get("create_task", False)

    # Handle goal linking
    goal_input = arguments.get("goal")
    goal_id = None
    goal_name = None
    if goal_input:
        config = get_goals_config()
        goals = config.get("goals", {})
        from .goals import resolve_goal_id
        goal_id = resolve_goal_id(goals, goal_input)
        if goal_id:
            goal_config = goals[goal_id]
            goal_name = goal_config.get("name", goal_id)
            # Use goal's color if no explicit color provided
            if color_id is None:
                color_id = goal_config.get("color")
            # Prefix title with [Goal] goal_name
            title = f"[Goal] {goal_name} - {title}"

    # Build description
    description = ""
    if goal_id:
        description = f"Goal: {goal_id}\n"
    if notes:
        description += notes

    # If create_task, create Google Task first
    google_task_id = None
    if create_task:
        task_result = tasks_service.create_task(
            title=title,
            due_date=time.date(),
            notes=notes,
        )
        if task_result.get("success"):
            google_task_id = task_result.get("task_id")
            description = f"TaskID: {google_task_id}\n{notes}" if notes else f"TaskID: {google_task_id}"
        else:
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

        result_lines = [f"Created: {title} at {time.strftime('%I:%M%p').lower().lstrip('0')}"]
        if create_task and google_task_id:
            result_lines.append(f"Google Task created (ID: {google_task_id})")
        if created.event_id:
            result_lines.append(f"Event ID: {created.event_id}")
        if conflict_warning:
            result_lines.append(conflict_warning)

        return [TextContent(type="text", text="\n".join(result_lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Failed to create calendar event: {e}{conflict_warning}")]


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
    if name == "check_in":
        return handle_check_in()
    elif name == "log_goal":
        return handle_log_goal(arguments)
    elif name == "log_daily":
        return handle_log_daily(arguments)
    elif name == "edit_goal_log":
        return handle_edit_goal_log(arguments)
    elif name == "get_goal_status":
        return handle_get_goal_status(arguments)
    elif name == "read_todo":
        return handle_read_todo(arguments)
    elif name == "write_todo":
        return handle_write_todo(arguments)
    elif name == "schedule_goal_task":
        return handle_schedule_goal_task(arguments)
    elif name == "add_calendar_event":
        return handle_add_calendar_event(arguments)
    elif name == "reschedule_event":
        return handle_reschedule_event(arguments)
    elif name == "delete_event":
        return handle_delete_event(arguments)
    elif name == "list_calendar_events":
        return handle_list_calendar_events(arguments)
    elif name == "memory_save":
        return handle_memory_save(arguments)
    elif name == "memory_read":
        return handle_memory_read(arguments)
    elif name == "memory_condense":
        return handle_memory_condense(arguments)
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
