"""
Workout write tools — create structured workouts and push them to Garmin Connect.

The create_workout tool accepts a high-level workout description using a step-based
schema that the Garmin agent can populate directly from its recommendations. Steps
support HR zones, pace ranges, and time/distance end conditions. Repeat blocks are
supported for intervals.
"""

from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime, timedelta
from typing import Any

from mcp.server.fastmcp import FastMCP, Context

from garmin_mcp.tools._utils import garmin_call


# ---------------------------------------------------------------------------
# Target builders
# ---------------------------------------------------------------------------

def _hr_zone_target(zone: int) -> dict[str, Any]:
    """Build a heart-rate-zone target dict (zones 1–5)."""
    return {
        "workoutTargetTypeId": 4,
        "workoutTargetTypeKey": "heart.rate.zone",
        "displayOrder": 1,
        "targetValueOne": float(zone),
        "targetValueTwo": float(zone),
    }


def _pace_target(min_pace_sec_per_km: float, max_pace_sec_per_km: float) -> dict[str, Any]:
    """Build a speed-zone target from pace boundaries (seconds per km → m/s)."""
    # Garmin speed targets are in m/s; pace in s/km → speed = 1000 / pace
    speed_min = 1000.0 / max_pace_sec_per_km  # slower pace = lower speed
    speed_max = 1000.0 / min_pace_sec_per_km  # faster pace = higher speed
    return {
        "workoutTargetTypeId": 5,
        "workoutTargetTypeKey": "speed.zone",
        "displayOrder": 1,
        "targetValueOne": speed_min,
        "targetValueTwo": speed_max,
    }


def _open_target() -> dict[str, Any]:
    return {
        "workoutTargetTypeId": 6,
        "workoutTargetTypeKey": "open",
        "displayOrder": 1,
    }


def _no_target() -> dict[str, Any]:
    return {
        "workoutTargetTypeId": 1,
        "workoutTargetTypeKey": "no.target",
        "displayOrder": 1,
    }


# ---------------------------------------------------------------------------
# End-condition builders
# ---------------------------------------------------------------------------

def _time_condition(seconds: float) -> tuple[dict[str, Any], float]:
    return (
        {
            "conditionTypeId": 2,
            "conditionTypeKey": "time",
            "displayOrder": 2,
            "displayable": True,
        },
        float(seconds),
    )


def _distance_condition(meters: float) -> tuple[dict[str, Any], float]:
    return (
        {
            "conditionTypeId": 1,
            "conditionTypeKey": "distance",
            "displayOrder": 1,
            "displayable": True,
        },
        float(meters),
    )


# ---------------------------------------------------------------------------
# Step type dicts
# ---------------------------------------------------------------------------

_STEP_TYPE = {
    "warmup":   {"stepTypeId": 1, "stepTypeKey": "warmup",   "displayOrder": 1},
    "cooldown": {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2},
    "interval": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
    "recovery": {"stepTypeId": 4, "stepTypeKey": "recovery", "displayOrder": 4},
    "rest":     {"stepTypeId": 5, "stepTypeKey": "rest",     "displayOrder": 5},
    "repeat":   {"stepTypeId": 6, "stepTypeKey": "repeat",   "displayOrder": 6},
    "other":    {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
}

_SPORT_TYPES = {
    "running":  {"sportTypeId": 1, "sportTypeKey": "running",           "displayOrder": 1},
    "cycling":  {"sportTypeId": 2, "sportTypeKey": "cycling",           "displayOrder": 2},
    "swimming": {"sportTypeId": 3, "sportTypeKey": "lap_swimming",      "displayOrder": 3},
    "walking":  {"sportTypeId": 4, "sportTypeKey": "walking",           "displayOrder": 4},
    "hiking":   {"sportTypeId": 7, "sportTypeKey": "hiking",            "displayOrder": 7},
    "strength": {"sportTypeId": 9, "sportTypeKey": "strength_training", "displayOrder": 6},
    "cardio":   {"sportTypeId": 26, "sportTypeKey": "cardio_training",  "displayOrder": 7},
    "other":    {"sportTypeId": 8, "sportTypeKey": "other",             "displayOrder": 8},
}


def _parse_date(value: str, field_name: str) -> date_cls:
    """Parse a YYYY-MM-DD date string with a friendly validation error."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field_name} must be in YYYY-MM-DD format, got: {value!r}") from exc


def _resolve_target_dates(
    date: str | None = None,
    dates: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[date_cls]:
    """Resolve exact dates or an inclusive range into a sorted unique date list."""
    exact_dates: list[date_cls] = []
    if date:
        exact_dates.append(_parse_date(date, "date"))
    if dates:
        for idx, value in enumerate(dates):
            exact_dates.append(_parse_date(value, f"dates[{idx}]"))

    has_exact_dates = bool(exact_dates)
    has_range = bool(start_date or end_date)

    if has_exact_dates and has_range:
        raise ValueError("Provide either date/date(s) or start_date+end_date, not both.")

    if not has_exact_dates and not has_range:
        raise ValueError("Provide date, dates, or both start_date and end_date.")

    if has_range:
        if not start_date or not end_date:
            raise ValueError("Both start_date and end_date are required for a date range.")

        start = _parse_date(start_date, "start_date")
        end = _parse_date(end_date, "end_date")
        if end < start:
            raise ValueError("end_date must be on or after start_date.")

        span_days = (end - start).days
        if span_days > 366:
            raise ValueError("Date range cannot exceed 366 days.")

        return [start + timedelta(days=offset) for offset in range(span_days + 1)]

    return sorted(set(exact_dates))


def _scheduled_workout_summary(item: dict[str, Any]) -> dict[str, Any]:
    """Return a compact, stable summary for a scheduled workout calendar item."""
    return {
        "scheduledWorkoutId": item.get("id"),
        "workoutId": item.get("workoutId"),
        "title": item.get("title"),
        "date": item.get("date"),
        "sportTypeKey": item.get("sportTypeKey"),
        "protectedWorkoutSchedule": bool(item.get("protectedWorkoutSchedule", False)),
    }


def _get_scheduled_workouts(client: Any, year: int, month: int) -> dict[str, Any]:
    """Fetch calendar items for a month across garminconnect versions."""
    year = int(year)
    month = int(month)
    if year < 2000:
        raise ValueError(f"year must be 2000 or later, got: {year}")
    if month < 1 or month > 12:
        raise ValueError(f"month must be between 1 and 12, got: {month}")

    if hasattr(client, "get_scheduled_workouts"):
        return garmin_call(client.get_scheduled_workouts, year, month) or {}

    base_url = getattr(client, "garmin_scheduled_workouts_url", "/calendar-service")
    url = f"{base_url}/year/{year}/month/{month - 1}"
    return garmin_call(client.connectapi, url) or {}


# ---------------------------------------------------------------------------
# Step builder
# ---------------------------------------------------------------------------

def _build_target(step: dict[str, Any]) -> dict[str, Any]:
    """Derive a Garmin target dict from a step definition."""
    if step.get("hr_zone"):
        return _hr_zone_target(int(step["hr_zone"]))
    if step.get("min_pace_sec_per_km") and step.get("max_pace_sec_per_km"):
        return _pace_target(
            float(step["min_pace_sec_per_km"]),
            float(step["max_pace_sec_per_km"]),
        )
    if step.get("open"):
        return _open_target()
    return _no_target()


def _build_end_condition(step: dict[str, Any]) -> tuple[dict[str, Any], float]:
    """Derive a Garmin end condition and value from a step definition."""
    if step.get("duration_seconds"):
        return _time_condition(float(step["duration_seconds"]))
    if step.get("distance_meters"):
        return _distance_condition(float(step["distance_meters"]))
    # fallback: lap button
    return (
        {
            "conditionTypeId": 3,
            "conditionTypeKey": "lap.button",
            "displayOrder": 7,
            "displayable": False,
        },
        1.0,
    )


def _build_executable_step(step: dict[str, Any], order: int) -> dict[str, Any]:
    step_type_key = step.get("type", "interval").lower()
    step_type = _STEP_TYPE.get(step_type_key, _STEP_TYPE["interval"])
    target = _build_target(step)
    end_cond, end_val = _build_end_condition(step)
    return {
        "type": "ExecutableStepDTO",
        "stepOrder": order,
        "stepType": step_type,
        "endCondition": end_cond,
        "endConditionValue": end_val,
        "targetType": target,
    }


def _build_steps(
    steps: list[dict[str, Any]],
    start_order: int = 1,
) -> tuple[list[dict[str, Any]], int, int]:
    """
    Recursively build Garmin step dicts from the user-friendly step list.
    Returns (built_steps, next_order, total_duration_seconds).
    """
    built: list[dict[str, Any]] = []
    order = start_order
    total_secs = 0

    for step in steps:
        step_type = step.get("type", "interval").lower()

        if step_type == "repeat":
            iterations = int(step.get("iterations", 1))
            inner_steps_def = step.get("steps", [])
            inner_steps, order, inner_secs = _build_steps(inner_steps_def, order)
            total_secs += inner_secs * iterations
            repeat_block = {
                "type": "RepeatGroupDTO",
                "stepOrder": order,
                "stepType": _STEP_TYPE["repeat"],
                "numberOfIterations": iterations,
                "workoutSteps": inner_steps,
                "endCondition": {
                    "conditionTypeId": 7,
                    "conditionTypeKey": "iterations",
                    "displayOrder": 7,
                    "displayable": False,
                },
                "endConditionValue": float(iterations),
                "smartRepeat": False,
            }
            built.append(repeat_block)
            order += 1
        else:
            exe = _build_executable_step(step, order)
            built.append(exe)
            order += 1
            total_secs += step.get("duration_seconds", 0)

    return built, order, total_secs


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def create_workout(
        ctx: Context,
        name: str,
        sport: str,
        steps: list[dict[str, Any]],
        description: str = "",
    ) -> dict[str, Any]:
        """
        Create a structured workout in the Garmin Connect workout library.

        Each step is a dict with these fields:
          - type (str): "warmup" | "interval" | "recovery" | "cooldown" | "rest" | "repeat"
          - duration_seconds (float): end condition in seconds (use this OR distance_meters)
          - distance_meters (float): end condition in meters (use this OR duration_seconds)
          - hr_zone (int): target HR zone 1–5 (mutually exclusive with pace target)
          - min_pace_sec_per_km (float): fastest pace in sec/km, e.g. 270 = 4:30/km
          - max_pace_sec_per_km (float): slowest pace in sec/km, e.g. 330 = 5:30/km
          - open (bool): set true for an open/lap-button end condition with no target

        For repeat blocks, add:
          - type: "repeat"
          - iterations (int): number of repetitions
          - steps (list): nested step dicts (same schema as above, no further nesting)

        Example — 5x1km threshold intervals:
          steps=[
            {"type": "warmup",   "duration_seconds": 600, "hr_zone": 2},
            {"type": "repeat",   "iterations": 5, "steps": [
              {"type": "interval", "distance_meters": 1000, "hr_zone": 4},
              {"type": "recovery", "duration_seconds": 90,  "hr_zone": 1},
            ]},
            {"type": "cooldown", "duration_seconds": 600, "hr_zone": 1},
          ]

        Args:
            name: Workout name shown in Garmin Connect (e.g. "5x1km Threshold").
            sport: Sport type: "running" | "cycling" | "swimming" | "walking" |
                   "hiking" | "strength" | "cardio" | "other".
            steps: List of step dicts as described above.
            description: Optional free-text description stored with the workout.

        Returns:
            Dict with the created workout's ID and details. Use the workoutId to
            schedule it with schedule_workout.
        """
        client = ctx.request_context.lifespan_context["garmin"]

        sport_key = sport.lower()
        sport_type = _SPORT_TYPES.get(sport_key, _SPORT_TYPES["other"])

        built_steps, _, total_secs = _build_steps(steps, start_order=1)

        payload: dict[str, Any] = {
            "workoutName": name,
            "description": description or None,
            "sportType": sport_type,
            "estimatedDurationInSecs": int(total_secs),
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": sport_type,
                    "workoutSteps": built_steps,
                }
            ],
        }

        result = client.upload_workout(payload)
        return result or {"status": "created", "workoutName": name}

    @mcp.tool()
    async def schedule_workout(
        ctx: Context,
        workout_id: int,
        date: str,
    ) -> dict[str, Any]:
        """
        Schedule an existing workout from the library onto a specific calendar date.

        Args:
            workout_id: Numeric workout ID (returned by create_workout or get_workouts).
            date: Target date in YYYY-MM-DD format.

        Returns:
            Confirmation dict with the scheduled workout entry details.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        result = client.schedule_workout(workout_id=workout_id, date_str=date)
        return result or {"status": "scheduled", "workout_id": workout_id, "date": date}

    @mcp.tool()
    async def delete_workout(
        ctx: Context,
        workout_id: int,
    ) -> dict[str, Any]:
        """
        Delete a workout from the Garmin Connect workout library.

        Args:
            workout_id: Numeric workout ID to delete.

        Returns:
            Confirmation of deletion.
        """
        client = ctx.request_context.lifespan_context["garmin"]
        result = client.delete_workout(workout_id=workout_id)
        return result or {"status": "deleted", "workout_id": workout_id}

    @mcp.tool()
    async def remove_scheduled_workouts(
        ctx: Context,
        date: str | None = None,
        dates: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        workout_id: int | None = None,
        title_contains: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Remove scheduled workouts from the Garmin calendar by exact date(s) or an inclusive date range.

        This removes calendar instances only. It does NOT delete the underlying workout
        template from your Garmin workout library.

        Args:
            date: Single target date in YYYY-MM-DD format.
            dates: Optional list of exact dates in YYYY-MM-DD format.
            start_date: Inclusive range start in YYYY-MM-DD format.
            end_date: Inclusive range end in YYYY-MM-DD format.
            workout_id: Optional filter to remove only calendar entries for a specific workout template.
            title_contains: Optional case-insensitive title substring filter.
            dry_run: When true, return the matching scheduled workouts without removing them.

        Returns:
            Dict describing the matched scheduled workouts and any removals performed.
        """
        client = ctx.request_context.lifespan_context["garmin"]

        target_dates = _resolve_target_dates(
            date=date,
            dates=dates,
            start_date=start_date,
            end_date=end_date,
        )
        target_date_strings = {value.isoformat() for value in target_dates}
        target_months = sorted({(value.year, value.month) for value in target_dates})

        matching_items: list[dict[str, Any]] = []
        for year, month in target_months:
            month_data = _get_scheduled_workouts(client, year, month)
            if isinstance(month_data, dict) and "error" in month_data:
                return month_data

            for item in month_data.get("calendarItems", []):
                if item.get("itemType") != "workout":
                    continue
                if item.get("date") not in target_date_strings:
                    continue
                if workout_id is not None and item.get("workoutId") != workout_id:
                    continue
                if title_contains and title_contains.casefold() not in str(item.get("title") or "").casefold():
                    continue
                matching_items.append(item)

        matching_items.sort(key=lambda item: (str(item.get("date") or ""), int(item.get("id") or 0)))
        matches = [_scheduled_workout_summary(item) for item in matching_items]

        if dry_run:
            return {
                "status": "dry_run",
                "matched_count": len(matches),
                "filters": {
                    "date": date,
                    "dates": dates or [],
                    "start_date": start_date,
                    "end_date": end_date,
                    "workout_id": workout_id,
                    "title_contains": title_contains,
                },
                "matches": matches,
            }

        removed: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for item in matching_items:
            scheduled_workout_id = item.get("id")
            result = garmin_call(client.unschedule_workout, scheduled_workout_id)
            if isinstance(result, dict) and "error" in result:
                errors.append(
                    {
                        **_scheduled_workout_summary(item),
                        "error": result["error"],
                    }
                )
                continue

            removed.append(_scheduled_workout_summary(item))

        status = "removed"
        if errors and removed:
            status = "partial"
        elif errors and not removed:
            status = "error"

        return {
            "status": status,
            "matched_count": len(matches),
            "removed_count": len(removed),
            "error_count": len(errors),
            "filters": {
                "date": date,
                "dates": dates or [],
                "start_date": start_date,
                "end_date": end_date,
                "workout_id": workout_id,
                "title_contains": title_contains,
            },
            "removed": removed,
            "errors": errors,
        }
