"""Goal logic: progression tracking, current position, todos computation."""

from datetime import datetime, timedelta

from .storage import get_goal_logs, discover_content, get_today, to_date_str


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
        start_str = to_date_str(goal_config.get("start", "2026-01-01"))
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


def get_urgency_config(goal_config: dict) -> dict:
    """
    Get urgency configuration for a goal, applying smart defaults.

    Returns dict with urgency settings, inferring from goal config if not explicit.
    """
    explicit_urgency = goal_config.get("urgency", {})

    # If explicit type: none, return early
    if explicit_urgency.get("type") == "none":
        return {"type": "none"}

    cadence = goal_config.get("cadence")
    progression = goal_config.get("progression")

    # Smart defaults based on existing config
    if cadence == "daily":
        # Cadence-based urgency for daily goals
        return {
            "type": "cadence",
            "cadence": "daily",
            "due_by": explicit_urgency.get("due_by", "23:59"),
            "nag_from": explicit_urgency.get("nag_from", "07:00"),
        }

    elif cadence == "weekly":
        # Check if target-based urgency
        if explicit_urgency.get("type") == "target" or explicit_urgency.get("target"):
            return {
                "type": "target",
                "target": explicit_urgency.get("target", goal_config.get("target", 0)),
                "period": explicit_urgency.get("period", "weekly"),
                "warn_at": explicit_urgency.get("warn_at", 0.5),
                "under_is_good": explicit_urgency.get("under_is_good", False),
            }
        # Default to info for weekly without target
        return {
            "type": "cadence",
            "cadence": "weekly",
        }

    elif cadence == "every_2_weeks":
        # 14-day cadence urgency
        return {
            "type": "cadence",
            "cadence": "biweekly",
        }

    elif progression == "sequential":
        # Stale detection for sequential goals
        return {
            "type": "stale",
            "stale_days": explicit_urgency.get("stale_days", 5),
            "overdue_days": explicit_urgency.get("overdue_days", 7),
        }

    elif progression == "unordered":
        # Flexible goals - no urgency
        return {"type": "none"}

    # Default: no urgency
    return {"type": "none"}


def compute_todos(config: dict) -> list[dict]:
    """
    Compute what needs attention today.

    Returns todos with priority: "overdue" (red), "due" (yellow), "info" (gray)
    """
    todos = []
    today = get_today()
    now = datetime.now()
    goals = config.get("goals", {})

    for goal_id, goal_config in goals.items():
        logs = get_goal_logs(goal_id)
        name = goal_config.get("name", goal_id)
        unit = goal_config.get("unit", "")

        # Get urgency configuration
        urgency = get_urgency_config(goal_config)
        urgency_type = urgency.get("type", "none")

        # Find last log date
        last_log_date = None
        for log in reversed(logs):
            if "date" in log:
                last_log_date = log["date"]
                break

        # Process based on urgency type
        if urgency_type == "cadence":
            cadence = urgency.get("cadence")

            if cadence == "daily":
                today_logs = [l for l in logs if to_date_str(l.get("date")) == today]
                if not today_logs:
                    due_by = urgency.get("due_by", "23:59")
                    nag_from = urgency.get("nag_from", "07:00")

                    # Parse times
                    try:
                        due_time = datetime.strptime(due_by, "%H:%M").time()
                        nag_time = datetime.strptime(nag_from, "%H:%M").time()
                    except ValueError:
                        due_time = datetime.strptime("23:59", "%H:%M").time()
                        nag_time = datetime.strptime("07:00", "%H:%M").time()

                    current_time = now.time()

                    if current_time > due_time:
                        # Overdue - past due_by time
                        todos.append({
                            "goal": goal_id,
                            "name": name,
                            "message": f"{name}: overdue (due by {due_by})",
                            "priority": "overdue"
                        })
                    elif current_time >= nag_time:
                        # Due - between nag_from and due_by
                        todos.append({
                            "goal": goal_id,
                            "name": name,
                            "message": f"{name}: not done today",
                            "priority": "due"
                        })
                    # Before nag_from: don't show

            elif cadence == "weekly":
                week_start = now - timedelta(days=now.weekday())
                week_start_str = week_start.strftime("%Y-%m-%d")
                week_logs = [l for l in logs if to_date_str(l.get("date")) >= week_start_str]

                if not week_logs:
                    # Nothing logged this week
                    day_of_week = now.weekday()  # 0=Monday, 6=Sunday
                    if day_of_week >= 4:  # Thursday or later
                        todos.append({
                            "goal": goal_id,
                            "name": name,
                            "message": f"{name}: nothing logged this week",
                            "priority": "overdue"
                        })
                    else:
                        todos.append({
                            "goal": goal_id,
                            "name": name,
                            "message": f"{name}: week started, nothing logged",
                            "priority": "due"
                        })
                else:
                    # Show progress
                    total = sum(l.get("value", 0) for l in week_logs)
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: {total} {unit} this week",
                        "priority": "info"
                    })

            elif cadence == "biweekly":
                if last_log_date:
                    last_date = datetime.strptime(to_date_str(last_log_date), "%Y-%m-%d")
                    days_since = (now - last_date).days

                    if days_since >= 14:
                        todos.append({
                            "goal": goal_id,
                            "name": name,
                            "message": f"{name}: {days_since} days since last (overdue)",
                            "priority": "overdue"
                        })
                    elif days_since >= 12:
                        todos.append({
                            "goal": goal_id,
                            "name": name,
                            "message": f"{name}: {days_since} days since last",
                            "priority": "due"
                        })
                    else:
                        # Show info
                        todos.append({
                            "goal": goal_id,
                            "name": name,
                            "message": f"{name}: {days_since} days since last",
                            "priority": "info"
                        })
                else:
                    # Never done - check if goal has started
                    start_str = goal_config.get("start")
                    if start_str:
                        start_date = datetime.strptime(to_date_str(start_str), "%Y-%m-%d")
                        if now.date() >= start_date.date():
                            days_since_start = (now - start_date).days
                            if days_since_start >= 14:
                                todos.append({
                                    "goal": goal_id,
                                    "name": name,
                                    "message": f"{name}: never done (overdue)",
                                    "priority": "overdue"
                                })
                            elif days_since_start >= 0:
                                todos.append({
                                    "goal": goal_id,
                                    "name": name,
                                    "message": f"{name}: never done",
                                    "priority": "due"
                                })
                    else:
                        todos.append({
                            "goal": goal_id,
                            "name": name,
                            "message": f"{name}: never done",
                            "priority": "due"
                        })

        elif urgency_type == "target":
            target = urgency.get("target", 0)
            warn_at = urgency.get("warn_at", 0.5)
            under_is_good = urgency.get("under_is_good", False)
            period = urgency.get("period", "weekly")

            # Calculate period totals
            if period == "weekly":
                week_start = now - timedelta(days=now.weekday())
                period_start_str = week_start.strftime("%Y-%m-%d")
            else:
                period_start_str = today

            period_logs = [l for l in logs if to_date_str(l.get("date")) >= period_start_str]
            period_total = sum(l.get("value", 0) for l in period_logs)

            day_of_week = now.weekday()  # 0=Monday, 6=Sunday
            threshold = target * warn_at

            if under_is_good:
                # For spend-less: being under target is good
                if period_total > target:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: {period_total}/{target} {unit} (over budget!)",
                        "priority": "overdue"
                    })
                elif period_total > threshold:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: {period_total}/{target} {unit} (approaching limit)",
                        "priority": "due"
                    })
                else:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: {period_total}/{target} {unit}",
                        "priority": "info"
                    })
            else:
                # For fitness: hitting target is good
                if period_total >= target:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: {period_total}/{target} {unit} (target met!)",
                        "priority": "info"
                    })
                elif day_of_week >= 3 and period_total < threshold:
                    # Thursday or later and under 50% - overdue
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: {period_total}/{target} {unit} (behind pace)",
                        "priority": "overdue"
                    })
                elif period_total < target:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: {period_total}/{target} {unit}",
                        "priority": "due"
                    })

        elif urgency_type == "stale":
            stale_days = urgency.get("stale_days", 5)
            overdue_days = urgency.get("overdue_days", 7)

            if last_log_date:
                last_date = datetime.strptime(to_date_str(last_log_date), "%Y-%m-%d")
                days_since = (now - last_date).days

                if days_since >= overdue_days:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: {days_since} days since last session",
                        "priority": "overdue"
                    })
                elif days_since >= stale_days:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: {days_since} days since last session",
                        "priority": "due"
                    })
                else:
                    # Show current progress
                    current_info = get_current(goal_config, logs)
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
            else:
                # Never started
                todos.append({
                    "goal": goal_id,
                    "name": name,
                    "message": f"{name}: not started",
                    "priority": "due"
                })

        elif urgency_type == "none":
            # Flexible goals - just show progress
            progression = goal_config.get("progression")
            if progression:
                current_info = get_current(goal_config, logs)
                done = current_info.get("done", 0)
                total = current_info.get("total", 0)
                if total > 0:
                    todos.append({
                        "goal": goal_id,
                        "name": name,
                        "message": f"{name}: {done}/{total} done",
                        "priority": "info"
                    })

    # Sort by priority: overdue first, then due, then info
    priority_order = {"overdue": 0, "due": 1, "info": 2}
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
