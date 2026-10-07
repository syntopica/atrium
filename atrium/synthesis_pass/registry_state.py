"""What the registry already holds, as one pass needs to read it."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegistryState:
    """``recorded_revisions`` are (conversation, revision) pairs some record synthesized."""

    done_episodes: set[str]
    covered: set[str]
    recorded_results: set[str]
    recorded_revisions: set[tuple[str, str]]
