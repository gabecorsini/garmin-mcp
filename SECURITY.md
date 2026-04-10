# Security Policy

## Supported versions

Only the latest version on `main` is actively maintained.

## Credential and data safety

This project is designed so that **no credentials or personal health data ever
leave your machine** except in direct API calls to Garmin Connect's own servers.

- Your Garmin email and password are used once during `garmin-mcp-auth` and are
  never written to disk.
- The only file written to disk is an OAuth token cache at
  `~/.garminconnect/<user_id>/garmin_tokens.json`, which contains three fields:
  `di_token`, `di_refresh_token`, and `di_client_id`. No personal data.
- The repo contains no hardcoded credentials and no telemetry.

If you believe a change in this repo could expose user credentials or health data,
please report it privately rather than opening a public issue.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report privately via GitHub's built-in security advisory feature:

1. Go to https://github.com/gabecorsini/garmin-mcp/security/advisories
2. Click **"Report a vulnerability"**
3. Describe the issue, steps to reproduce, and potential impact

You can expect an acknowledgment within a few days. This is a personal open source
project maintained by one person, so response times may vary.

## Scope

In scope:
- Credential or token exposure through code changes
- Unintended outbound network calls to third-party servers
- Dependency vulnerabilities with a plausible exploit path in this project

Out of scope:
- Garmin Connect's own API security
- Issues requiring physical access to the user's machine
- Rate limiting or ToS compliance (these are usage concerns, not security bugs)
