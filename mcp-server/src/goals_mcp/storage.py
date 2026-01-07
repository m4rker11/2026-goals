"""YAML storage operations for goals and logs."""

import os
from datetime import datetime
from datetime import date as date_type
from pathlib import Path
from typing import Any

import yaml
from ruamel.yaml import YAML


def to_date_str(value) -> str:
    """Convert date value to string, handling both str and datetime.date."""
    if isinstance(value, date_type):
        return value.strftime("%Y-%m-%d")
    return str(value) if value else ""


def _discover_repo_path() -> Path:
    """
    Discover the repo path dynamically.

    Priority:
    1. REPO_PATH environment variable (for Docker/explicit config)
    2. Walk up from this file to find _data/goals.yml
    """
    if env_path := os.environ.get("REPO_PATH"):
        return Path(env_path)

    # Walk up from this file's location to find repo root
    current = Path(__file__).resolve().parent
    for _ in range(10):  # Max 10 levels up
        if (current / "_data" / "goals.yml").exists():
            return current
        if current.parent == current:
            break
        current = current.parent

    # Fallback for Docker (original default)
    return Path("/repo")


REPO_PATH = _discover_repo_path()

# Round-trip YAML parser for preserving structure
_ruamel = YAML(typ='rt')  # Explicit round-trip mode
_ruamel.preserve_quotes = True
_ruamel.default_flow_style = False
_ruamel.indent(mapping=2, sequence=4, offset=2)  # Match original file style


def get_today() -> str:
    """Get today's date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def load_yaml(path: Path) -> Any:
    """Load YAML file, return empty dict/list if only comments."""
    if not path.exists():
        return {}
    content = path.read_text()
    lines = [l.strip() for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
    if not lines:
        return []
    return yaml.safe_load(content) or []


def save_yaml(path: Path, data: Any) -> None:
    """Save data to YAML file, preserving header comments."""
    if path.exists():
        content = path.read_text()
        header_lines = []
        for line in content.split('\n'):
            if line.strip().startswith('#') or not line.strip():
                header_lines.append(line)
            else:
                break
        header = '\n'.join(header_lines) + '\n' if header_lines else ''
    else:
        header = ''

    # Don't write empty arrays - just keep header
    if isinstance(data, list) and len(data) == 0:
        path.write_text(header.rstrip() + '\n')
        return

    path.write_text(header + yaml.dump(data, default_flow_style=False, allow_unicode=True))


def get_goals_config() -> dict:
    """Load goals configuration."""
    return load_yaml(REPO_PATH / "_data" / "goals.yml")


# --- Schedule and Current Progress ---

def get_schedule() -> dict:
    """Load schedule configuration (week dates, phases, periods)."""
    return load_yaml(REPO_PATH / "_data" / "schedule.yml")


def _load_current_progress_ruamel():
    """Load current.yml with ruamel to preserve comments."""
    path = REPO_PATH / "_data" / "current.yml"
    if not path.exists():
        return {}
    with open(path) as f:
        return _ruamel.load(f) or {}


def get_current_progress() -> dict:
    """Load current progress state (focus, learning, reviewing, offsets)."""
    data = _load_current_progress_ruamel()
    # Convert to regular dict for reading (ruamel CommentedMap)
    return dict(data) if data else {}


def save_current_progress(data) -> None:
    """Save current progress state (expects ruamel CommentedMap to preserve comments)."""
    path = REPO_PATH / "_data" / "current.yml"
    with open(path, 'w') as f:
        _ruamel.dump(data, f)


def update_current_goal(goal_id: str, updates: dict) -> dict:
    """
    Update specific fields for a goal in current.yml.
    Preserves comments by using ruamel for round-trip.

    Args:
        goal_id: Goal identifier (hindi, fitness, etc.)
        updates: Dict of fields to update

    Returns:
        The updated goal section
    """
    # Load with ruamel to preserve comments
    current = _load_current_progress_ruamel()

    if goal_id not in current:
        current[goal_id] = {}

    goal_section = current[goal_id]

    # Save and clear end comments before inserting new keys
    # (ruamel attaches trailing blank lines/comments to mapping end)
    end_comment = None
    if hasattr(goal_section, 'ca') and goal_section.ca.comment:
        end_comment = goal_section.ca.comment
        goal_section.ca.comment = None

    for key, value in updates.items():
        if key in goal_section:
            # Key exists - update in place (preserves position)
            goal_section[key] = value
        else:
            # New key - insert at end of existing keys
            existing_keys = list(goal_section.keys())
            insert_pos = len(existing_keys)
            goal_section.insert(insert_pos, key, value)

    # Restore end comments after the new keys
    if end_comment:
        goal_section.ca.comment = end_comment

    save_current_progress(current)
    return dict(current[goal_id])


def get_current_week(schedule: dict = None) -> dict:
    """
    Calculate current week from schedule.yml.

    Returns dict with:
        number: Week number (1-8)
        start: Start date string
        end: End date string
    """
    if schedule is None:
        schedule = get_schedule()

    today = get_today()

    for week in schedule.get("weeks", []):
        if week["start"] <= today <= week["end"]:
            return {
                "number": week["number"],
                "start": week["start"],
                "end": week["end"]
            }

    # Fallback: return week 1 or last week based on date
    weeks = schedule.get("weeks", [])
    if weeks:
        if today < weeks[0]["start"]:
            return weeks[0]
        if today > weeks[-1]["end"]:
            return weeks[-1]

    return {"number": 1, "start": "?", "end": "?"}


def get_effective_week(goal_id: str, schedule: dict = None, current: dict = None) -> dict:
    """
    Get effective current week for a goal, accounting for offsets/overrides.

    Checks current.yml for:
        - override_week: Use this week number directly
        - offset_weeks: Shift calculated week by this amount
        - paused_until: If today < this date, return paused status

    Returns dict with:
        number: Effective week number
        start: Week start date
        end: Week end date
        adjusted: True if offset/override applied
        paused: True if goal is paused
        reason: Adjustment reason if set
    """
    if schedule is None:
        schedule = get_schedule()
    if current is None:
        current = get_current_progress()

    base_week = get_current_week(schedule)
    goal_current = current.get(goal_id, {})

    # Check for pause
    paused_until = goal_current.get("paused_until")
    if paused_until and get_today() < paused_until:
        return {
            "number": base_week["number"],
            "start": base_week["start"],
            "end": base_week["end"],
            "adjusted": True,
            "paused": True,
            "paused_until": paused_until,
            "reason": goal_current.get("adjustment_reason", "Paused")
        }

    # Check for override
    override = goal_current.get("override_week")
    if override:
        # Find the override week in schedule
        weeks = schedule.get("weeks", [])
        for week in weeks:
            if week["number"] == override:
                return {
                    "number": override,
                    "start": week["start"],
                    "end": week["end"],
                    "adjusted": True,
                    "paused": False,
                    "reason": goal_current.get("adjustment_reason", f"Overridden to week {override}")
                }
        # Override week not found, use the number anyway
        return {
            "number": override,
            "start": "?",
            "end": "?",
            "adjusted": True,
            "paused": False,
            "reason": goal_current.get("adjustment_reason")
        }

    # Check for offset
    offset = goal_current.get("offset_weeks", 0)
    if offset:
        effective_num = max(1, base_week["number"] - offset)
        weeks = schedule.get("weeks", [])
        for week in weeks:
            if week["number"] == effective_num:
                return {
                    "number": effective_num,
                    "start": week["start"],
                    "end": week["end"],
                    "adjusted": True,
                    "paused": False,
                    "reason": goal_current.get("adjustment_reason", f"Offset by {offset} weeks")
                }

    # No adjustments
    return {
        "number": base_week["number"],
        "start": base_week["start"],
        "end": base_week["end"],
        "adjusted": False,
        "paused": False,
        "reason": None
    }


def get_goal_logs(goal_id: str) -> list:
    """Load logs for a specific goal."""
    return load_yaml(REPO_PATH / "_data" / "logs" / f"{goal_id}.yml")


def save_goal_logs(goal_id: str, logs: list) -> None:
    """Save logs for a specific goal."""
    save_yaml(REPO_PATH / "_data" / "logs" / f"{goal_id}.yml", logs)


def discover_content(content_path: str) -> list[str]:
    """Discover subgoals/items from directory structure."""
    full_path = REPO_PATH / content_path
    if not full_path.exists():
        return []

    items = []
    for item in full_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            items.append(item.name)
        elif item.is_file() and item.suffix == '.md' and item.name != 'index.md':
            items.append(item.stem)
    return sorted(items)


# --- Todo storage (uses ruamel.yaml for round-trip preservation) ---

def get_todo_path(goal_id: str, unit: str) -> Path:
    """Get path to todo.yml for a goal unit."""
    return REPO_PATH / "_data" / "todos" / goal_id / f"{unit}.yml"


def get_unit_todo(goal_id: str, unit: str) -> dict:
    """
    Load todo.yml for a specific unit (week/chapter).

    Returns dict with structure:
    {
        "unit": "week-1",
        "tasks": [
            {"id": "task1", "name": "Do thing", "done": False, "notes": None},
            ...
        ]
    }
    """
    path = get_todo_path(goal_id, unit)
    if not path.exists():
        return {"unit": unit, "tasks": []}

    with open(path) as f:
        data = _ruamel.load(f)

    if isinstance(data, dict):
        return dict(data)  # Convert from ruamel CommentedMap
    return {"unit": unit, "tasks": []}


def save_unit_todo(goal_id: str, unit: str, todo_data: dict) -> None:
    """Save todo.yml for a specific unit, preserving structure."""
    path = get_todo_path(goal_id, unit)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        _ruamel.dump(todo_data, f)


def update_todo_task(goal_id: str, unit: str, task_id: str,
                     done: bool = None, notes: str = None,
                     scheduled_for: str = None, event_id: str = None,
                     clear_schedule: bool = False) -> dict | None:
    """
    Update a specific task in a unit's todo.yml, preserving file structure.

    Args:
        scheduled_for: ISO datetime string for when task is scheduled
        event_id: Google Calendar event ID
        clear_schedule: If True, removes scheduled_for and event_id fields

    Returns the updated task or None if not found.
    """
    path = get_todo_path(goal_id, unit)
    if not path.exists():
        return None

    # Load with ruamel for round-trip preservation
    with open(path) as f:
        data = _ruamel.load(f)

    if not isinstance(data, dict) or "tasks" not in data:
        return None

    # Find and update the task
    updated_task = None
    for task in data["tasks"]:
        if task.get("id") == task_id:
            # Save original values before clearing (for return value)
            original_event_id = task.get("event_id")

            if done is not None:
                task["done"] = done
            if notes is not None:
                task["notes"] = notes
            if scheduled_for is not None:
                task["scheduled_for"] = scheduled_for
            if event_id is not None:
                task["event_id"] = event_id
            if clear_schedule:
                task.pop("scheduled_for", None)
                task.pop("event_id", None)

            # Include original event_id in return so caller can mark it complete
            updated_task = dict(task)
            if clear_schedule and original_event_id:
                updated_task["_cleared_event_id"] = original_event_id
            break

    if updated_task:
        # Save back preserving structure
        with open(path, 'w') as f:
            _ruamel.dump(data, f)

    return updated_task


def get_all_pending_tasks(goal_id: str = None) -> list[dict]:
    """
    Get all pending (not done) tasks across all units.

    Returns list of dicts with goal_id, unit, and task info.
    """
    todos_dir = REPO_PATH / "_data" / "todos"
    if not todos_dir.exists():
        return []

    pending = []
    goal_dirs = [todos_dir / goal_id] if goal_id else todos_dir.iterdir()

    for goal_dir in goal_dirs:
        if not goal_dir.is_dir():
            continue
        gid = goal_dir.name

        for todo_file in goal_dir.glob("*.yml"):
            unit = todo_file.stem
            todo = get_unit_todo(gid, unit)

            for task in todo.get("tasks", []):
                if not task.get("done", False):
                    pending.append({
                        "goal_id": gid,
                        "unit": unit,
                        "task": dict(task)
                    })

    return pending


def get_all_scheduled_tasks() -> list[dict]:
    """
    Get all tasks with scheduled_for field set.

    Returns list of dicts with goal_id, unit, and task info.
    """
    todos_dir = REPO_PATH / "_data" / "todos"
    if not todos_dir.exists():
        return []

    scheduled = []

    for goal_dir in todos_dir.iterdir():
        if not goal_dir.is_dir():
            continue
        gid = goal_dir.name

        for todo_file in goal_dir.glob("*.yml"):
            unit = todo_file.stem
            todo = get_unit_todo(gid, unit)

            for task in todo.get("tasks", []):
                if task.get("scheduled_for") and not task.get("done", False):
                    scheduled.append({
                        "goal_id": gid,
                        "unit": unit,
                        "task": dict(task)
                    })

    return scheduled


def find_task_by_event_id(event_id: str) -> dict | None:
    """
    Find a task by its calendar event_id.

    Returns dict with goal_id, unit, and task info, or None.
    """
    todos_dir = REPO_PATH / "_data" / "todos"
    if not todos_dir.exists():
        return None

    for goal_dir in todos_dir.iterdir():
        if not goal_dir.is_dir():
            continue
        gid = goal_dir.name

        for todo_file in goal_dir.glob("*.yml"):
            unit = todo_file.stem
            todo = get_unit_todo(gid, unit)

            for task in todo.get("tasks", []):
                if task.get("event_id") == event_id:
                    return {
                        "goal_id": gid,
                        "unit": unit,
                        "task": dict(task)
                    }

    return None


# --- Daily tracking ---

def get_daily_path() -> Path:
    """Get path to daily.yml."""
    return REPO_PATH / "_data" / "daily.yml"


def get_daily_entries() -> list:
    """Load all daily entries."""
    return load_yaml(get_daily_path())


def save_daily_entries(entries: list) -> None:
    """Save daily entries."""
    save_yaml(get_daily_path(), entries)


def get_daily_entry(date: str = None) -> dict | None:
    """Get a specific day's entry, or today's if no date specified."""
    target_date = date or get_today()
    entries = get_daily_entries()

    for entry in entries:
        if to_date_str(entry.get("date")) == target_date:
            return entry
    return None


# --- Memory storage ---

def get_memory_path() -> Path:
    """Get path to memory.yml."""
    return REPO_PATH / "_data" / "memory.yml"


def get_memory_entries() -> list:
    """Load all memory entries."""
    data = load_yaml(get_memory_path())
    # Ensure we always return a list (load_yaml returns {} for missing files)
    return data if isinstance(data, list) else []


def save_memory_entries(entries: list) -> None:
    """Save memory entries (used by condense)."""
    save_yaml(get_memory_path(), entries)


def add_memory_entry(text: str, date: str = None) -> dict:
    """
    Add a new memory entry.

    Args:
        text: The observation/quote/insight to remember
        date: Date in YYYY-MM-DD format (defaults to today)

    Returns:
        The created entry
    """
    entries = get_memory_entries()
    entry = {
        "date": date or get_today(),
        "text": text
    }
    entries.append(entry)
    save_memory_entries(entries)
    return entry


def get_recent_memory(limit: int = 10) -> list:
    """Get the most recent memory entries."""
    entries = get_memory_entries()
    return entries[-limit:] if entries else []


def update_daily_entry(date: str = None, **fields) -> dict:
    """
    Update or create a daily entry.

    Args:
        date: Date in YYYY-MM-DD format (defaults to today)
        **fields: Fields to update (calendar, fitness, hindi, mood, notes)

    Returns:
        The updated entry
    """
    target_date = date or get_today()
    entries = get_daily_entries()

    # Find existing entry
    found_idx = None
    for i, entry in enumerate(entries):
        if to_date_str(entry.get("date")) == target_date:
            found_idx = i
            break

    if found_idx is not None:
        # Update existing
        for key, value in fields.items():
            if value is not None:
                entries[found_idx][key] = value
        result = entries[found_idx]
    else:
        # Create new entry with defaults
        new_entry = {
            "date": target_date,
            "calendar": fields.get("calendar", False),
            "fitness": fields.get("fitness", 0),
            "hindi": fields.get("hindi", 0),
        }
        # Add optional fields if provided
        if "mood" in fields:
            new_entry["mood"] = fields["mood"]
        if "notes" in fields:
            new_entry["notes"] = fields["notes"]

        entries.append(new_entry)
        result = new_entry

    save_daily_entries(entries)
    return result
