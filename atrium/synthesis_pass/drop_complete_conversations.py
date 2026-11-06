"""Leave out of a pass the conversations already finished at their content."""

from pathlib import Path
from typing import Any

from atrium.synthesis_pass.is_complete import is_complete


def drop_complete_conversations(
    conversations: list[dict[str, Any]], holding: set[str], registry: Path
) -> list[dict[str, Any]]:
    """Keep the rest; one holding worker results is kept, so they get collected."""
    kept = [c for c in conversations if c["id"] in holding or not is_complete(registry, c)]
    if len(kept) < len(conversations):
        print(
            f"  {len(conversations) - len(kept)} conversations complete at their content; not walked"
        )
    return kept
