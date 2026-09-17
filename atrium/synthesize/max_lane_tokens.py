"""Read every Max account's OAuth access token from the macOS keychain."""

import json
import subprocess
import time

# One keychain service per Claude Code profile. The same three the
# project-after/wide-project Max-lane scripts rotate through: a heavy session may
# have rate-limited one account while another still has headroom.
_SERVICES = (
    "Claude Code-credentials",
    "Claude Code-credentials-36d7ba4b",
    "Claude Code-credentials-63a1365a",
)


def max_lane_tokens() -> list[str]:
    """Return every live access token, in service order.

    Expired or malformed keychain payloads are skipped rather than returned:
    a dead token would surface downstream as a 401 indistinguishable from a
    revoked account. Raises only when no account has a live token at all.
    """
    tokens: list[str] = []
    for service in _SERVICES:
        try:
            raw = subprocess.run(
                ["security", "find-generic-password", "-s", service, "-w"],
                capture_output=True,
                check=True,
                text=True,
            ).stdout.strip()
            credentials = json.loads(raw).get("claudeAiOauth") or {}
            token = credentials.get("accessToken")
            expires_at = credentials.get("expiresAt")
            live = isinstance(expires_at, int | float) and expires_at > time.time() * 1000
            if isinstance(token, str) and live:
                tokens.append(token)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue
    if not tokens:
        raise RuntimeError("no live Max OAuth token in the keychain")
    return tokens
