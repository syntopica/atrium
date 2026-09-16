"""What `record-session` reports: an exit code and one line each way."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RecordOutcome:
    """``status`` 0 written or consumed, 2 invalid payload, 3 no usable checkpoint."""

    status: int
    stdout: str = ""
    stderr: str = ""
