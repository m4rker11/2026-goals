"""Goals 2026 MCP Server - Main entry point."""

import os
import sys
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

from .storage import get_goals_config, get_today
from .goals import compute_todos
from .tools import TOOL_DEFINITIONS, handle_tool


# Create MCP server
app = Server("goals-2026")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return TOOL_DEFINITIONS


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls."""
    return await handle_tool(name, arguments)


async def run_stdio():
    """Run the MCP server via stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def create_sse_app():
    """Create SSE web application."""
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import HTMLResponse
    from mcp.server.sse import SseServerTransport

    sse = SseServerTransport("/messages/")

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
        ]
    )


def main():
    """Entry point."""
    if "--stdio" in sys.argv:
        asyncio.run(run_stdio())
    else:
        import uvicorn
        port = int(os.environ.get("PORT", 8788))
        sse_app = create_sse_app()
        uvicorn.run(sse_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
