"""Goals 2026 MCP Server - Main entry point."""

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, Prompt, PromptMessage, TextContent

from .storage import get_goals_config, get_today
from .goals import compute_todos
from .tools import get_tool_definitions, handle_tool
from .git import commit_and_push
from . import wger_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Create MCP server
app = Server("goals-2026")


def get_urgent_summary() -> str:
    """Get a summary of urgent goals for injection."""
    config = get_goals_config()
    todos = compute_todos(config)

    overdue = [t for t in todos if t.get("priority") == "overdue"]
    due = [t for t in todos if t.get("priority") == "due"]

    if not overdue and not due:
        return "All goals on track."

    lines = []
    if overdue:
        lines.append("OVERDUE: " + ", ".join(t["name"] for t in overdue))
    if due:
        lines.append("Due: " + ", ".join(t["name"] for t in due))

    return " | ".join(lines)


@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts with dynamic urgent summary."""
    summary = get_urgent_summary()
    return [
        Prompt(
            name="goals-status",
            description=f"Current goals status. {summary}",
        )
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict | None = None) -> list[PromptMessage]:
    """Get prompt content."""
    if name == "goals-status":
        config = get_goals_config()
        todos = compute_todos(config)

        lines = [f"Goals Status ({get_today()})", ""]

        overdue = [t for t in todos if t.get("priority") == "overdue"]
        due = [t for t in todos if t.get("priority") == "due"]
        info = [t for t in todos if t.get("priority") == "info"]

        if overdue:
            lines.append("⚠️ OVERDUE:")
            for t in overdue:
                lines.append(f"  - {t['message']}")
            lines.append("")

        if due:
            lines.append("📌 Due:")
            for t in due:
                lines.append(f"  - {t['message']}")
            lines.append("")

        if info:
            lines.append("📊 Progress:")
            for t in info:
                lines.append(f"  - {t['message']}")

        return [PromptMessage(
            role="user",
            content=TextContent(type="text", text="\n".join(lines))
        )]

    return []


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools with dynamic descriptions."""
    summary = get_urgent_summary()
    return get_tool_definitions(summary)


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls."""
    return await handle_tool(name, arguments)


async def run_stdio():
    """Run the MCP server via stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


# Background sync task
SYNC_INTERVAL_SECONDS = 60 * 60  # 1 hour


async def background_sync_task():
    """Background task that commits changes hourly."""
    while True:
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
        try:
            result = commit_and_push()
            if "Nothing to commit" not in result["message"]:
                logger.info(f"Background sync: {result['message']}")
        except Exception as e:
            logger.error(f"Background sync error: {e}")


def check_wger_connection():
    """Check if wger is configured and reachable on startup."""
    if not wger_service.is_authenticated():
        logger.info("Wger not configured (no ~/.goals-mcp/wger-config.yml)")
        return

    try:
        client = wger_service.get_client()
        if client:
            # Test connection by getting token
            client._get_token()
            logger.info(f"Wger connected: {client.host}")
    except Exception as e:
        logger.warning(f"Wger connection failed: {e}")


async def load_anki_mastery():
    """Load Anki mastery data in background on startup."""
    from . import anki

    try:
        success = await anki.load_mastery_async()
        if success:
            cache = anki.get_mastery_cache()
            logger.info(f"Anki mastery loaded: {len(cache)} vocab items")
        else:
            logger.info("Anki not available, practice prompts will use raw vocab")
    except Exception as e:
        logger.warning(f"Anki mastery load failed: {e}")


def create_sse_app():
    """Create SSE web application."""
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import HTMLResponse
    from mcp.server.sse import SseServerTransport

    sse = SseServerTransport("/messages/")

    @asynccontextmanager
    async def lifespan(app):
        """Start background tasks on startup."""
        # Check wger connection on startup
        check_wger_connection()

        # Load Anki mastery in background (non-blocking)
        anki_task = asyncio.create_task(load_anki_mastery())

        sync_task = asyncio.create_task(background_sync_task())
        logger.info("Started hourly background sync task")
        yield
        anki_task.cancel()
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            logger.info("Background sync task stopped")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await app.run(
                streams[0], streams[1], app.create_initialization_options()
            )

    async def handle_messages(scope, receive, send):
        await sse.handle_post_message(scope, receive, send)

    async def homepage(request):
        config = get_goals_config()
        goals = config.get("goals", {})
        todos = compute_todos(config)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Goals 2026 MCP</title>
            <style>
                body {{ font-family: system-ui; max-width: 800px; margin: 40px auto; padding: 0 20px; }}
                .todo {{ padding: 8px; margin: 4px 0; border-radius: 4px; }}
                .high {{ background: #fee; }}
                .medium {{ background: #ffefd5; }}
                .info {{ background: #f0f0f0; }}
            </style>
        </head>
        <body>
            <h1>Goals 2026 MCP Server</h1>
            <p>SSE endpoint: <code>http://localhost:8788/sse</code></p>

            <h2>Today's Check-in ({get_today()})</h2>
            {"".join(f'<div class="todo {t.get("priority", "info")}">{t["message"]}</div>' for t in todos) or "<p>All caught up!</p>"}

            <h2>Goals</h2>
            <ul>
            {"".join(f'<li><strong>{g.get("name", gid)}</strong> - {g.get("cadence", "open")}</li>' for gid, g in goals.items())}
            </ul>

            <h2>Connect from Claude Code</h2>
            <pre>claude mcp add goals -t sse http://localhost:8788/sse</pre>
        </body>
        </html>
        """
        return HTMLResponse(html)

    return Starlette(
        routes=[
            Route("/", homepage),
            Route("/sse", handle_sse),
            Mount("/messages", app=handle_messages),
        ],
        lifespan=lifespan
    )


def main():
    """Entry point."""
    if "auth" in sys.argv:
        from .auth import run_auth
        run_auth()
    elif "--stdio" in sys.argv:
        asyncio.run(run_stdio())
    else:
        import uvicorn
        port = int(os.environ.get("PORT", 8788))
        sse_app = create_sse_app()
        uvicorn.run(sse_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
