"""What one finished synthesis pass did, in counts and instants."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SynthesisPass:
    """The tallies `atrium synthesize` prints at the end of a pass."""

    producer: str
    started: float
    finished: float
    conversations: int
    synthesized: int
    skipped: int
    failed: int
    deferred: int
