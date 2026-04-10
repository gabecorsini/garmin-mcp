# garmin-mcp

Personal MCP server for interacting with your Garmin Connect data.

Exposes **62 tools** across 11 domains — activities, health, body composition, training,
workouts, nutrition, profile, extras, stats, write, and workout write — via the
[Model Context Protocol](https://modelcontextprotocol.io/) over stdio transport.
Works with Claude Desktop, VS Code / GitHub Copilot, Cursor, OpenCode, and any other
MCP-compatible AI client.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://github.com/gabecorsini/garmin-mcp/actions/workflows/ci.yml/badge.svg)

---

## Security & credentials

> **Read this before you do anything else.**

**Your Garmin email and password are used exactly once** — during the one-time
`garmin-mcp-auth` setup step — to authenticate with Garmin's servers over HTTPS.
They are **never written to disk, never logged, and never stored anywhere by this
software.**

What _is_ stored afterward is a small OAuth token file managed by the
`garminconnect` library:

```
~/.garminconnect/<user_id>/garmin_tokens.json
```

That file contains exactly three fields:

| Field | What it is |
|---|---|
| `di_token` | Short-lived access token |
| `di_refresh_token` | Refresh token |
| `di_client_id` | Garmin client identifier |

No email address. No password. No display name. No health data. The file lives
**outside your project folder** and cannot accidentally be committed to git.

This repo contains no hardcoded credentials, no telemetry, and no outbound
network calls except directly to Garmin Connect's own servers.

---

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- A Garmin Connect account

---

## Setup

### 1. Install uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://astral.sh/uv/install.ps1 -UseBasicParsing).Content | powershell -c -
```

### 2. Clone and install dependencies

```bash
git clone https://github.com/gabecorsini/garmin-mcp.git
cd garmin-mcp
uv sync
```

### 3. Authenticate with Garmin Connect (one-time)

```bash
uv run garmin-mcp-auth
```

You will be prompted for your Garmin email, password, and MFA code (if enabled).
Tokens are saved to `~/.garminconnect/<user_id>/garmin_tokens.json` and refreshed
automatically on subsequent runs.

### 4. Verify the server starts

```bash
uv run python -m garmin_mcp
```

You should see: `[garmin-mcp] Connected to Garmin Connect as: <your display name>`

Press Ctrl+C to stop.

---

## MCP client configuration

Replace `/absolute/path/to/garmin-mcp` (or the Windows equivalent) with the actual
path to your cloned repo in every snippet below.

### Claude Desktop

Config file locations:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "garmin": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/garmin-mcp",
        "python",
        "-m",
        "garmin_mcp"
      ]
    }
  }
}
```

### VS Code / GitHub Copilot

VS Code uses a **different key** (`"servers"`, not `"mcpServers"`).

**Workspace config** — create `.vscode/mcp.json` in your project:

```json
{
  "servers": {
    "garmin": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/garmin-mcp",
        "python",
        "-m",
        "garmin_mcp"
      ]
    }
  }
}
```

**User profile config** — open the Command Palette, run
`MCP: Open User Configuration`, and add the same block.

### Cursor

Global config file: `~/.cursor/mcp.json`  
Project-level config file: `.cursor/mcp.json`

```json
{
  "mcpServers": {
    "garmin": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/garmin-mcp",
        "python",
        "-m",
        "garmin_mcp"
      ]
    }
  }
}
```

### OpenCode

Config file: `~/.config/opencode/opencode.json`

OpenCode requires the `command` to be an **array** (not a string + args object).
Use the full path to your `uv` executable.

```json
{
  "mcpServers": {
    "garmin": {
      "command": [
        "/path/to/uv",
        "run",
        "--directory",
        "/absolute/path/to/garmin-mcp",
        "python",
        "-m",
        "garmin_mcp"
      ]
    }
  }
}
```

Find your `uv` path with `which uv` (macOS/Linux) or `(Get-Command uv).Source` (Windows PowerShell).

---

## OpenCode agent

A ready-made agent definition is provided at
[`agents/garmin.md`](agents/garmin.md). Copy it to your OpenCode agents folder:

```bash
# macOS / Linux
cp agents/garmin.md ~/.config/opencode/agents/garmin.md

# Windows (PowerShell)
Copy-Item agents\garmin.md "$env:USERPROFILE\.config\opencode\agents\garmin.md"
```

Once installed, OpenCode will load the Garmin-specific context and guidance
automatically when you start a conversation with the `garmin` agent. The agent
knows all 62 tool names, understands when data might not be available (older
devices, non-running activities, etc.), and provides examples for common queries.

---

## Available tools

### Activities (9)

| Tool | Description |
|---|---|
| `get_activities` | Recent activities with pagination and optional type filter |
| `get_activity_detail` | Full detail for a specific activity by ID |
| `get_activity_hr_zones` | HR zone breakdown for an activity |
| `get_activities_by_date` | Activities within a date range |
| `get_activity_splits` | Per-split pace and HR data |
| `get_activity_typed_splits` | Typed splits (auto laps, manual laps, intervals) |
| `get_personal_records` | All-time personal records |
| `get_activity_count` | Total activity count |
| `get_last_activity` | Most recent activity summary |

### Health & Wellness (13)

| Tool | Description |
|---|---|
| `get_sleep_data` | Sleep stages, score, SpO2, respiration |
| `get_hrv_data` | HRV nightly average, status, and baseline |
| `get_daily_stress` | Stress level breakdown by day |
| `get_body_battery` | Body Battery charged/drained over a date range |
| `get_daily_steps` | Step counts and goals over a date range |
| `get_heart_rate` | Daily HR summary (resting, min, max, avg) |
| `get_resting_heart_rate` | Resting heart rate trend over a date range |
| `get_respiration_data` | Breathing rate summary |
| `get_spo2_data` | Blood oxygen saturation |
| `get_intensity_minutes` | Moderate and vigorous intensity minutes |
| `get_floors` | Floors climbed |
| `get_hydration` | Daily hydration log |
| `get_daily_summary` | Overall daily wellness summary |

### Body Composition (3)

| Tool | Description |
|---|---|
| `get_body_composition` | Weight, BMI, body fat, muscle mass |
| `get_weight_history` | Weight log entries over a date range |
| `get_weight_stats` | Aggregated weight stats (avg / min / max) |

### Training & Performance (8)

| Tool | Description |
|---|---|
| `get_training_status` | Productive / Maintaining / Overreaching status |
| `get_training_readiness` | 0–100 readiness score with contributing factors |
| `get_vo2max` | VO2 max estimate and fitness age |
| `get_race_predictions` | Predicted 5K / 10K / half marathon / marathon times |
| `get_hill_score` | Hill climbing efficiency score |
| `get_endurance_score` | Aerobic endurance score |
| `get_running_tolerance` | Running load tolerance and injury risk signal |
| `get_fitness_stats` | Aggregate training load and aerobic/anaerobic effect |

### Workouts (2)

| Tool | Description |
|---|---|
| `get_workouts` | Saved workout library |
| `get_workout_detail` | Full workout definition with steps and targets |

### Nutrition (3)

| Tool | Description |
|---|---|
| `get_nutrition_summary` | Daily macro and calorie totals |
| `get_food_logs` | Individual food log entries by meal |
| `get_nutrition_settings` | Configured nutrition goals |

### Profile & Devices (7)

| Tool | Description |
|---|---|
| `get_user_profile` | Account profile info |
| `get_user_settings` | Unit preferences and HR zone definitions |
| `get_devices` | All registered Garmin devices |
| `get_device_settings` | Settings for a specific device |
| `get_gear` | Registered gear (shoes, bikes, etc.) |
| `get_earned_badges` | Earned badges and achievements |
| `get_primary_training_device` | Primary training device info |

### Extras (6)

| Tool | Description |
|---|---|
| `get_activity_exercise_sets` | Exercise sets for a strength training activity |
| `get_activity_weather` | Weather conditions recorded during an activity |
| `get_body_battery_events` | Body Battery charge and drain events for a day |
| `get_morning_training_readiness` | Morning Report readiness score |
| `get_lactate_threshold` | Lactate threshold HR, pace, and power |
| `get_fitnessage_data` | Garmin Fitness Age for a specific date |

### Stats (5)

| Tool | Description |
|---|---|
| `get_weekly_steps` | Weekly step count totals over a number of weeks |
| `get_weekly_stress` | Weekly average stress levels over a number of weeks |
| `get_goals` | Active, completed, or archived Garmin Connect goals |
| `get_progress_summary` | Aggregated training progress by metric over a date range |
| `get_cycling_ftp` | Current cycling Functional Threshold Power (FTP) estimate |

### Write — Health (3)

| Tool | Description |
|---|---|
| `log_weight` | Log a body weight measurement |
| `log_hydration` | Log a water intake entry |
| `upload_activity` | Upload a FIT, TCX, or GPX activity file |

### Write — Workouts (3)

| Tool | Description |
|---|---|
| `create_workout` | Create a structured workout in the Garmin library |
| `schedule_workout` | Schedule a saved workout onto a calendar date |
| `delete_workout` | Delete a workout from the library |

---

## Notes

- **Unofficial API:** This server uses the reverse-engineered Garmin Connect API
  via [`python-garminconnect`](https://github.com/cyberjunky/python-garminconnect)
  (MIT) and [`garmin-health-data`](https://github.com/diegoscarabelli/garmin-health-data)
  (Apache 2.0). Garmin does not provide an official public API. Use at your own risk.
- **Garmin ToS:** Automated access to Garmin Connect is a gray area. This tool is
  intended for personal, non-commercial use only. Do not use it in ways that could
  disrupt Garmin's services.
- **Rate limits:** Garmin may throttle or block excessive API calls. Avoid tight
  loops over large date ranges.
- **Token refresh:** Tokens are refreshed automatically. If authentication fails
  after an extended period, re-run `garmin-mcp-auth`.
- **Data availability:** Not all tools return data for all devices or activity types.
  Metrics like VO2 max, race predictions, lactate threshold, and HRV require a
  compatible Garmin device (e.g. Forerunner, Fenix, Venu series).

---

## License

[MIT](LICENSE) — Gabe Corsini, 2026
