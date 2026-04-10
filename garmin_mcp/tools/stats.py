"""
Stats tools — weekly rollups, goals, progress summaries, and cycling FTP.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP, Context

from garmin_mcp.tools._utils import garmin_call


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_weekly_steps(
        ctx: Context,
        end_date: str,
        weeks: int = 4,
    ) -> list[dict[str, Any]]:
        """
        Retrieve weekly step count totals ending on a given date.

        Args:
            end_date: End date in YYYY-MM-DD format (last day of the final week).
            weeks: Number of weeks to look back (default 4, max 52).

        Returns:
            List of weekly step summaries including week start date and total steps.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        weeks = min(weeks, 52)
        return garmin_call(client.get_weekly_steps, end_date, weeks) or []

    @mcp.tool()
    async def get_weekly_stress(
        ctx: Context,
        end_date: str,
        weeks: int = 4,
    ) -> list[dict[str, Any]]:
        """
        Retrieve weekly average stress levels ending on a given date.

        Args:
            end_date: End date in YYYY-MM-DD format (last day of the final week).
            weeks: Number of weeks to look back (default 4, max 52).

        Returns:
            List of weekly stress summaries including week start date and average
            stress score.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        weeks = min(weeks, 52)
        return garmin_call(client.get_weekly_stress, end_date, weeks) or []

    @mcp.tool()
    async def get_goals(
        ctx: Context,
        status: str = "active",
    ) -> list[dict[str, Any]]:
        """
        Retrieve Garmin Connect goals.

        Args:
            status: Goal status filter — 'active' (default), 'completed', or 'archived'.

        Returns:
            List of goals including goal type (steps, distance, weight, etc.),
            target value, current value, start date, and target date.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_goals, status=status, start=0, limit=30) or []

    @mcp.tool()
    async def get_progress_summary(
        ctx: Context,
        start_date: str,
        end_date: str,
        metric: str = "distance",
    ) -> dict[str, Any]:
        """
        Retrieve an aggregated training progress summary over a date range.

        Useful for questions like "how far did I run last month?" or
        "how many calories did I burn this year?".

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            metric: The metric to aggregate. One of: 'distance', 'duration',
                    'calories', 'elevationGain', 'movingDuration'.
                    Defaults to 'distance'.

        Returns:
            Aggregated progress summary broken down by activity type, including
            totals and per-activity-type breakdowns for the chosen metric.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return (
            garmin_call(
                client.get_progress_summary_between_dates,
                start_date,
                end_date,
                metric=metric,
                groupbyactivities=True,
            )
            or {}
        )

    @mcp.tool()
    async def get_cycling_ftp(
        ctx: Context,
    ) -> dict[str, Any]:
        """
        Retrieve the current cycling Functional Threshold Power (FTP) estimate.

        FTP is the highest average power a cyclist can sustain for approximately
        one hour and is used to calibrate power-based training zones.

        Returns:
            FTP value in watts, the date it was recorded, and the detection method
            (auto-detected from a ride or manually entered).
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_cycling_ftp) or {}
