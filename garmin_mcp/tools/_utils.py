"""
Shared utilities for garmin-mcp tool modules.
"""

from __future__ import annotations

from typing import Any

from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)


def garmin_call(fn, *args, **kwargs) -> Any:
    """
    Call a garminconnect client method with standard error handling.

    Catches the three common garminconnect exceptions and returns a plain
    error dict rather than raising, so MCP tools can surface friendly messages
    to the agent instead of a stack trace.

    Usage:
        result = garmin_call(client.get_sleep_data, date)
    """
    try:
        return fn(*args, **kwargs)
    except GarminConnectTooManyRequestsError:
        return {"error": "Rate limited by Garmin. Wait a few minutes and retry."}
    except GarminConnectAuthenticationError:
        return {"error": "Authentication expired. Run garmin-mcp-auth to re-authenticate."}
    except GarminConnectConnectionError as exc:
        return {"error": str(exc)}
