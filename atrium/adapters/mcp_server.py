"""MCP adapter: atrium's retrieval, served to an agent over stdio."""

from pathlib import Path

from mcp.server import MCPServer

from atrium.recall.project_workspace import project_workspace
from atrium.recall.recent_episodes import recent_episodes
from atrium.retrieve.hit import Hit
from atrium.retrieve.search import LANES, search
from atrium.store.open_store import open_store

DEFAULT_INDEX = Path.home() / ".atrium" / "index.sqlite3"

mcp = MCPServer("atrium")

# Constructing the embedder costs seconds, which is most of what a one-shot
# `atrium search` spends. This process outlives a request, so it is built once
# on the first query that needs it and reused for the life of the server.
_embedder = None


def _resident_embedder():
    global _embedder
    if _embedder is None:
        from atrium.embed.embedder import Embedder

        _embedder = Embedder()
    return _embedder


def _rendered(hits: list[Hit]) -> list[dict]:
    """Return whole hits.

    Never the CLI's printed form: that truncates text to fit a terminal, and an
    agent served the truncated version has no way to see what is missing.
    """
    return [
        {
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


@mcp.tool()
def atrium_search(query: str, limit: int = 10, lane: str = "auto") -> list[dict]:
    """Search the conversation archive, curated notes and synthesized episodes.

    Lanes: "auto" fuses lexical and semantic and is the right default; "words"
    is whole-word lexical alone; "substring" matches fragments inside words;
    "dense" is the semantic lane alone. Ask for "dense" when the wording of the
    question shares nothing with the wording of the answer -- fusing a blind
    lexical lane measurably buries the semantic signal.
    """
    if lane not in LANES:
        raise ValueError(f"unknown lane {lane!r}; expected one of {', '.join(LANES)}")
    connection = open_store(DEFAULT_INDEX, read_only=True)
    try:
        embedder = _resident_embedder() if lane in ("auto", "dense") else None
        return _rendered(search(connection, query, limit, lane, embedder=embedder))
    finally:
        connection.close()


@mcp.tool()
def atrium_recall(cwd: str, limit: int = 12) -> list[dict]:
    """Return the newest synthesized episodes for the project containing ``cwd``.

    This is not a search: it takes no query. It answers "what has already been
    worked out in this project", which is what a session needs before it knows
    what to ask.
    """
    connection = open_store(DEFAULT_INDEX, read_only=True)
    try:
        return _rendered(recent_episodes(connection, project_workspace(cwd), limit))
    finally:
        connection.close()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
