"""
Profile tools — user profile, connected devices, gear, and earned badges.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP, Context

from garmin_mcp.tools._utils import garmin_call


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_user_profile(
        ctx: Context,
    ) -> dict[str, Any]:
        """
        Retrieve the Garmin Connect user profile.

        Returns:
            Profile data including displayName, fullName, location, profileImageUrl,
            and account creation date.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_user_profile) or {}

    @mcp.tool()
    async def get_user_settings(
        ctx: Context,
    ) -> dict[str, Any]:
        """
        Retrieve user account settings and unit preferences from Garmin Connect.

        Returns:
            Settings including measurement system (metric/imperial), time format,
            first day of week, HR zone definitions, and lactate threshold.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_userprofile_settings) or {}

    @mcp.tool()
    async def get_devices(
        ctx: Context,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all Garmin devices registered to the account.

        Returns:
            List of devices including deviceId, productDisplayName (e.g. 'Fenix 8'),
            deviceTypeName, softwareVersion, and lastUsed date.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_devices) or []

    @mcp.tool()
    async def get_device_settings(
        ctx: Context,
        device_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve settings and configuration for a specific registered device.

        Args:
            device_id: The device ID (returned by get_devices).

        Returns:
            Device settings including HR alert thresholds, GPS settings, activity
            tracking settings, and display preferences.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_device_settings, device_id) or {}

    @mcp.tool()
    async def get_gear(
        ctx: Context,
        activity_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve gear registered in Garmin Connect, optionally filtered to gear
        used in a specific activity.

        Args:
            activity_id: Optional activity ID to filter gear used in that activity.
                         If None, returns all registered gear.

        Returns:
            List of gear items including gearId, displayName, gearTypeName (e.g. 'shoes'),
            totalActivities, totalDistance (meters), and dateBegin.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        if activity_id is not None:
            return garmin_call(client.get_activity_gear, activity_id) or []

        # get_gear requires a numeric userProfileNumber, not display_name
        profile = garmin_call(client.connectapi, "/userprofile-service/socialProfile")
        if isinstance(profile, dict) and "error" in profile:
            return profile  # type: ignore[return-value]
        user_profile_number = (profile or {}).get("id")
        if not user_profile_number:
            return {"error": "Could not resolve userProfileNumber from social profile"}  # type: ignore[return-value]
        return garmin_call(client.get_gear, user_profile_number) or []

    @mcp.tool()
    async def get_earned_badges(
        ctx: Context,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all earned badges and achievements from Garmin Connect.

        Returns:
            List of earned badges including badgeName, badgeCategoryName,
            earnedDate, and badgePoints.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_earned_badges) or []

    @mcp.tool()
    async def get_primary_training_device(
        ctx: Context,
    ) -> dict[str, Any]:
        """
        Retrieve the primary training device for the account.

        Returns:
            Primary device info including productDisplayName, deviceTypeName,
            and deviceId.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        return garmin_call(client.get_primary_training_device) or {}
