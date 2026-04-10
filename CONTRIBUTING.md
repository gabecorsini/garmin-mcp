# Contributing to garmin-mcp

Thank you for your interest in contributing. This document covers everything you
need to get started.

## What makes a good contribution

- A new Garmin Connect tool that exposes data not yet covered
- A fix for a broken or incorrect tool
- Improved error handling or resilience
- Documentation improvements
- CI / developer experience improvements

If you're unsure whether something fits, open an issue first to discuss.

## Development setup

```bash
git clone https://github.com/gabecorsini/garmin-mcp.git
cd garmin-mcp
uv sync
uv run garmin-mcp-auth   # one-time login — writes tokens to ~/.garminconnect/
```

Verify the server starts:

```bash
uv run python -m garmin_mcp
# [garmin-mcp] Connected to Garmin Connect as: <your name>
```

## How to add a new tool

1. **Choose a module** in `garmin_mcp/tools/` or create a new one.
2. **Register the tool** as an `async def` decorated with `@mcp.tool()` inside the
   module's `register(mcp: FastMCP) -> None` function.
3. **Retrieve the client** from context:
   ```python
   client = ctx.request_context.lifespan_context["garmin"]
   ```
4. **Wrap the client call** with `garmin_call()` from `_utils.py`:
   ```python
   from garmin_mcp.tools._utils import garmin_call
   return garmin_call(client.some_method, arg1, arg2)
   ```
   This catches the three common `garminconnect` exceptions and returns a plain
   error dict instead of raising.
5. **Register the module** in `garmin_mcp/server.py` if it's new:
   ```python
   from garmin_mcp.tools import your_module
   your_module.register(mcp)
   ```
6. **Update the tool tables** in `README.md` and increment the tool count in the
   description at the top.

> **Note:** `write.py` intentionally does not use `garmin_call()` because write
> methods have different error shapes. Check that file before assuming the pattern
> is universal.

## Testing without Garmin credentials

CI runs on every PR and validates three things without needing a live account:

- **Dependency install** — `uv sync` resolves the lockfile cleanly
- **Syntax check** — `python -m py_compile` on every `.py` file
- **Import check** — every module imports without error

To run the same checks locally:

```bash
uv sync
find . -name "*.py" -not -path "./.venv/*" -exec python -m py_compile {} +
uv run python -c "import garmin_mcp.server; print('OK')"
```

Live tool testing requires a real Garmin account. If you're adding or modifying a
tool, test it manually against your own account before submitting a PR.

## Commit style

Use short, imperative subject lines. Prefix with a type where it helps:

```
feat: add get_training_load tool
fix: handle missing VO2 max data on older devices
chore: update dependencies
docs: clarify token storage in README
```

No strict enforcement — just keep messages clear enough to scan in a log.

## Pull request checklist

- CI passes (all three Python versions)
- New tools are documented in `README.md`
- Tool count in the README header is updated if you added tools
- No credentials, token files, or personal data in the diff

## What not to contribute

- Re-adding `get_workout_schedule` — it was intentionally removed
- A replacement for the `garmin-health-data` auth flow — the curl_cffi TLS
  impersonation it uses is necessary to bypass Cloudflare; a plain `requests`
  login will be blocked
- Telemetry, analytics, or any outbound calls to non-Garmin servers
