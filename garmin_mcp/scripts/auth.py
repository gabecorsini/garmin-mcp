"""
One-time authentication script for Garmin MCP.

Uses garmin-health-data's battle-tested multi-strategy login flow, which cycles
through five SSO approaches (portal+cffi, portal+requests, mobile+cffi,
mobile+requests, widget+cffi) with curl_cffi TLS impersonation to bypass
Cloudflare's bot detection.

On success, tokens are saved to:
    ~/.garminconnect/<user_id>/garmin_tokens.json

These tokens are loaded by the MCP server at startup without requiring credentials.

Usage:
    uv run garmin-mcp-auth
    uv run python -m garmin_mcp.scripts.auth
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from garmin_health_data.auth import discover_accounts, get_credentials, refresh_tokens


GARMINCONNECT_HOME = Path.home() / ".garminconnect"


def verify_tokens(token_dir: Path) -> bool:
    """Verify saved tokens work against the live Garmin API."""
    print("\nVerifying tokens against Garmin Connect API...")
    try:
        from garminconnect import Garmin

        client = Garmin()
        client.login(tokenstore=str(token_dir))
        print(f"  Connected as: {client.display_name}")
        return True
    except Exception as exc:
        print(f"  Verification failed: {exc}", file=sys.stderr)
        return False


def main() -> None:
    print("\nGarmin MCP -- Authentication Setup")
    print("=" * 40)
    print()

    # Use env vars if set, otherwise prompt interactively
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    if not (email and password):
        print("Enter your Garmin Connect credentials.")
        print("(These are used once to obtain tokens; they are not stored.)")
        print()
        email, password = get_credentials()

    try:
        refresh_tokens(
            email=email,
            password=password,
            base_token_dir=str(GARMINCONNECT_HOME),
        )
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as exc:
        print(f"\nAuthentication failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Discover the token directory that was just written
    try:
        accounts = discover_accounts(str(GARMINCONNECT_HOME))
    except Exception as exc:
        print(f"\nCould not locate saved tokens: {exc}", file=sys.stderr)
        sys.exit(1)

    # Use the first (most likely only) account
    user_id, token_dir = accounts[0]

    ok = verify_tokens(token_dir)
    if ok:
        print()
        print("Setup complete. Start the MCP server with:")
        print("  uv run python -m garmin_mcp")
        print()
        print(f"Token location: {token_dir}")
    else:
        print(
            "\nVerification failed. Tokens may be invalid.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
