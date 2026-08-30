"""MCP adapter: atrium's retrieval, served to an agent over stdio."""

import os
import threading
from pathlib import Path

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from atrium.recall.project_workspace import project_workspace
from atrium.recall.recent_episodes import recent_episodes
from atrium.retrieve.hit import Hit
from atrium.retrieve.search import LANES, search
from atrium.store.open_store import open_store

# Configurable, because this server and the CLI must be able to disagree about
# which index they serve on purpose rather than by accident -- a second index at
# the default path would otherwise be served silently.
INDEX = Path(os.environ.get("ATRIUM_INDEX", Path.home() / ".atrium" / "index.sqlite3"))

# A limit is a promise about how much context the answer will spend. Left
# unbounded, one tool call can flood the agent that asked; left unchecked, a
# negative one reaches SQLite as "no limit".
MAX_LIMIT = 50

mcp = MCPServer("atrium")

# Both tools open the index read-only and neither has anything to undo, which
# is what lets a host auto-approve them. Declaring it is not decoration: a host
# that has to assume a tool writes will stop and ask before every recall.
_READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)

# Constructing the embedder costs seconds, which is most of what a one-shot
# `atrium search` spends. This process outlives a request, so it is built once
# on the first query that needs it and reused for the life of the server. Tools
# run in worker threads, so the first two concurrent searches would otherwise
# each build one and one would be thrown away after paying for it.
_embedder = None
_embedder_lock = threading.Lock()


def _resident_embedder():
    global _embedder
    with _embedder_lock:
        if _embedder is None:
            from atrium.embed.embedder import Embedder

            _embedder = Embedder()
        return _embedder


def _checked_limit(limit: int) -> int:
    if limit < 1:
        raise ValueError(f"limit must be at least 1, got {limit}")
    return min(limit, MAX_LIMIT)


def _rendered(hits: list[Hit]) -> list[dict]:
    """Return whole hits.

    Never the CLI's printed form: that truncates text to fit a terminal, and an
    agent served the truncated version has no way to see what is missing.
    """
    return [
        {
            "record_id": hit.record_id,
            "text": hit.text,
            "lane": hit.lane,
            "score": hit.score,
            "authored_at": hit.authored_at,
            "provider": hit.provider,
            "conversation_id": hit.conversation_id,
            "source_sha256": hit.source_sha256,
        }
        for hit in hits
    ]


@mcp.tool(annotations=_READ_ONLY)
def atrium_search(
    query: str, limit: int = 10, lane: str = "auto", project: str | None = None
) -> list[dict]:
    """Search the conversation archive, curated notes and synthesized episodes.

    Lanes: "auto" fuses lexical and semantic and is the right default; "words"
    is whole-word lexical alone; "substring" matches fragments inside words;
    "dense" is the semantic lane alone. Ask for "dense" when the wording of the
    question shares nothing with the wording of the answer -- fusing a blind
    lexical lane measurably buries the semantic signal.

    ``project`` is a directory: pass one to search only the work done in the
    project containing it, and leave it out to search everything. The archive
    spans unrelated clients and personal work, so a question about one of them
    is usually better asked with a project than without.
    """
    if lane not in LANES:
        raise ValueError(f"unknown lane {lane!r}; expected one of {', '.join(LANES)}")
    limit = _checked_limit(limit)
    workspace = None
    if project is not None:
        workspace = project_workspace(project)
        if workspace is None:
            raise ValueError(f"{project!r} is in no repository, so it names no project")
    connection = open_store(INDEX, read_only=True)
    try:
        embedder = _resident_embedder() if lane in ("auto", "dense") else None
        return _rendered(
            search(connection, query, limit, lane, embedder=embedder, workspace=workspace)
        )
    finally:
        connection.close()


@mcp.tool(annotations=_READ_ONLY)
def atrium_recall(cwd: str, limit: int = 12) -> list[dict]:
    """Return the newest synthesized episodes for the project containing ``cwd``.

    This is not a search: it takes no query. It answers "what has already been
    worked out in this project", which is what a session needs before it knows
    what to ask.

    Returns an empty list when ``cwd`` is in no repository: there is no project
    boundary to recall within, and answering with everything would be worse
    than answering with nothing.
    """
    limit = _checked_limit(limit)
    workspace = project_workspace(cwd)
    if workspace is None:
        return []
    connection = open_store(INDEX, read_only=True)
    try:
        return _rendered(recent_episodes(connection, workspace, limit))
    finally:
        connection.close()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
