"""Git operations for committing and pushing changes."""

import subprocess
from .storage import REPO_PATH


def commit_and_push(message: str) -> dict:
    """
    Git add, commit, and push changes.

    Returns dict with:
      - success: bool
      - message: str (result or error)
    """
    try:
        # Git add
        subprocess.run(
            ["git", "add", "_data/"],
            cwd=REPO_PATH,
            check=True,
            capture_output=True
        )

        # Git commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=REPO_PATH,
            capture_output=True,
            text=True
        )

        if "nothing to commit" in result.stdout + result.stderr:
            return {"success": True, "message": "Nothing to commit - no changes."}

        # Git push
        subprocess.run(
            ["git", "push"],
            cwd=REPO_PATH,
            check=True,
            capture_output=True
        )

        return {"success": True, "message": f"Committed and pushed: {message}"}

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if hasattr(e, 'stderr') and e.stderr else str(e)
        return {"success": False, "message": f"Git error: {error_msg}"}
