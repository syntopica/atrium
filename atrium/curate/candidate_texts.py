"""Stream the ledger as (id, text) without holding it in memory."""

import json
from collections.abc import Iterator
from pathlib import Path


def candidate_texts(path: Path) -> Iterator[tuple[str, str]]:
    """Yield (candidate_id, text) for every line of a candidate ledger.

    A generator because the ledger is 200 MB of JSON: the embedding pass needs
    the texts in order and nothing else, and materialising the dictionaries
    costs several gigabytes for no gain.
    """
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            yield record["candidate_id"], record["text"]
