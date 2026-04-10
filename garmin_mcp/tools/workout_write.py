"""
Workout write tools — create structured workouts and push them to Garmin Connect.

The create_workout tool accepts a high-level workout description using a step-based
schema that the Garmin agent can populate directly from its recommendations. Steps
support HR zones, pace ranges, and time/distance end conditions. Repeat blocks are
supported for intervals.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP, Context


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
