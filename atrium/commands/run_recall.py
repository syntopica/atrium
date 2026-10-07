"""The `recall` handler of the atrium CLI."""

import sys
from pathlib import Path

from atrium.store.open_store import open_store


def run_recall(index: Path, cwd: Path, limit: int, archive: Path, stamp: Path) -> int:
    """Print the recall block for the project containing ``cwd``.

    Exit status separates the two ways of printing nothing. Zero means there is
    genuinely nothing to recall -- no project here, or no episodes in it -- and
    silence is the right injection. Non-zero means recall could not answer, and
    a caller must say so rather than let a broken index read as a project with
    no history.

    A stale index breaks the silence: the session about to trust this memory is
    exactly the reader that must hear the archive stopped moving, and the empty
    block is the case where nothing else would say so.
    """
    from atrium.doctor.archive_freshness import archive_freshness
    from atrium.doctor.refresh_health import refresh_health
    from atrium.recall.project_workspace import project_workspace
    from atrium.recall.recent_episodes import recent_episodes
    from atrium.recall.render_snapshot import render_snapshot

    if not index.exists():
        print(f"no index at {index}; run `atrium ingest` first", file=sys.stderr)
        return 1
    project = project_workspace(cwd)
    if project is None:
        return 0
    connection = open_store(index, read_only=True)
    try:
        hits = recent_episodes(connection, project, limit)
    finally:
        connection.close()
    stale = [
        finding
        for finding in (archive_freshness(archive), refresh_health(stamp))
        if finding.severity != "ok"
    ]
    if stale:
        details = "; ".join(finding.summary for finding in stale)
        print(f"# atrium recall warning: memory may be stale -- {details}")
    block = render_snapshot(project, hits)
    if block:
        print(block)
    return 0
