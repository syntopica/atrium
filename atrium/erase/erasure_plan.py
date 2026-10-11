"""What Atrium takes from an applied scribe erasure plan."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ErasurePlan:
    """The erased conversation ids and the generation that no longer holds them."""

    conversation_ids: tuple[str, ...]
    to_generation_id: str
