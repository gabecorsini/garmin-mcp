"""
Nutrition tools — daily nutrition summaries and food logs from Garmin Connect.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP, Context

from garmin_mcp.tools._utils import garmin_call


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_nutrition_summary(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve the daily nutrition summary for a specific date.

        Returns totals for calories, macronutrients (carbs, fat, protein),
        water intake, and any calorie goals set in Garmin Connect.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Nutrition summary including totalCalories, totalCarbs, totalFat,
            totalProtein, totalFiber, totalSugar, totalSodium, totalWater,
            netCalories, and calorieGoal.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_nutrition_daily_meals, date) or {}

    @mcp.tool()
    async def get_food_logs(
        ctx: Context,
        date: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve individual food log entries for a specific date.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            List of food log entries including food name, meal type (breakfast,
            lunch, dinner, snack), calories, servingSize, and macros per entry.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        data = garmin_call(client.get_nutrition_daily_food_log, date) or {}

        if isinstance(data, dict) and "error" in data:
            return data  # type: ignore[return-value]

        # Flatten food logs across meal types into a single list
        if isinstance(data, dict):
            logs = []
            for meal_entries in data.values():
                if isinstance(meal_entries, list):
                    logs.extend(meal_entries)
            return logs
        if isinstance(data, list):
            return data
        return []

    @mcp.tool()
    async def get_nutrition_settings(
        ctx: Context,
        date: str,
    ) -> dict[str, Any]:
        """
        Retrieve nutrition goal settings from Garmin Connect for a specific date.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Configured nutrition targets including daily calorie goal,
            macro percentage targets (carbs/fat/protein), and meal plan settings.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_nutrition_daily_settings, date) or {}
