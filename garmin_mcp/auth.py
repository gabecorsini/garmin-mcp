"""
Garmin Connect authentication via garmin-health-data token caching.

On first use, run `garmin-mcp-auth` (or `py -m garmin_mcp.scripts.auth`) to
perform the interactive login (handles MFA) and cache OAuth tokens to
~/.garminconnect/<user_id>/garmin_tokens.json.

Subsequent runs load cached tokens silently, refreshing when needed.
"""

from __future__ import annotations

from pathlib import Path

from garminconnect import Garmin


GARMINCONNECT_HOME = str(Path.home() / ".garminconnect")


def _find_token_dir() -> str:
    """
    Locate the token directory under ~/.garminconnect/.

    garmin-health-data saves tokens to ~/.garminconnect/<user_id>/garmin_tokens.json.
    This function returns the path to the first valid per-account directory.

    Raises RuntimeError if no tokens are found.
    """
    base = Path(GARMINCONNECT_HOME)
    if not base.exists():
        raise RuntimeError(
            f"Token directory not found: {base}\n"
            "Run `garmin-mcp-auth` first to log in and cache your credentials."
        )

    # Look for numeric subdirectories (per-account layout from garmin-health-data)
    accounts = sorted(
        e for e in base.iterdir()
        if e.is_dir() and e.name.isdigit() and (e / "garmin_tokens.json").exists()
    )
    if accounts:
        return str(accounts[0])

    # Legacy fallback: token file at root level
    if (base / "garmin_tokens.json").exists():
        return str(base)

    raise RuntimeError(
        f"No token files found in {base}\n"
        "Run `garmin-mcp-auth` first to log in and cache your credentials."
    )


def get_client() -> Garmin:
    """
    Return an authenticated Garmin client.

    Loads cached DI tokens from ~/.garminconnect/<user_id>/garmin_tokens.json.
    If tokens are missing or expired beyond refresh, raises RuntimeError with
    setup instructions.
    """
    token_dir = _find_token_dir()

    try:
        client = Garmin()
        client.login(tokenstore=token_dir)
        return client
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load Garmin session from {token_dir}: {exc}\n"
            "Try running `garmin-mcp-auth` again to re-authenticate."
        ) from exc
