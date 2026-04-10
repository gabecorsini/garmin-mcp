"""
Health tools — sleep, HRV, stress, body battery, steps, heart rate, and more.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from mcp.server.fastmcp import FastMCP, Context

from garmin_mcp.tools._utils import garmin_call


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_sleep_data(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve detailed sleep data for a specific date.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Sleep summary including total sleep time, sleep stages (deep, light, REM,
            awake), sleep score, and overnight SpO2/respiration averages.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        data = garmin_call(client.get_sleep_data, date)

        # Remove raw epoch-level timeline data — too verbose for LLM context
        # NOTE: remSleepData and sleepBodyBattery are summary fields — keep them.
        # Only sleepMovement (per-minute actigraphy) and sleepLevels (raw stage array)
        # are stripped.
        if isinstance(data, dict):
            data.pop("sleepMovement", None)
            data.pop("sleepLevels", None)
            data.pop("hrvData", None)
        return data or {}

    @mcp.tool()
    async def get_hrv_data(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve Heart Rate Variability (HRV) data for a specific date.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            HRV summary including nightly average HRV (ms), 5-minute HRV readings,
            HRV status (balanced, low, unbalanced), and baseline ranges.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        data = garmin_call(client.get_hrv_data, date) or {}

        # Keep summary, drop per-reading timeline for brevity
        if isinstance(data, dict):
            data.pop("hrvReadings", None)
        return data

    @mcp.tool()
    async def get_daily_stress(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve stress level data for a specific date.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Daily stress summary including average stress, max stress, rest stress,
            and time spent in low/medium/high/rest stress buckets (seconds).
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_stress_data, date) or {}

    @mcp.tool()
    async def get_body_battery(
        ctx: Context,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve Body Battery energy levels for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            Daily Body Battery summaries including charged/drained values and
            start/end battery levels for each day in the range.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        data = garmin_call(client.get_body_battery, start_date, end_date) or []

        if isinstance(data, dict) and "error" in data:
            return data  # type: ignore[return-value]

        # Strip per-minute readings; keep daily summaries
        cleaned = []
        for entry in data:
            if isinstance(entry, dict):
                entry.pop("bodyBatteryValuesArray", None)
                cleaned.append(entry)
        return cleaned

    @mcp.tool()
    async def get_daily_steps(
        ctx: Context,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve daily step counts for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            List of daily step summaries including totalSteps, totalDistance,
            stepGoal, and wellnessActiveKilocalories per day.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_daily_steps, start_date, end_date) or []

    @mcp.tool()
    async def get_heart_rate(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve heart rate data for a specific date.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Daily HR summary including restingHeartRate, minHeartRate, maxHeartRate,
            and averageHeartRate. Per-minute HR readings are excluded.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        data = garmin_call(client.get_heart_rates, date) or {}

        # Remove high-frequency per-reading data
        if isinstance(data, dict):
            data.pop("heartRateValues", None)
        return data

    @mcp.tool()
    async def get_resting_heart_rate(
        ctx: Context,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve resting heart rate (RHR) trend over a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            List of daily resting heart rate values with dates.
        """
        client = ctx.request_context.lifespan_context["garmin"]

        # get_rhr_day takes a single date — loop over the range
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        results = []
        current = start
        while current <= end:
            day_str = current.isoformat()
            entry = garmin_call(client.get_rhr_day, day_str)
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
    async def get_respiration_data(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve daily respiration (breathing rate) data.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Respiration summary including average, min, max breaths per minute,
            and sleep respiration data.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        data = garmin_call(client.get_respiration_data, date) or {}
        if isinstance(data, dict):
            data.pop("respirationValues", None)
        return data

    @mcp.tool()
    async def get_spo2_data(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve blood oxygen saturation (SpO2) data for a specific date.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            SpO2 summary including average, min, and max SpO2 percentages,
            and overnight continuous monitoring averages.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        data = garmin_call(client.get_spo2_data, date) or {}
        if isinstance(data, dict):
            data.pop("spO2HourlyAverages", None)
            data.pop("continuousReadingDTOList", None)
        return data

    @mcp.tool()
    async def get_intensity_minutes(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve weekly intensity minutes (moderate + vigorous) for the week
        containing the given date.

        Args:
            date: Any date in YYYY-MM-DD format within the desired week.

        Returns:
            Intensity minute totals including weeklyModerate, weeklyVigorous,
            and combined weekly total vs. goal.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_intensity_minutes_data, date) or {}

    @mcp.tool()
    async def get_floors(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve floors climbed data for a specific date.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Floors climbed summary including floorsAscended, floorsDescended,
            and daily goal.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        data = garmin_call(client.get_floors, date) or {}
        if isinstance(data, dict):
            data.pop("floorValuesArray", None)
        return data

    @mcp.tool()
    async def get_hydration(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve daily hydration log for a specific date.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Hydration summary including totalIntakeInML, sweatLossInML, goal,
            and activity hydration.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_hydration_data, date) or {}

    @mcp.tool()
    async def get_daily_summary(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve the overall daily wellness summary for a specific date.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Daily summary including steps, calories (active + resting),
            distance, floors, moderate/vigorous intensity minutes, stress average,
            body battery start/end, and restingHeartRate.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_stats, date) or {}
