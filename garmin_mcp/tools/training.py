"""
Training tools — training status, VO2 max, training load, race predictions,
training readiness, and endurance score.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from mcp.server.fastmcp import FastMCP, Context

from garmin_mcp.tools._utils import garmin_call


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_training_status(
        ctx: Context,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve training status over a date range.

        Training status reflects whether current training is productive, maintaining
        fitness, overreaching, detraining, etc.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            List of daily training status entries including trainingStatus
            (e.g. 'PRODUCTIVE', 'MAINTAINING', 'RECOVERY'), acuteLoad, and
            the associated date.
        """
        client = ctx.request_context.lifespan_context["garmin"]

        # get_training_status takes a single date — loop over the range
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        results = []
        current = start
        while current <= end:
            day_str = current.isoformat()
            entry = garmin_call(client.get_training_status, day_str)
            if isinstance(entry, dict) and "error" in entry:
                return entry  # type: ignore[return-value]
            if entry:
                if isinstance(entry, list):
                    results.extend(entry)
                else:
                    results.append(entry)
            current += timedelta(days=1)
        return results

    @mcp.tool()
    async def get_training_readiness(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve training readiness score for a specific date.

        Training readiness is a 0–100 score reflecting how prepared the body is
        for a training load, based on sleep, HRV, recovery time, and acute load.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Training readiness score, category (e.g. 'READY', 'MODERATE', 'LOW'),
            and contributing factor scores (sleep, HRV, recovery, acute load).
        """
        client = ctx.request_context.lifespan_context["garmin"]
        data = garmin_call(client.get_training_readiness, date)

        if isinstance(data, dict) and "error" in data:
            return data

        # API returns a dict (not a list) — return it directly
        if isinstance(data, dict):
            return data
        # Defensive: if a list comes back, grab the last entry
        if isinstance(data, list) and data:
            return data[-1]
        return {}

    @mcp.tool()
    async def get_vo2max(
        ctx: Context,
    ) -> dict[str, Any]:
        """
        Retrieve the current VO2 max estimate and fitness age from Garmin.

        Returns:
            VO2 max value for running and/or cycling, Garmin fitness age,
            and VO2 max trend over time.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        today = date.today().isoformat()
        return garmin_call(client.get_max_metrics, today) or {}

    @mcp.tool()
    async def get_race_predictions(
        ctx: Context,
    ) -> dict[str, Any]:
        """
        Retrieve race time predictions based on current fitness.

        Returns:
            Predicted finish times for standard race distances:
            5K, 10K, half marathon, and marathon.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_race_predictions) or {}

    @mcp.tool()
    async def get_hill_score(
        ctx: Context,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve hill score data over a date range.

        Hill score reflects the ability to climb hills efficiently.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            List of hill score entries with date, score, and status.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_hill_score, start_date, end_date) or []

    @mcp.tool()
    async def get_endurance_score(
        ctx: Context,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve endurance score over a date range.

        Endurance score reflects aerobic fitness based on recent training history.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            List of endurance score entries with date and score value.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_endurance_score, start_date, end_date) or []

    @mcp.tool()
    async def get_running_tolerance(
        ctx: Context,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve running tolerance (running load tolerance) data.

        Running tolerance reflects how well the body is adapting to running stress
        and helps identify injury risk from overtraining.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            List of running tolerance entries including date, status, and score.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_running_tolerance, start_date, end_date) or []

    @mcp.tool()
    async def get_fitness_stats(
        ctx: Context,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        """
        Retrieve aggregate fitness statistics including training load summaries
        over a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            Fitness stats including aerobic training effect, anaerobic training effect,
            total activity time, and load distribution across intensity zones.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_progress_summary_between_dates, start_date, end_date) or {}
