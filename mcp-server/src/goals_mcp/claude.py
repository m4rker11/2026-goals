"""Claude Code integration for autonomous content editing."""

import subprocess
import shlex
from pathlib import Path

from .storage import REPO_PATH
from .git import commit_and_push

# Paths that can be edited by Claude Code
ALLOWED_PATHS = [
    "Hindi/",
    "calendaring/",
    "fitness/",
    "sell/",
    "Goals.md",
    "index.md",
    "updates/",
]

# Paths that must NEVER be edited
BLOCKED_PATHS = [
    "_data/",
    ".git/",
    ".github/",
    ".claude/",
    "mcp-server/",
    "_config.yml",
]


def is_path_allowed(file_path: str) -> tuple[bool, str]:
    """
    Check if a file path is allowed to be edited.

    Returns (allowed: bool, reason: str)
    """
    # Normalize path
    normalized = file_path.lstrip("/").lstrip("repo/")

    # Check blocked paths first
    for blocked in BLOCKED_PATHS:
        if normalized.startswith(blocked):
            return False, f"Path '{normalized}' is blocked. Use MCP tools for _data/ edits."

    # Check if in allowed paths
    for allowed in ALLOWED_PATHS:
        if normalized.startswith(allowed) or normalized == allowed.rstrip("/"):
            return True, "OK"

    return False, f"Path '{normalized}' not in allowed directories: {ALLOWED_PATHS}"


def run_claude_edit(instruction: str, file_path: str | None = None) -> dict:
    """
    Run Claude Code to edit content files.

    Args:
        instruction: What to edit/change
        file_path: Optional specific file to edit (relative to repo)

    Returns:
        dict with success, message, files_changed
    """
    # Validate file path if provided
    if file_path:
        allowed, reason = is_path_allowed(file_path)
        if not allowed:
            return {"success": False, "message": reason, "files_changed": []}

    # Build the prompt for Claude Code
    if file_path:
        full_path = REPO_PATH / file_path
        if not full_path.exists():
            # Check if we should create it
            if file_path.startswith("sell/") and file_path.endswith(".md"):
                prompt = f"""Create a new file at {full_path}.

{instruction}

The file should follow the same format as other files in the sell/ directory:
---
name: [Item Name]
---

[Additional details]"""
            else:
                return {
                    "success": False,
                    "message": f"File not found: {file_path}",
                    "files_changed": []
                }
        else:
            prompt = f"""Edit the file at {full_path}.

{instruction}

Rules:
- Make only the changes requested
- Preserve existing formatting and structure
- If updating a markdown table, keep alignment
- If marking checkboxes, use [x] format
- Keep the file valid markdown"""
    else:
        # No specific file - Claude Code will find the right one
        prompt = f"""In the repository at {REPO_PATH}, make the following edit:

{instruction}

Rules:
- Only edit files in: {', '.join(ALLOWED_PATHS)}
- NEVER edit files in: {', '.join(BLOCKED_PATHS)}
- Make minimal changes to accomplish the task
- Preserve existing formatting"""

    # Run Claude Code
    try:
        cmd = [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "--allowedTools", "Read,Edit,Write,Glob",
            "--max-turns", "5",
            prompt
        ]

        result = subprocess.run(
            cmd,
            cwd=REPO_PATH,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        # Check what files were changed
        git_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_PATH,
            capture_output=True,
            text=True
        )

        changed_files = []
        for line in git_status.stdout.strip().split("\n"):
            if line.strip():
                # Format: "M  path/to/file" or "?? path/to/file"
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    changed_files.append(parts[1])

        if result.returncode != 0:
            return {
                "success": False,
                "message": f"Claude Code error: {result.stderr}",
                "files_changed": changed_files
            }

        return {
            "success": True,
            "message": result.stdout[:500] if result.stdout else "Edit completed",
            "files_changed": changed_files
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Claude Code timed out after 2 minutes",
            "files_changed": []
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": "Claude Code CLI not found. Is it installed?",
            "files_changed": []
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error running Claude Code: {str(e)}",
            "files_changed": []
        }


def edit_and_commit(instruction: str, file_path: str | None = None, auto_commit: bool = True) -> dict:
    """
    Edit content using Claude Code and optionally commit.

    Args:
        instruction: What to edit
        file_path: Optional specific file
        auto_commit: Whether to commit after editing

    Returns:
        dict with success, message, files_changed, committed
    """
    # Run the edit
    result = run_claude_edit(instruction, file_path)

    if not result["success"]:
        return {**result, "committed": False}

    if not result["files_changed"]:
        return {
            "success": True,
            "message": "No changes were made",
            "files_changed": [],
            "committed": False
        }

    # Validate all changed files are in allowed paths
    for changed in result["files_changed"]:
        allowed, reason = is_path_allowed(changed)
        if not allowed:
            # Revert the change
            subprocess.run(
                ["git", "checkout", "--", changed],
                cwd=REPO_PATH,
                capture_output=True
            )
            return {
                "success": False,
                "message": f"Blocked: Claude tried to edit {changed}. Reverted.",
                "files_changed": [],
                "committed": False
            }

    if not auto_commit:
        return {**result, "committed": False}

    # Generate commit message
    files_summary = ", ".join(result["files_changed"][:3])
    if len(result["files_changed"]) > 3:
        files_summary += f" (+{len(result['files_changed']) - 3} more)"

    commit_msg = f"Edit content: {files_summary}"
    if len(commit_msg) > 72:
        commit_msg = commit_msg[:69] + "..."

    # Add only the changed content files (not _data/)
    for f in result["files_changed"]:
        subprocess.run(
            ["git", "add", f],
            cwd=REPO_PATH,
            capture_output=True
        )

    commit_result = commit_and_push(commit_msg)

    return {
        "success": True,
        "message": result["message"],
        "files_changed": result["files_changed"],
        "committed": commit_result["success"],
        "commit_message": commit_msg if commit_result["success"] else commit_result["message"]
    }
