"""
Write tools — log weight, log hydration, upload activities.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP, Context


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def log_weight(
        ctx: Context,
        weight_kg: float,
        timestamp: str = "",
    ) -> dict[str, Any]:
        """
        Log a body weight measurement to Garmin Connect.

        Args:
            weight_kg: Weight in kilograms (e.g. 75.4).
            timestamp: Optional ISO 8601 datetime string (e.g. "2026-04-09T08:00:00").
                       Defaults to the current time if omitted.

        Returns:
            Confirmation dict from Garmin with the logged weight entry details.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        result = client.add_weigh_in(
            weight=weight_kg,
            unitKey="kg",
            timestamp=timestamp,
        )
        return result or {"status": "logged", "weight_kg": weight_kg}

    @mcp.tool()
    async def log_hydration(
        ctx: Context,
        amount_ml: float,
        timestamp: str = "",
        date: str = "",
    ) -> dict[str, Any]:
        """
        Log a water intake entry to Garmin Connect.

        Args:
            amount_ml: Amount of water in millilitres (positive to add, negative to remove).
            timestamp: Optional ISO 8601 datetime (e.g. "2026-04-09T10:30:00").
                       Defaults to current time.
            date: Optional date string YYYY-MM-DD. Defaults to today.

        Returns:
            Confirmation dict with the updated daily hydration totals.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        result = client.add_hydration_data(
            value_in_ml=amount_ml,
            timestamp=timestamp or None,
            cdate=date or None,
        )
        return result or {"status": "logged", "amount_ml": amount_ml}

    @mcp.tool()
    async def upload_activity(
        ctx: Context,
        file_path: str,
    ) -> dict[str, Any]:
        """
        Upload a FIT, TCX, or GPX activity file to Garmin Connect.

        The file is treated as an import (not re-exported to third parties like Strava).

        Args:
            file_path: Absolute path to the activity file on disk.

        Returns:
            Dict with upload result including any created activity IDs.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        result = client.import_activity(file_path)
        return result or {"status": "uploaded", "file": file_path}
