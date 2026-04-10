"""
Workouts tools — read the workout library stored in Garmin Connect.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP, Context

from garmin_mcp.tools._utils import garmin_call


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_workouts(
        ctx: Context,
        start: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Retrieve saved workouts from the Garmin Connect workout library.

        Args:
            start: Pagination offset (default 0).
            limit: Number of workouts to return (default 20, max 100).

        Returns:
            List of workout summaries including workoutId, workoutName, sportType,
            estimatedDurationInSecs, estimatedDistanceInMeters, and workoutProvider.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        limit = min(limit, 100)
        return garmin_call(client.get_workouts, start, limit) or []

    @mcp.tool()
    async def get_workout_detail(
        ctx: Context,
        workout_id: int,
    ) -> dict[str, Any]:
        """
        Retrieve full detail for a specific saved workout.

        Args:
            workout_id: The Garmin workout ID (returned by get_workouts).

        Returns:
            Full workout definition including all steps, targets (pace/HR/power),
            sport type, and estimated metrics.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_workout_by_id, workout_id) or {}
