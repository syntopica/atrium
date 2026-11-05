"""How much of the subscription the account has spent, as a stream-json run reports it."""

import json


def claude_stream_utilization(stdout: str) -> float | None:
    """Return the highest window utilization (0..1) any ``rate_limit_event`` names.

    The CLI reports each usage window (five-hour, seven-day) it tracks for the
    account; the fullest one is the one that walls the pass first. ``None``
    when the run reported no window.
    """
    highest: float | None = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "rate_limit_event":
            continue
        windows = (event.get("rate_limit_info") or {}).get("unifiedWindows") or {}
        for window in windows.values():
            value = window.get("utilization") if isinstance(window, dict) else None
            if isinstance(value, int | float) and (highest is None or value > highest):
                highest = float(value)
    return highest
