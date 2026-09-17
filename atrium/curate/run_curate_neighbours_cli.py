"""The `curate-neighbours` command: how much paraphrase the ledger holds."""

import json
import time

from atrium.curate.curation_directory import curation_directory
from atrium.curate.embedded_ledger import embedded_ledger
from atrium.curate.near_duplicate_pairs import near_duplicate_pairs
from atrium.curate.write_ledger import CANDIDATES
from atrium.embed.embedder import Embedder

MATRIX = "candidates.f32"
IDS = "candidate-ids.jsonl"
PAIRS = "pairs.jsonl"
_REPORTED = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.98)


def run_curate_neighbours_cli(threshold: float, neighbours: int) -> int:
    """Embed the whole candidate ledger and count its near-duplicate pairs.

    This exists because a random sample cannot measure merging: 492 claims
    drawn from 288,844 yielded 4 equivalent pairs, and both halves of a
    paraphrase live in the same project and week, so a 0.17% sample almost
    never holds both. No model is called here -- the point is the exact
    distribution over the whole corpus, which then says how many pairs are
    worth adjudicating at all.
    """
    directory = curation_directory()
    ledger = directory / CANDIDATES
    if not ledger.exists():
        print(f"  no candidate ledger at {ledger}; run `atrium curate-screen` first")
        return 1
    started = time.monotonic()
    matrix, ids = embedded_ledger(ledger, directory / MATRIX, directory / IDS, Embedder())
    print(f"  {len(ids):,} vectors in {(time.monotonic() - started) / 60:,.1f} min", flush=True)
    scanned = time.monotonic()
    pairs = near_duplicate_pairs(matrix, threshold, neighbours)
    print(f"  scanned in {(time.monotonic() - scanned) / 60:,.1f} min", flush=True)
    for floor in _REPORTED:
        if floor >= threshold:
            print(
                f"    >= {floor:.2f}  {sum(1 for _, _, score in pairs if score >= floor):,} pairs"
            )
    (directory / PAIRS).write_text(
        "".join(
            json.dumps(
                {"left": ids[left], "right": ids[right], "similarity": round(score, 4)},
                sort_keys=True,
            )
            + "\n"
            for left, right, score in pairs
        )
    )
    print(f"  pairs {directory / PAIRS}")
    return 0
