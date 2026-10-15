"""What replaced one superseded record, and when."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Supersession:
    """``superseded_by`` is the record id of the statement that replaced it."""

    superseded_by: str
    at: str | None
