"""MCP tool definitions and handlers."""

from datetime import datetime, timedelta

from mcp.types import TextContent, Tool

from .storage import (
    get_goals_config, get_goal_logs, save_goal_logs,
    get_unit_todo, save_unit_todo, update_todo_task, get_all_pending_tasks,
    get_today, get_daily_entry, update_daily_entry, get_daily_entries, to_date_str
)
from .goals import get_current, compute_todos, resolve_goal_id
from .git import commit_and_push


TOOL_DEFINITIONS = [
    Tool(
        name="check_in",
        description="Check what goals need attention today. Call this at the start of every conversation.",
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
        description="""Log progress on a goal. Use path for subgoals (e.g., 'chapter-3/vocab').
Optionally update a todo task when logging (marks task done and adds notes to the task).""",
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
        name="commit",
        description="Commit and push changes to git. Call after logging to update GitHub Pages.",
        inputSchema={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message (auto-generated if not provided)"
                }
            },
            "required": []
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
    )
]


def handle_check_in() -> list[TextContent]:
    """Handle check_in tool."""
    config = get_goals_config()
    goal_todos = compute_todos(config)
    pending_tasks = get_all_pending_tasks()

    # Get today's daily entry
    today_entry = get_daily_entry()

    lines = [f"📋 **Goals Check-in** ({get_today()})", ""]

    # Show today's daily status first
    if today_entry:
        lines.append("**Today's tracking:**")
        lines.append(f"  Calendar: {'✓' if today_entry.get('calendar') else '✗'}")
        lines.append(f"  Fitness: {today_entry.get('fitness', 0)} min")
        lines.append(f"  Hindi: {today_entry.get('hindi', 0)} chapters")
        if today_entry.get('mood'):
            lines.append(f"  Mood: {today_entry['mood']}/5")
        lines.append("")
    else:
        lines.append("**Today's tracking:** No entry yet. Use `daily` tool to log.")
        lines.append("")

    high = [t for t in goal_todos if t.get("priority") == "high"]
    medium = [t for t in goal_todos if t.get("priority") == "medium"]
    info = [t for t in goal_todos if t.get("priority") == "info"]

    if high:
        lines.append("**Needs attention:**")
        for t in high:
            lines.append(f"- {t['message']}")
        lines.append("")

    if medium:
        lines.append("**Coming up:**")
        for t in medium:
            lines.append(f"- {t['message']}")
        lines.append("")

    if info:
        lines.append("**Progress:**")
        for t in info:
            lines.append(f"- {t['message']}")
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
    result_lines = [f"Logged to {goal_name}: {entry}"]

    # Handle todo update if specified
    todo_unit = arguments.get("todo_unit")
    todo_task = arguments.get("todo_task")

    if todo_unit and todo_task:
        todo_notes = arguments.get("todo_notes")
        updated = update_todo_task(goal_id, todo_unit, todo_task, done=True, notes=todo_notes)
        if updated:
            result_lines.append(f"Todo updated: {todo_task} marked done")
            if todo_notes:
                result_lines.append(f"Task notes: {todo_notes}")
        else:
            result_lines.append(f"Warning: Task '{todo_task}' not found in {todo_unit}")

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


def handle_commit(arguments: dict) -> list[TextContent]:
    """Handle commit tool."""
    message = arguments.get("message", f"Update goals - {get_today()}")
    result = commit_and_push(message)
    return [TextContent(type="text", text=result["message"])]


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
    elif name == "commit":
        return handle_commit(arguments)
    elif name == "status":
        return handle_status(arguments)
    elif name == "read_todo":
        return handle_read_todo(arguments)
    elif name == "write_todo":
        return handle_write_todo(arguments)

    return [TextContent(type="text", text=f"Unknown tool: {name}")]
