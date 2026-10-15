"""The `atrium file-context` command: what this project concluded about one file."""

import json
from pathlib import Path

from atrium.context.read_supersessions import read_supersessions
from atrium.recall.file_episodes import file_episodes
from atrium.recall.file_phrase import file_phrase
from atrium.recall.project_workspace import project_workspace
from atrium.recall.repository_root import repository_root
from atrium.store.open_store import open_store


def run_file_context_cli(index: Path, path: Path, limit: int) -> int:
    """Print JSON with the episodes naming ``path``; empty outside a project.

    The file is resolved against its own repository, so the answer is the
    project's memory of the file whatever directory the caller stands in. An
    episode a later statement replaced carries the mark, as in context, since
    the correction need not name the file and so may not be among them.
    """
    resolved = path.expanduser().resolve()
    root = repository_root(resolved.parent)
    workspace = project_workspace(resolved.parent)
    phrase = (
        file_phrase(resolved.relative_to(root).as_posix())
        if root is not None and workspace
        else None
    )
    episodes = []
    if phrase is not None and workspace is not None:
        connection = open_store(index, read_only=True)
        try:
            hits = file_episodes(connection, workspace, phrase, limit)
            marks = read_supersessions(connection, [hit.record_id for hit in hits])
            episodes = [
                {
                    "record_id": hit.record_id,
                    "conversation_id": hit.conversation_id,
                    "authored_at": hit.authored_at,
                    "text": hit.text,
                    "superseded_by": marks[hit.record_id].superseded_by
                    if hit.record_id in marks
                    else None,
                    "superseded_at": marks[hit.record_id].at if hit.record_id in marks else None,
                }
                for hit in hits
            ]
        finally:
            connection.close()
    print(json.dumps({"workspace": workspace, "phrase": phrase, "episodes": episodes}))
    return 0
