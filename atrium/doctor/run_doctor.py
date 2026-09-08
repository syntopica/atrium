"""Run every coherence check and report what the memory would answer from."""

from pathlib import Path

from atrium.doctor.archive_freshness import archive_freshness
from atrium.doctor.archive_schema_coherence import archive_schema_coherence
from atrium.doctor.entry_point_health import entry_point_health
from atrium.doctor.finding import Finding
from atrium.doctor.index_coverage import index_coverage
from atrium.doctor.read_archive_admissions import read_archive_admissions
from atrium.doctor.refresh_health import refresh_health
from atrium.doctor.synthesis_coherence import synthesis_coherence
from atrium.doctor.synthesis_event_membership import synthesis_event_membership
from atrium.store.open_store import open_store


def run_doctor(index: Path, archive: Path, stamp: Path, registry: Path) -> list[Finding]:
    """Check the whole chain, cheapest first.

    Order matters. A dead refresh or an unwritten archive explains every
    downstream number, so those are answered before anything reads four
    gigabytes to compare identifier sets. The entry points come first of all:
    an index nobody can reach makes every number under it academic.
    """
    findings = [entry_point_health(), archive_freshness(archive), refresh_health(stamp)]
    if not archive.exists():
        return findings
    findings.append(archive_schema_coherence(archive))

    admissions = read_archive_admissions(archive)
    connection = open_store(index, read_only=True)
    try:
        findings.append(index_coverage(connection, admissions))
    finally:
        connection.close()
    findings.append(synthesis_coherence(registry, admissions.all_ids))
    findings.append(synthesis_event_membership(archive, registry))
    return findings
