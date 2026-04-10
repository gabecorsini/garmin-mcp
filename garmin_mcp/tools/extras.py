"""
Extras tools — additional Garmin Connect data not covered by the core modules.

Includes: activity exercise sets, activity weather, body battery events,
morning training readiness, lactate threshold, and fitness age.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from mcp.server.fastmcp import FastMCP, Context

from garmin_mcp.tools._utils import garmin_call


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_activity_exercise_sets(
        ctx: Context,
        activity_id: int,
    ) -> dict[str, Any]:
        """
        Retrieve exercise sets for a strength training activity.

        Each set includes exercise name, reps, weight, duration, and set order.
        Only available for strength training activities recorded with a compatible
        Garmin device.

        Args:
            activity_id: The Garmin activity ID (returned by get_activities).

        Returns:
            Dict containing exercise sets grouped by exercise, with reps,
            weight (kg), and duration per set.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_activity_exercise_sets, activity_id) or {}

    @mcp.tool()
    async def get_activity_weather(
        ctx: Context,
        activity_id: int,
    ) -> dict[str, Any]:
        """
        Retrieve weather conditions recorded during a specific activity.

        Args:
            activity_id: The Garmin activity ID (returned by get_activities).

        Returns:
            Weather data including temperature, humidity, wind speed/direction,
            and weather condition (e.g. clear, cloudy, rain) at the time of the activity.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_activity_weather, activity_id) or {}

    @mcp.tool()
    async def get_body_battery_events(
        ctx: Context,
        date: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve body battery charge and drain events for a specific date.

        Events explain why body battery changed throughout the day — e.g. sleep
        charging it, stress or activity draining it, and by how much.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            List of body battery events including eventType (charge/drain),
            startTimestamp, durationInMs, bodyBatteryImpact, and eventSubType.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_body_battery_events, date) or []

    @mcp.tool()
    async def get_morning_training_readiness(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve the Morning Report training readiness for a specific date.

        This is the post-wakeup readiness score shown in Garmin's Morning Report,
        distinct from the intraday training readiness score.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Morning readiness score, category, and contributing factor breakdown
            (sleep quality, HRV status, recovery time, acute load).
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_morning_training_readiness, date) or {}

    @mcp.tool()
    async def get_lactate_threshold(
        ctx: Context,
    ) -> dict[str, Any]:
        """
        Retrieve the current lactate threshold estimate from Garmin.

        Lactate threshold (LT) is the exercise intensity at which lactate begins
        to accumulate rapidly. Used to calibrate HR/pace training zones.

        Returns:
            Lactate threshold data including LT heart rate (bpm), LT pace (m/s),
            and LT power (watts) where available.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_lactate_threshold) or {}

    @mcp.tool()
    async def get_fitnessage_data(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve Garmin Fitness Age for a specific date.

        Fitness Age is a Garmin metric estimating biological age based on VO2 max,
        activity level, BMI, and resting heart rate. Lower is better.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Fitness Age value and comparison to chronological age.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_fitnessage_data, date) or {}
