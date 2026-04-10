"""
Body composition tools — weight, BMI, body fat, and muscle mass trends.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP, Context

from garmin_mcp.tools._utils import garmin_call


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_body_composition(
        ctx: Context,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        """
        Retrieve body composition measurements over a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            Body composition data including weight (kg), BMI, bodyFatPercentage,
            muscleMass (kg), boneMass (kg), and visceralFat rating where available
            from your scale/device. The API returns a dict keyed by date or a
            summary wrapper — all fields are returned as-is.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        # get_body_composition returns a dict, not a list
        return garmin_call(client.get_body_composition, start_date, end_date) or {}

    @mcp.tool()
    async def get_weight_history(
        ctx: Context,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve weight log entries over a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            List of weight entries with date, weight (kg), and BMI.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        data = garmin_call(client.get_weigh_ins, start_date, end_date) or {}

        if isinstance(data, dict) and "error" in data:
            return data  # type: ignore[return-value]

        # Flatten to a simple list of entries
        if isinstance(data, dict):
            entries = data.get("dateWeightList", data.get("allWeightMetrics", []))
            return entries or []
        return data

    @mcp.tool()
    async def get_weight_stats(
        ctx: Context,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        """
        Retrieve aggregated weight statistics (average, min, max) over a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            Weight stats including average, minimum, and maximum weight in kg
            over the specified period, plus the overall trend direction.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        data = garmin_call(client.get_weigh_ins, start_date, end_date) or {}

        if isinstance(data, dict) and "error" in data:
            return data

        if isinstance(data, dict):
            return {
                k: v for k, v in data.items()
                if k not in ("dateWeightList", "allWeightMetrics")
            }
        return {}
