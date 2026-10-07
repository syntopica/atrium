"""Narrow conversations to one stored workspace."""

from typing import Any

from atrium.ingest.workspace_aliases import workspace_aliases


def conversations_in_workspace(
    conversations: list[dict[str, Any]], target: str
) -> list[dict[str, Any]]:
    """Keep the conversations whose canonical workspace matches ``target``."""
    from atrium.ingest.canonical_workspace import canonical_workspace
    from atrium.recall.workspace_matches import workspace_matches

    # The same aliases the ingest applies, or this filter would miss exactly
    # the renamed history that makes a project whole: project-after's first
    # month is archived under `p/project-before`.
    aliases = workspace_aliases()
    return [
        conversation
        for conversation in conversations
        if workspace_matches(
            canonical_workspace(
                conversation.get("workspace"),
                aliases=aliases,
                started_at=conversation.get("startedAt"),
            ),
            target,
        )
    ]
