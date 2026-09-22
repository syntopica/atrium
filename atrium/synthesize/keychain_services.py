"""Name the keychain services that hold a Max account's credentials."""

import os

# One service per Claude Code profile: a heavy session may have rate-limited one
# account while another still has headroom. Extra profiles are named in
# ATRIUM_KEYCHAIN_SERVICES, colon-separated, because a profile's service name is
# local to the machine that created it.
_DEFAULT_SERVICE = "Claude Code-credentials"


def keychain_services() -> tuple[str, ...]:
    """Return the services to read, in order, defaulting to the plain profile."""
    named = tuple(
        part for part in os.environ.get("ATRIUM_KEYCHAIN_SERVICES", "").split(":") if part
    )
    return named or (_DEFAULT_SERVICE,)
