"""The `search` handler of the atrium CLI."""

from pathlib import Path

from atrium.session.redact_sensitive_text import redact_sensitive_text
from atrium.store.open_store import open_store
from atrium.store.read_record_hosts import read_record_hosts


def run_search(index: Path, query: str, limit: int, lane: str, project: Path | None = None) -> int:
    """Print the ranked hits for ``query``, optionally scoped to a project."""
    from atrium.recall.project_workspace import project_workspace
    from atrium.retrieve.search import search

    workspace = None
    if project is not None:
        workspace = project_workspace(project)
        if workspace is None:
            print(f"  {project} is in no repository, so it names no project to search")
            return 1
    connection = open_store(index, read_only=True)
    exhausted: set[str] = set()
    hits = search(connection, query, limit, lane, workspace=workspace, exhausted=exhausted)
    hosts = read_record_hosts(connection, (hit.record_id for hit in hits))
    connection.close()
    if exhausted:
        # "No matches" and "ran out of time" are the same empty list, and only
        # one of them means the index does not hold this (raised by review).
        print("  the word lane ran out of its time budget; results may be incomplete")
    if not hits:
        print("  no matches")
        return 0
    for position, hit in enumerate(hits, start=1):
        stamp = (hit.authored_at or "")[:10]
        origin = "  UNTRUSTED THIRD-PARTY TEXT" if hit.role == "source" else ""
        print(
            f"\n  [{position}] {hit.provider} {stamp}  "
            f"score={hit.score:.3f} lane={hit.lane}{origin}"
        )
        print(f"      {redact_sensitive_text(hit.text)[:200].strip()}")
        print(f"      source: {hit.source_sha256[:12]} conversation: {hit.conversation_id[:12]}")
        if hit.record_id in hosts:
            print(f"      observed hosts: {hosts[hit.record_id]!r}")
    return 0
