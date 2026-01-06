"""Google Calendar integration using gcsa."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from gcsa.attendee import Attendee


# Token storage location
TOKEN_DIR = Path.home() / ".goals-mcp"
TOKEN_PATH = TOKEN_DIR / "google-token.pickle"
CREDENTIALS_PATH = TOKEN_DIR / "credentials.json"


def get_calendar() -> Optional[GoogleCalendar]:
    """
    Get authenticated Google Calendar instance.

    Returns None if not authenticated.
    """
    if not CREDENTIALS_PATH.exists():
        return None

    try:
        # gcsa handles token refresh automatically
        gc = GoogleCalendar(
            credentials_path=str(CREDENTIALS_PATH),
            token_path=str(TOKEN_PATH),
        )
        return gc
    except Exception:
        return None


def is_authenticated() -> bool:
    """Check if we have valid Google Calendar credentials."""
    return TOKEN_PATH.exists() and CREDENTIALS_PATH.exists()


def get_upcoming_events(hours_ahead: int = 8) -> list[dict]:
    """
    Get upcoming calendar events.

    Returns list of events with: time, title, is_goal, goal_id, duration_min
    """
    gc = get_calendar()
    if not gc:
        return []

    now = datetime.now()
    end = now + timedelta(hours=hours_ahead)

    events = []
    try:
        for event in gc.get_events(time_min=now, time_max=end, order_by='startTime', single_events=True):
            is_goal = event.summary and event.summary.startswith("[Goal]")
            goal_id = None
            title = event.summary or "Untitled"

            if is_goal:
                # Parse goal ID from title: "[Goal] Hindi - Chapter 5"
                parts = title.replace("[Goal]", "").strip().split(" - ", 1)
                if parts:
                    goal_id = parts[0].lower().replace(" ", "-")
                    title = parts[1] if len(parts) > 1 else parts[0]

            # Calculate duration
            duration_min = 30
            if event.start and event.end:
                if hasattr(event.start, 'hour'):
                    # datetime objects
                    duration = event.end - event.start
                    duration_min = int(duration.total_seconds() / 60)

            events.append({
                "time": event.start.strftime("%I:%M%p").lower().lstrip("0") if hasattr(event.start, 'strftime') else str(event.start),
                "title": title,
                "is_goal": is_goal,
                "goal_id": goal_id,
                "duration_min": duration_min,
                "event_id": event.event_id,
            })
    except Exception as e:
        # Calendar errors shouldn't break the server
        print(f"Calendar error: {e}")

    return events


def schedule_goal(
    goal_id: str,
    goal_name: str,
    time: datetime,
    duration_min: int = 30,
    notes: str = "",
    invite_emails: list[str] = None,
    color_id: int = None,
) -> dict:
    """
    Schedule a goal on the calendar.

    Returns: {success, event_id, message}

    Color IDs: 1=Lavender, 2=Sage, 3=Grape, 4=Flamingo, 5=Banana,
               6=Tangerine, 7=Peacock, 8=Graphite, 9=Blueberry,
               10=Basil, 11=Tomato
    """
    gc = get_calendar()
    if not gc:
        return {"success": False, "message": "Not authenticated. Run: goals-mcp auth"}

    # Check for conflicts across all calendars
    conflicts = check_conflicts(time, duration_min)
    if conflicts:
        conflict_list = ", ".join([f"{c['title']} ({c['calendar']})" for c in conflicts])
        return {"success": False, "message": f"Conflicts with: {conflict_list}"}

    title = f"[Goal] {goal_name}"
    if notes:
        title += f" - {notes}"

    end_time = time + timedelta(minutes=duration_min)

    attendees = []
    if invite_emails:
        attendees = [Attendee(email=e) for e in invite_emails]

    try:
        event = Event(
            summary=title,
            start=time,
            end=end_time,
            attendees=attendees if attendees else None,
            description=f"Goal: {goal_id}\n{notes}" if notes else f"Goal: {goal_id}",
            color_id=str(color_id) if color_id else None,
        )

        created = gc.add_event(event)
        return {
            "success": True,
            "event_id": created.event_id,
            "message": f"Scheduled {goal_name} at {time.strftime('%I:%M%p').lower().lstrip('0')}"
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to schedule: {e}"}


def get_event_info(event_id: str) -> dict | None:
    """
    Get info about a calendar event.

    Returns dict with: exists, start, end, title
    Or None if not authenticated.
    """
    gc = get_calendar()
    if not gc:
        return None

    try:
        event = gc.get_event(event_id)
        if not event:
            return {"exists": False}

        return {
            "exists": True,
            "start": event.start if hasattr(event.start, 'isoformat') else None,
            "end": event.end if hasattr(event.end, 'isoformat') else None,
            "title": event.summary,
        }
    except Exception:
        return {"exists": False}


def reschedule_goal(event_id: str, new_time: datetime) -> dict:
    """
    Reschedule an existing goal event.

    Returns: {success, message}
    """
    gc = get_calendar()
    if not gc:
        return {"success": False, "message": "Not authenticated. Run: goals-mcp auth"}

    try:
        event = gc.get_event(event_id)
        if not event:
            return {"success": False, "message": f"Event not found: {event_id}"}

        # Calculate duration from original event
        duration = event.end - event.start
        duration_min = int(duration.total_seconds() / 60)

        # Check for conflicts at new time
        conflicts = check_conflicts(new_time, duration_min)
        if conflicts:
            conflict_list = ", ".join([f"{c['title']} ({c['calendar']})" for c in conflicts])
            return {"success": False, "message": f"Conflicts with: {conflict_list}"}

        event.start = new_time
        event.end = new_time + duration

        gc.update_event(event)
        return {
            "success": True,
            "message": f"Rescheduled to {new_time.strftime('%I:%M%p').lower().lstrip('0')}"
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to reschedule: {e}"}


def unschedule_goal(event_id: str) -> dict:
    """
    Remove a scheduled goal event.

    Returns: {success, message}
    """
    gc = get_calendar()
    if not gc:
        return {"success": False, "message": "Not authenticated. Run: goals-mcp auth"}

    try:
        event = gc.get_event(event_id)
        if not event:
            return {"success": False, "message": f"Event not found: {event_id}"}

        gc.delete_event(event)
        return {"success": True, "message": "Event removed"}
    except Exception as e:
        return {"success": False, "message": f"Failed to remove: {e}"}


def _check_calendar_conflicts(cal_id: str, cal_name: str, time: datetime, end_time: datetime) -> list[dict]:
    """Check a single calendar for conflicts (sync helper)."""
    conflicts = []
    try:
        cal_gc = GoogleCalendar(
            default_calendar=cal_id,
            credentials_path=str(CREDENTIALS_PATH),
            token_path=str(TOKEN_PATH),
        )
        for event in cal_gc.get_events(time_min=time, time_max=end_time, single_events=True):
            if not hasattr(event.start, 'hour'):
                continue
            start_str = event.start.strftime("%I:%M%p").lower().lstrip("0")
            end_str = event.end.strftime("%I:%M%p").lower().lstrip("0") if hasattr(event.end, 'hour') else ""
            conflicts.append({
                "title": event.summary or "Untitled",
                "time": f"{start_str}-{end_str}" if end_str else start_str,
                "calendar": cal_name,
            })
    except Exception:
        pass
    return conflicts


async def check_conflicts_async(time: datetime, duration_min: int = 30) -> list[dict]:
    """
    Check for calendar conflicts at the given time across ALL calendars concurrently.

    Returns list of conflicting events.
    """
    gc = get_calendar()
    if not gc:
        return []

    end_time = time + timedelta(minutes=duration_min)

    try:
        calendars = list(gc.get_calendar_list())
    except Exception:
        return []

    # Run all calendar checks concurrently
    tasks = [
        asyncio.to_thread(_check_calendar_conflicts, cal.calendar_id, cal.summary, time, end_time)
        for cal in calendars
    ]

    results = await asyncio.gather(*tasks)

    # Flatten results
    conflicts = []
    for result in results:
        conflicts.extend(result)

    return conflicts


def check_conflicts(time: datetime, duration_min: int = 30) -> list[dict]:
    """
    Check for calendar conflicts (sync wrapper).
    """
    try:
        asyncio.get_running_loop()
        # Already in async context - can't use asyncio.run
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, check_conflicts_async(time, duration_min))
            return future.result()
    except RuntimeError:
        # No running loop - safe to use asyncio.run
        return asyncio.run(check_conflicts_async(time, duration_min))


def find_goal_event_today(goal_id: str) -> Optional[str]:
    """
    Find today's scheduled event for a goal.

    Returns event_id if found, None otherwise.
    """
    gc = get_calendar()
    if not gc:
        return None

    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

    try:
        for event in gc.get_events(time_min=start_of_day, time_max=end_of_day):
            if event.summary and event.summary.startswith("[Goal]"):
                # Check if this event is for the target goal
                if event.description and f"Goal: {goal_id}" in event.description:
                    return event.event_id
    except Exception:
        pass

    return None


def mark_goal_complete(event_id: str) -> dict:
    """
    Mark a goal event as complete by prefixing with checkmark.

    Returns: {success, message}
    """
    gc = get_calendar()
    if not gc:
        return {"success": False, "message": "Not authenticated"}

    try:
        event = gc.get_event(event_id)
        if not event:
            return {"success": False, "message": f"Event not found: {event_id}"}

        if not event.summary.startswith("✓"):
            event.summary = "✓ " + event.summary
            gc.update_event(event)

        return {"success": True, "message": "Marked complete"}
    except Exception as e:
        return {"success": False, "message": f"Failed: {e}"}


def get_missed_scheduled(hours_back: int = 24) -> list[dict]:
    """
    Find goal events that passed without being marked complete.

    Returns list of missed events with: time, title, goal_id
    """
    gc = get_calendar()
    if not gc:
        return []

    now = datetime.now()
    start = now - timedelta(hours=hours_back)

    missed = []
    try:
        for event in gc.get_events(time_min=start, time_max=now, order_by='startTime', single_events=True):
            # Only check goal events that aren't marked complete
            if event.summary and event.summary.startswith("[Goal]") and not event.summary.startswith("✓"):
                goal_id = None
                if event.description:
                    for line in event.description.split("\n"):
                        if line.startswith("Goal: "):
                            goal_id = line.replace("Goal: ", "").strip()
                            break

                missed.append({
                    "time": event.start.strftime("%I:%M%p").lower().lstrip("0") if hasattr(event.start, 'strftime') else str(event.start),
                    "title": event.summary.replace("[Goal] ", ""),
                    "goal_id": goal_id,
                    "date": event.start.strftime("%Y-%m-%d") if hasattr(event.start, 'strftime') else str(event.start),
                })
    except Exception:
        pass

    return missed


def parse_time(time_str: str) -> Optional[datetime]:
    """
    Parse natural time strings like "today 4pm", "tomorrow 9am", ISO datetime.

    Returns datetime or None if parsing fails.
    """
    now = datetime.now()
    time_str = time_str.lower().strip()

    # Try ISO format first
    try:
        return datetime.fromisoformat(time_str)
    except ValueError:
        pass

    # Parse "today/tomorrow Xpm/am"
    day_offset = 0
    if time_str.startswith("today"):
        time_str = time_str.replace("today", "").strip()
    elif time_str.startswith("tomorrow"):
        day_offset = 1
        time_str = time_str.replace("tomorrow", "").strip()

    # Parse time like "4pm", "9am", "14:00"
    time_str = time_str.strip()

    hour = None
    minute = 0

    is_pm = "pm" in time_str
    is_am = "am" in time_str

    if ":" in time_str:
        # 14:00 format
        parts = time_str.replace("am", "").replace("pm", "").split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        if is_pm and hour < 12:
            hour += 12
        elif is_am and hour == 12:
            hour = 0
    elif is_pm or is_am:
        # 4pm format
        time_str = time_str.replace("pm", "").replace("am", "").strip()
        hour = int(time_str)
        if is_pm and hour < 12:
            hour += 12
        elif is_am and hour == 12:
            hour = 0
    else:
        # Just a number - assume PM if reasonable
        try:
            hour = int(time_str)
            if hour < 12:
                hour += 12  # Assume PM for work hours
        except ValueError:
            return None

    if hour is None:
        return None

    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    target += timedelta(days=day_offset)

    return target
