"""One thing the doctor checked, and what it found."""

from dataclasses import dataclass

# A finding is `ok` when the check ran and the answer was healthy, `warn` when
# the memory still answers correctly but is drifting, and `broken` when it would
# answer from a world that no longer exists. Only `broken` fails the command:
# an operator who is warned every run stops reading the warnings.
SEVERITIES = ("ok", "warn", "broken")


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str
    summary: str
    detail: dict

    def __post_init__(self):
        if self.severity not in SEVERITIES:
            raise ValueError(f"unknown severity {self.severity!r}")
