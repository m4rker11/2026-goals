"""Goal logic: progression tracking, current position, todos computation."""

from datetime import datetime, timedelta

from .storage import get_goal_logs, discover_content


def get_today() -> str:
    """Get today's date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def get_completed_items(logs: list) -> set:
    """Get set of completed top-level items from logs."""
    completed = set()
    for log in logs:
        if log.get("done") and log.get("path"):
            top_item = log["path"].split("/")[0]
            completed.add(top_item)
    return completed


def get_current(goal_config: dict, logs: list) -> dict:
    """
    Compute current position for a goal based on progression type.

    Returns dict with:
      - current: current item name (or None)
      - done: count of completed items
      - total: total items
      - week: week number (for time-weekly)
    """
    progression = goal_config.get("progression")
    content_path = goal_config.get("content")

    if not content_path:
        return {"current": None, "done": 0, "total": 0}

    items = discover_content(content_path)
    completed = get_completed_items(logs)
    done_count = len([i for i in items if i in completed])

    if progression == "sequential":
        current = None
        for item in items:
            if item not in completed:
                current = item
                break
        return {
            "current": current,
            "done": done_count,
            "total": len(items)
        }

    elif progression == "time-weekly":
        start_str = goal_config.get("start", "2026-01-01")
        start = datetime.strptime(start_str, "%Y-%m-%d")
        now = datetime.now()
        week_num = ((now - start).days // 7) + 1

        current = None
        for item in items:
            if f"week-{week_num}" in item.lower() or item == f"{week_num}":
                current = item
                break

        return {
            "current": current,
            "week": week_num,
            "done": done_count,
            "total": len(items)
        }

    elif progression == "unordered":
        return {
            "current": None,
            "done": done_count,
            "total": len(items)
        }

    return {"current": None, "done": 0, "total": 0}


def compute_todos(config: dict) -> list[dict]:
    """Compute what needs attention today."""
    todos = []
    today = get_today()
    now = datetime.now()
    goals = config.get("goals", {})

    for goal_id, goal_config in goals.items():
        logs = get_goal_logs(goal_id)
        cadence = goal_config.get("cadence")
        progression = goal_config.get("progression")
        name = goal_config.get("name", goal_id)

        # Find last log date
        last_log_date = None
        for log in reversed(logs):
            if "date" in log:
                last_log_date = log["date"]
                break

        # Cadence-based reminders
        if cadence == "daily":
            today_logs = [l for l in logs if l.get("date") == today]
            if not today_logs:
                todos.append({
                    "goal": goal_id,
                    "name": name,
                    "message": f"{name}: not done today",
                    "priority": "high"
                })

        elif cadence == "weekly":
            week_start = now - timedelta(days=now.weekday())
            week_start_str = week_start.strftime("%Y-%m-%d")
            week_total = sum(
                l.get("value", 0) for l in logs
                if l.get("date", "") >= week_start_str
            )
            unit = goal_config.get("unit", "")
            todos.append({
                "goal": goal_id,
                "name": name,
                "message": f"{name}: {week_total} {unit} this week",
                "priority": "info"
            })

        elif cadence == "every_2_weeks":
            if last_log_date:
                last_date = datetime.strptime(last_log_date, "%Y-%m-%d")
                days_since = (now - last_date).days
                if days_since >= 12:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: {days_since} days since last",
                        "priority": "high" if days_since >= 14 else "medium"
                    })
            else:
                todos.append({
                    "goal": goal_id,
                    "name": name,
                    "message": f"{name}: never done",
                    "priority": "medium"
                })

        # Progression-based status
        if progression:
            current_info = get_current(goal_config, logs)

            if progression == "sequential":
                current = current_info.get("current")
                done = current_info.get("done", 0)
                total = current_info.get("total", 0)
                if current:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: on {current} ({done}/{total})",
                        "priority": "info"
                    })
                elif total > 0 and done == total:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: complete! ({done}/{total})",
                        "priority": "info"
                    })

            elif progression == "time-weekly":
                week = current_info.get("week", 1)
                current = current_info.get("current")
                if current:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: Week {week} ({current})",
                        "priority": "info"
                    })
                else:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: Week {week}",
                        "priority": "info"
                    })

            elif progression == "unordered":
                done = current_info.get("done", 0)
                total = current_info.get("total", 0)
                if total > 0:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: {done}/{total} done",
                        "priority": "info"
                    })

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "info": 2}
    todos.sort(key=lambda x: priority_order.get(x.get("priority", "info"), 99))

    return todos


def resolve_goal_id(goals: dict, input_name: str) -> str | None:
    """Resolve alias or name to goal ID."""
    input_lower = input_name.lower()

    if input_lower in goals:
        return input_lower

    for goal_id, config in goals.items():
        aliases = config.get("aliases", [])
        if input_lower in [a.lower() for a in aliases]:
            return goal_id
        if config.get("name", "").lower() == input_lower:
            return goal_id

    return None
