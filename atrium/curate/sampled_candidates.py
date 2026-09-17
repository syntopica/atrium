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
    working: list[tuple[str, int]] = []
    held: list[tuple[str, int]] = []
    for stratum, entries in sorted(index.items()):
        entries.sort()
        drawn = entries[: quotas[stratum]]
        # Split inside the stratum, not across the concatenation. Ranks are
        # hashes, and a small stratum's smallest ten ranks are far larger than a
        # large stratum's smallest two hundred, so a global sort puts every rare
        # stratum at the end: the first run of this sampler sent 33 of the 40
        # repeated claims into the holdout and left 7 to work with.
        cut = round(len(drawn) * size / wanted) if wanted else 0
        working.extend(drawn[:cut])
        held.extend(drawn[cut:])
    working.sort()
    held.sort()
    return (
        records_at_offsets(path, [offset for _, offset in working]),
        records_at_offsets(path, [offset for _, offset in held]),
    )
