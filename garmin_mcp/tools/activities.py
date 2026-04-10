"""
Activities tools — retrieve Garmin Connect activity history and details.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP, Context

from garmin_mcp.tools._utils import garmin_call


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_activities(
        ctx: Context,
        start: int = 0,
        limit: int = 20,
        activity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve a list of recent Garmin Connect activities.

        Args:
            start: Offset for pagination (default 0).
            limit: Number of activities to return (max 100, default 20).
            activity_type: Optional filter, e.g. 'running', 'cycling', 'swimming',
                           'strength_training', 'hiking'. Leave blank for all types.

        Returns:
            List of activity summaries including activityId, activityName, activityType,
            startTimeLocal, distance (meters), duration (seconds), averageHR, maxHR,
            calories, elevationGain, and averageSpeed.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        limit = min(limit, 100)
        activities = garmin_call(client.get_activities, start, limit, activitytype=activity_type)

        if isinstance(activities, dict) and "error" in activities:
            return activities  # type: ignore[return-value]

        keys = [
            "activityId", "activityName", "activityType", "startTimeLocal",
            "distance", "duration", "averageHR", "maxHR", "calories",
            "elevationGain", "averageSpeed", "avgPower",
        ]
        return [
            {k: a.get(k) for k in keys if a.get(k) is not None}
            for a in (activities or [])
        ]

    @mcp.tool()
    async def get_activity_detail(
        ctx: Context,
        activity_id: int,
    ) -> dict[str, Any]:
        """
        Retrieve detailed information for a specific activity by its ID.

        Args:
            activity_id: The Garmin activity ID (visible in Garmin Connect URLs or
                         returned by get_activities).

        Returns:
            Detailed activity data including splits, laps, weather, device info,
            and performance metrics. GPS coordinates are excluded.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        detail = garmin_call(client.get_activity, activity_id)

        if isinstance(detail, dict) and "error" in detail:
            return detail

        # Strip raw GPS/polyline data to keep response LLM-friendly
        for key in ("geoPolylineDTO", "metadataDTO", "fullFormattedMessage"):
            detail.pop(key, None)

        return detail

    @mcp.tool()
    async def get_activity_hr_zones(
        ctx: Context,
        activity_id: int,
    ) -> dict[str, Any]:
        """
        Retrieve heart rate zone breakdown for a specific activity.

        Args:
            activity_id: The Garmin activity ID.

        Returns:
            Time spent in each HR zone (zone1–zone5) in seconds, along with
            zone boundaries in bpm.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_activity_hr_in_timezones, activity_id) or {}

    @mcp.tool()
    async def get_activities_by_date(
        ctx: Context,
        start_date: str,
        end_date: str,
        activity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve activities within a specific date range.

        Args:
            start_date: Start date in YYYY-MM-DD format (inclusive).
            end_date: End date in YYYY-MM-DD format (inclusive).
            activity_type: Optional filter, e.g. 'running', 'cycling'. Leave blank for all.

        Returns:
            List of activity summaries within the date range.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        activities = garmin_call(
            client.get_activities_by_date,
            start_date, end_date, activitytype=activity_type,
        )

        if isinstance(activities, dict) and "error" in activities:
            return activities  # type: ignore[return-value]

        keys = [
            "activityId", "activityName", "activityType", "startTimeLocal",
            "distance", "duration", "averageHR", "maxHR", "calories",
            "elevationGain", "averageSpeed",
        ]
        return [
            {k: a.get(k) for k in keys if a.get(k) is not None}
            for a in (activities or [])
        ]

    @mcp.tool()
    async def get_activity_splits(
        ctx: Context,
        activity_id: int,
    ) -> dict[str, Any]:
        """
        Retrieve split data (e.g. per-mile/km pace) for a specific activity.

        Args:
            activity_id: The Garmin activity ID.

        Returns:
            Split summaries including distance, elapsed duration, moving duration,
            average speed, and average HR per split.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_activity_splits, activity_id) or {}

    @mcp.tool()
    async def get_personal_records(
        ctx: Context,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all personal records (PRs) from Garmin Connect.

        Returns:
            List of personal records including activity type, PR type (e.g. fastest 5K,
            longest run), value, and the date achieved.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_personal_record) or []

    @mcp.tool()
    async def get_activity_count(
        ctx: Context,
    ) -> dict[str, Any]:
        """
        Retrieve the total count of activities stored in Garmin Connect.

        Returns:
            Dict with total activity count.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        count = garmin_call(client.count_activities)
        if isinstance(count, dict) and "error" in count:
            return count
        return {"totalCount": count}

    @mcp.tool()
    async def get_last_activity(
        ctx: Context,
    ) -> dict[str, Any]:
        """
        Retrieve the most recent Garmin Connect activity.

        Returns:
            Activity summary including activityId, activityName, activityType,
            startTimeLocal, distance (meters), duration (seconds), averageHR,
            maxHR, calories, elevationGain, and averageSpeed.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        activity = garmin_call(client.get_last_activity)

        if isinstance(activity, dict) and "error" in activity:
            return activity

        keys = [
            "activityId", "activityName", "activityType", "startTimeLocal",
            "distance", "duration", "averageHR", "maxHR", "calories",
            "elevationGain", "averageSpeed", "avgPower",
        ]
        if isinstance(activity, list):
            activity = activity[0] if activity else {}
        return {k: activity.get(k) for k in keys if activity.get(k) is not None}

    @mcp.tool()
    async def get_activity_typed_splits(
        ctx: Context,
        activity_id: int,
    ) -> dict[str, Any]:
        """
        Retrieve typed split data for a specific activity.

        Typed splits distinguish between different split types within an activity
        (e.g. auto laps, manual laps, interval splits). More granular than
        get_activity_splits.

        Args:
            activity_id: The Garmin activity ID.

        Returns:
            Typed split summaries grouped by split type, including distance,
            duration, average pace, average HR, and elevation per split.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_activity_typed_splits, activity_id) or {}
