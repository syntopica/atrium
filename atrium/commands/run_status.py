"""The `status` handler of the atrium CLI."""

from pathlib import Path

from atrium.commands.print_coverage import print_coverage
from atrium.commands.print_populations import print_populations
from atrium.store.open_store import open_store
from atrium.synthesize.default_registry import default_registry


def run_status(  # noqa: PLR0913 -- the CLI surface: each argument is one flag
    index: Path,
    archive: Path,
    stamp: Path,
    registry: Path | None = None,
    *,
    coverage: bool = False,
    publish: Path | None = None,
    as_json: bool = False,
) -> int:
    """Show what the index holds -- and say loudly when it is answering stale.

    The archive sat frozen from 2026-08-27 while status printed healthy row
    counts and the index answered every query as if current. Row counts cannot
    show that; the ages below can, so they print on every status, not only in
    `doctor`.

    ``publish`` is the state directory to write ``status/refresh.json`` into,
    from the same open index, so the file and the printed lines agree.
    ``as_json`` prints that same document instead of the text report.
    """
    import time

    from atrium.doctor.archive_freshness import archive_freshness
    from atrium.doctor.newest_content_gap import newest_content_gap
    from atrium.doctor.refresh_health import refresh_health
    from atrium.recall.project_coverage import project_coverage
    from atrium.status.indexed_synthesis_episodes import indexed_synthesis_episodes
    from atrium.status.publish_json_atomically import publish_json_atomically
    from atrium.status.refresh_status import refresh_status
    from atrium.status.status_file import status_file

    connection = open_store(index, read_only=True)
    records = connection.execute("SELECT count(*) FROM records").fetchone()[0]
    providers = connection.execute(
        "SELECT provider, count(*) FROM records GROUP BY provider ORDER BY 2 DESC"
    ).fetchall()
    build = dict(connection.execute("SELECT key, value FROM build_metadata"))
    freshness = [
        archive_freshness(archive),
        refresh_health(stamp),
        newest_content_gap(connection),
    ]
    indexed_episodes = indexed_synthesis_episodes(connection)
    # Scanning every record for coverage costs ~44s against 1.1M rows, so the
    # hourly refresh does not pay for a number that moves by fractions of a
    # percent between runs. Ask for it when the question is being asked.
    project_memory = project_coverage(connection) if coverage else None
    document = None
    if publish is not None or as_json:
        document = refresh_status(
            connection,
            archive,
            stamp,
            registry if registry is not None else default_registry(),
            time.time(),
        )
    if publish is not None and document is not None:
        publish_json_atomically(status_file(publish, "refresh"), document)
    connection.close()
    if as_json:
        import json

        print(json.dumps(document, sort_keys=True))
        return 0
    print(f"  index: {index}")
    print(f"  built by: schema {build.get('schema')}, pipeline {build.get('pipeline')}")
    print(f"  records: {records:,}")
    for provider, count in providers:
        print(f"    {provider:<14} {count:>8,}")
    for finding in freshness:
        loud = {"ok": "", "warn": "  <- STALE", "broken": "  <- BROKEN"}[finding.severity]
        print(f"  {finding.summary}{loud}")
    if project_memory is not None:
        print_coverage(project_memory)
    print_populations(registry, indexed_episodes)
    return 0
