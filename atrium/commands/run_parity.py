"""The `parity` handler of the atrium CLI."""

import json
from pathlib import Path

from atrium.parity.parity_report import parity_report


def run_parity(test: Path, live: Path) -> int:
    """Print the comparison as JSON; exit 1 when the indexes differ."""
    report = parity_report(test, live)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["equal"] else 1
