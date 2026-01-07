"""Google Tasks API integration."""

import pickle
from datetime import datetime, date
from typing import Optional

from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from .calendar_service import TOKEN_PATH, CREDENTIALS_PATH


def get_tasks_service():
    """
    Get authenticated Google Tasks service.

    Returns None if not authenticated or missing tasks scope.
    """
    if not TOKEN_PATH.exists():
        return None

    try:
        with open(TOKEN_PATH, 'rb') as f:
            creds = pickle.load(f)

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'wb') as f:
                pickle.dump(creds, f)

        # Check if we have tasks scope
        if 'https://www.googleapis.com/auth/tasks' not in (creds.scopes or []):
            return None

        return build('tasks', 'v1', credentials=creds)
    except Exception:
        return None


def get_task_lists() -> list[dict]:
    """
    Get all task lists.

    Returns list of {id, title}.
    """
    service = get_tasks_service()
    if not service:
        return []

    try:
        results = service.tasklists().list().execute()
        return [
            {"id": tl["id"], "title": tl["title"]}
            for tl in results.get("items", [])
        ]
    except Exception:
        return []


def get_default_task_list_id() -> Optional[str]:
    """Get the default task list ID (usually '@default')."""
    lists = get_task_lists()
    if lists:
        return lists[0]["id"]
    return "@default"


def create_task(
    title: str,
    due_date: date = None,
    notes: str = None,
    task_list_id: str = None,
) -> dict:
    """
    Create a new Google Task.

    Args:
        title: Task title
        due_date: Due date (date only, Tasks API doesn't support times)
        notes: Optional notes/description
        task_list_id: Task list to add to (default: primary list)

    Returns: {success, task_id, message}
    """
    service = get_tasks_service()
    if not service:
        return {
            "success": False,
            "message": "Tasks not authenticated. Run: goals-mcp auth (with Tasks API enabled)"
        }

    task_list = task_list_id or "@default"

    task_body = {"title": title}

    if due_date:
        # Tasks API expects RFC3339 date format
        if isinstance(due_date, datetime):
            due_date = due_date.date()
        task_body["due"] = f"{due_date.isoformat()}T00:00:00.000Z"

    if notes:
        task_body["notes"] = notes

    try:
        result = service.tasks().insert(
            tasklist=task_list,
            body=task_body
        ).execute()

        return {
            "success": True,
            "task_id": result["id"],
            "message": f"Created task: {title}"
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to create task: {e}"}


def complete_task(task_id: str, task_list_id: str = None) -> dict:
    """
    Mark a Google Task as complete.

    Returns: {success, message}
    """
    service = get_tasks_service()
    if not service:
        return {"success": False, "message": "Tasks not authenticated"}

    task_list = task_list_id or "@default"

    try:
        # Get current task
        task = service.tasks().get(
            tasklist=task_list,
            task=task_id
        ).execute()

        # Mark complete
        task["status"] = "completed"
        service.tasks().update(
            tasklist=task_list,
            task=task_id,
            body=task
        ).execute()

        return {"success": True, "message": "Task marked complete"}
    except Exception as e:
        return {"success": False, "message": f"Failed to complete task: {e}"}


def delete_task(task_id: str, task_list_id: str = None) -> dict:
    """
    Delete a Google Task.

    Returns: {success, message}
    """
    service = get_tasks_service()
    if not service:
        return {"success": False, "message": "Tasks not authenticated"}

    task_list = task_list_id or "@default"

    try:
        service.tasks().delete(
            tasklist=task_list,
            task=task_id
        ).execute()

        return {"success": True, "message": "Task deleted"}
    except Exception as e:
        return {"success": False, "message": f"Failed to delete task: {e}"}


def is_tasks_authenticated() -> bool:
    """Check if we have valid Google Tasks credentials."""
    return get_tasks_service() is not None
