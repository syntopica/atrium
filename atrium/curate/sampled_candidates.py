"""Draw a stratified sample of candidates from the stage-one ledger."""

import json
from pathlib import Path
from typing import Any

from atrium.curate.candidate_stratum import candidate_stratum
from atrium.curate.records_at_offsets import records_at_offsets
from atrium.curate.sample_rank import sample_rank
from atrium.curate.stratum_quotas import stratum_quotas


def sampled_candidates(
    path: Path, size: int, holdout: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(working, holdout)`` samples, disjoint and deterministic.

    Read in two passes because the ledger is hundreds of megabytes: the first
    keeps only a rank, a stratum and a byte offset per line, the second reads
    back just the lines drawn. Allocation is proportional to stratum size, and
    the holdout is drawn from the same ordering immediately after the working
    set so neither is biased against the other.
    """
    index: dict[str, list[tuple[str, int]]] = {}
    with path.open("rb") as handle:
        offset = 0
        for line in handle:
            record = json.loads(line)
            index.setdefault(candidate_stratum(record), []).append(
                (sample_rank(record["candidate_id"]), offset)
            )
            offset += len(line)
    total = sum(len(entries) for entries in index.values())
    wanted = min(size + holdout, total)
    quotas = stratum_quotas({stratum: len(entries) for stratum, entries in index.items()}, wanted)
    drawn: list[tuple[str, int]] = []
    for stratum, entries in index.items():
        entries.sort()
        drawn.extend(entries[: quotas[stratum]])
    drawn.sort()
    records = records_at_offsets(path, [offset for _, offset in drawn])
    split = min(size, len(records))
    return records[:split], records[split:]
