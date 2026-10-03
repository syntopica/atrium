"""One thing the doctor checked, and what it found."""

import re
from dataclasses import dataclass
from typing import Any

# A finding is `ok` when the check ran and the answer was healthy, `warn` when
# the memory still answers correctly but is drifting, and `broken` when it would
# answer from a world that no longer exists. Only `broken` fails the command:
# an operator who is warned every run stops reading the warnings.
SEVERITIES = ("ok", "warn", "broken")

# A code is a fixed machine word, never prose: `doctor --json` publishes it to
# dashboards that store and display it, and a summary can carry host names and
# paths that must not leave the machine.
CODE_PATTERN = re.compile(r"[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class Finding:
    """One check's verdict: what was looked at, how bad, and the numbers."""

    check: str
    severity: str
    summary: str
    detail: dict[str, Any]
    code: str

    def __post_init__(self) -> None:
        """Reject a severity or code outside the vocabulary the callers switch on."""
        if self.severity not in SEVERITIES:
            raise ValueError(f"unknown severity {self.severity!r}")
        if not CODE_PATTERN.fullmatch(self.code):
            raise ValueError(f"code {self.code!r} is not a fixed machine word")
