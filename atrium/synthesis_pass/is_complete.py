"""Whether a conversation's current content was already fully synthesized."""

from pathlib import Path
from typing import Any

from atrium.synthesize.complete_marker import complete_marker


def is_complete(registry: Path, conversation: dict[str, Any]) -> bool:
    """True when a pass finished this content without leaving an episode pending."""
    marker = complete_marker(registry, conversation)
    return marker is not None and marker.exists()
