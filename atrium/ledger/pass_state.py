"""Name what a pass's exit status means."""

# `timeout` exits 124 when it stops the pass at its time box, and 137 when the
# pass ignored the stop and `--kill-after` had to kill it.
_STATES = {0: "ok", 124: "timeout", 137: "killed"}


def pass_state(exit_code: int) -> str:
    """Return ``ok``, ``timeout``, ``killed`` or ``failed``."""
    return _STATES.get(exit_code, "failed")
