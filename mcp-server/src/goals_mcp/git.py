"""Git operations for committing and pushing changes."""

import subprocess
from datetime import datetime
from .storage import REPO_PATH


def get_today_str() -> str:
    """Get today's date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def get_last_commit_info() -> dict | None:
    """
    Get info about the last commit.

    Returns dict with:
      - date: YYYY-MM-DD
      - message: commit message
    Or None if no commits or error.
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cd|%s", "--date=short"],
            cwd=REPO_PATH,
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout.strip()
        if not output:
            return None
        date, message = output.split("|", 1)
        return {"date": date, "message": message}
    except (subprocess.CalledProcessError, ValueError):
        return None


def is_todays_status_commit(commit_info: dict | None) -> bool:
    """Check if commit is today's status update commit."""
    if not commit_info:
        return False
    today = get_today_str()
    expected_message = f"status updates-{today}"
    return commit_info["date"] == today and commit_info["message"] == expected_message


def commit_and_push() -> dict:
    """
    Git add, commit, and push changes.

    Uses daily commit strategy:
    - First commit of the day: "status updates-YYYY-MM-DD"
    - Subsequent commits: amend the daily commit + force push

    Returns dict with:
      - success: bool
      - message: str (result or error)
    """
    try:
        today = get_today_str()
        daily_message = f"status updates-{today}"

        # Git add
        subprocess.run(
            ["git", "add", "_data/"],
            cwd=REPO_PATH,
            check=True,
            capture_output=True
        )

        # Check if there are staged changes
        status_result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=REPO_PATH,
            capture_output=True
        )

        if status_result.returncode == 0:
            return {"success": True, "message": "Nothing to commit - no changes."}

        # Check if we should amend today's commit
        last_commit = get_last_commit_info()
        should_amend = is_todays_status_commit(last_commit)

        if should_amend:
            # Amend existing daily commit
            subprocess.run(
                ["git", "commit", "--amend", "-m", daily_message, "--no-edit"],
                cwd=REPO_PATH,
                check=True,
                capture_output=True
            )

            # Force push (safe for personal repo)
            subprocess.run(
                ["git", "push", "--force-with-lease"],
                cwd=REPO_PATH,
                check=True,
                capture_output=True
            )

            return {"success": True, "message": f"Amended and pushed: {daily_message}"}
        else:
            # Create new daily commit
            subprocess.run(
                ["git", "commit", "-m", daily_message],
                cwd=REPO_PATH,
                check=True,
                capture_output=True
            )

            # Normal push
            subprocess.run(
                ["git", "push"],
                cwd=REPO_PATH,
                check=True,
                capture_output=True
            )

            return {"success": True, "message": f"Committed and pushed: {daily_message}"}

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if hasattr(e, 'stderr') and e.stderr else str(e)
        return {"success": False, "message": f"Git error: {error_msg}"}
