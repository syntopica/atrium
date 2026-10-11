"""Render bounded lane usage status."""

import json
from pathlib import Path

from atrium.telemetry.aggregate_lane_usage import aggregate_lane_usage


def run_lane_status(state: Path, days: int, as_json: bool) -> int:
    """Show measured usage with explicit coverage and error counts."""
    result = aggregate_lane_usage(state, days)
    if as_json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            f"Lane usage {result['window_start']} to {result['window_end']}: {result['coverage']}"
        )
        print(f"Events: {result['events']} (lower bound: {result['lower_bound']})")
        print(f"First: {result['first'] or 'none'}; last: {result['last'] or 'none'}")
        for lane, count in result["lanes"].items():
            print(f"  {lane}: {count}")
        print(f"Malformed lines: {result['malformed_lines']}")
        print(f"Unreadable files: {', '.join(result['unreadable_files']) or 'none'}")
    return 0
