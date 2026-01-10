"""
GitHub Gist client using gh CLI.

Creates private gists with Hindi practice content, returns URL for Pushover.
"""

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GistResult:
    success: bool
    url: str | None
    message: str


def create_gist(
    content: str,
    description: str = "Hindi Practice Prompt",
    public: bool = False,
) -> GistResult:
    """
    Create a GitHub Gist using gh CLI.

    Args:
        content: The markdown content for the gist
        description: Gist description
        public: Whether the gist is public (default: private)

    Returns:
        GistResult with URL if successful
    """
    try:
        # Write content to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            prefix="hindi-practice-",
            delete=False,
        ) as f:
            f.write(content)
            temp_path = f.name

        # Build gh command
        cmd = ["gh", "gist", "create", temp_path]
        if description:
            cmd.extend(["--desc", description])
        if public:
            cmd.append("--public")

        # Run gh gist create
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Clean up temp file
        Path(temp_path).unlink(missing_ok=True)

        if result.returncode == 0:
            url = result.stdout.strip()
            return GistResult(
                success=True,
                url=url,
                message="Gist created successfully",
            )
        else:
            error = result.stderr.strip() or "Unknown error"
            logger.error(f"gh gist create failed: {error}")
            return GistResult(success=False, url=None, message=error)

    except subprocess.TimeoutExpired:
        return GistResult(success=False, url=None, message="Timed out creating gist")

    except FileNotFoundError:
        return GistResult(success=False, url=None, message="gh CLI not found - install with 'brew install gh'")

    except Exception as e:
        logger.error(f"Gist creation error: {e}")
        return GistResult(success=False, url=None, message=str(e))
