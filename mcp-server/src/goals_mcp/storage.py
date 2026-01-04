"""YAML storage operations for goals and logs."""

import os
from pathlib import Path
from typing import Any

import yaml

REPO_PATH = Path(os.environ.get("REPO_PATH", "/repo"))


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

    path.write_text(header + yaml.dump(data, default_flow_style=False, allow_unicode=True))


def get_goals_config() -> dict:
    """Load goals configuration."""
    return load_yaml(REPO_PATH / "_data" / "goals.yml")


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


# --- Todo storage ---

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

    data = load_yaml(path)
    if isinstance(data, dict):
        return data
    return {"unit": unit, "tasks": []}


def save_unit_todo(goal_id: str, unit: str, todo_data: dict) -> None:
    """Save todo.yml for a specific unit."""
    path = get_todo_path(goal_id, unit)
    path.parent.mkdir(parents=True, exist_ok=True)
    save_yaml(path, todo_data)


def update_todo_task(goal_id: str, unit: str, task_id: str,
                     done: bool = None, notes: str = None) -> dict:
    """
    Update a specific task in a unit's todo.yml.

    Returns the updated task or None if not found.
    """
    todo = get_unit_todo(goal_id, unit)

    for task in todo.get("tasks", []):
        if task.get("id") == task_id:
            if done is not None:
                task["done"] = done
            if notes is not None:
                task["notes"] = notes
            save_unit_todo(goal_id, unit, todo)
            return task

    return None


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
                        "task": task
                    })

    return pending
