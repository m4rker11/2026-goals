"""
Pushover client for sending notifications to phone.

Used to push Hindi practice prompts for copy-paste to Gemini Live.
"""

import json
import logging
import os
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"
MAX_MESSAGE_LENGTH = 1024


@dataclass
class PushResult:
    success: bool
    message: str
    request_id: str | None = None


def get_credentials() -> tuple[str, str]:
    """Get Pushover credentials from environment."""
    user_key = os.environ.get("PUSHOVER_USER_KEY")
    api_token = os.environ.get("PUSHOVER_API_TOKEN")

    if not user_key or not api_token:
        raise ValueError(
            "Missing Pushover credentials. Set PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN environment variables."
        )

    return user_key, api_token


def push_notification(
    title: str,
    message: str,
    priority: int = 0,
    url: str | None = None,
    url_title: str | None = None,
) -> PushResult:
    """
    Send a push notification via Pushover.

    Args:
        title: Notification title
        message: Notification body (max 1024 chars, will be truncated)
        priority: -2 (silent) to 2 (emergency), default 0 (normal)
        url: Optional URL to include
        url_title: Title for the URL

    Returns:
        PushResult with success status
    """
    try:
        user_key, api_token = get_credentials()
    except ValueError as e:
        return PushResult(success=False, message=str(e))

    # Truncate message if needed
    if len(message) > MAX_MESSAGE_LENGTH:
        message = message[: MAX_MESSAGE_LENGTH - 3] + "..."

    # Build request data
    data = {
        "token": api_token,
        "user": user_key,
        "title": title,
        "message": message,
        "priority": priority,
    }

    if url:
        data["url"] = url
    if url_title:
        data["url_title"] = url_title

    # Send request
    try:
        request_data = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(PUSHOVER_API_URL, data=request_data)

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

            if result.get("status") == 1:
                return PushResult(
                    success=True,
                    message="Notification sent",
                    request_id=result.get("request"),
                )
            else:
                errors = result.get("errors", ["Unknown error"])
                return PushResult(success=False, message=", ".join(errors))

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        logger.error(f"Pushover HTTP error: {e.code} - {error_body}")
        return PushResult(success=False, message=f"HTTP {e.code}: {error_body}")

    except urllib.error.URLError as e:
        logger.error(f"Pushover connection error: {e}")
        return PushResult(success=False, message=f"Connection error: {e}")

    except Exception as e:
        logger.error(f"Pushover error: {e}")
        return PushResult(success=False, message=str(e))


def push_hindi_practice(
    unit: int,
    vocab_section: str,
    dialogue_context: str | None = None,
) -> PushResult:
    """
    Push a Hindi practice prompt to phone.

    Args:
        unit: Current unit number
        vocab_section: Formatted vocab list for practice
        dialogue_context: Optional dialogue setup for conversation practice

    Returns:
        PushResult with success status
    """
    title = f"Hindi Practice - Unit {unit}"

    parts = [vocab_section]
    if dialogue_context:
        parts.append(f"\n---\n{dialogue_context}")

    message = "\n".join(parts)

    return push_notification(title=title, message=message)


# Import urllib.parse for urlencode
import urllib.parse
