"""
Garmin MCP server entry point.

Starts a FastMCP server over stdio with all Garmin Connect tools registered.
Authentication uses cached garth tokens from ~/.garth/ — run `garmin-mcp-auth`
once before starting this server.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP

from garmin_mcp.auth import get_client
from garmin_mcp.tools import (
    activities,
    body_composition,
    extras,
    health,
    nutrition,
    profile,
    training,
    workouts,
    workout_write,
    write,
)


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Authenticate once at startup and pass the client via context."""
    try:
        client = get_client()
    except RuntimeError as exc:
        print(f"[garmin-mcp] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(
        f"[garmin-mcp] Connected to Garmin Connect as: {client.display_name}",
        file=sys.stderr,
    )
    yield {"garmin": client}


mcp = FastMCP(
    name="garmin-mcp",
    instructions=(
        "This server provides read and write access to a personal Garmin Connect account. "
        "Use the available tools to retrieve fitness activities, health metrics, "
        "sleep data, HRV, stress, body composition, training load, VO2 max, "
        "race predictions, workouts, nutrition summaries, and device/profile info. "
        "Write tools allow logging weight, logging hydration, creating structured workouts, "
        "scheduling workouts to the calendar, and uploading activity files. "
        "All dates should be provided in YYYY-MM-DD format unless otherwise noted."
    ),
    lifespan=lifespan,
)

# Register all tool modules
activities.register(mcp)
health.register(mcp)
body_composition.register(mcp)
training.register(mcp)
workouts.register(mcp)
nutrition.register(mcp)
profile.register(mcp)
extras.register(mcp)
# v2: write tools
write.register(mcp)
workout_write.register(mcp)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
