"""The curation candidates screened from erased conversations."""

from collections.abc import Collection
from pathlib import Path

from atrium.curate.jsonl_rows import jsonl_rows
from atrium.curate.write_ledger import CANDIDATES, QUARANTINE


def erased_curation_candidates(curation: Path, conversation_ids: Collection[str]) -> list[str]:
    """Return the ids of candidates any of whose sources was erased.

    Reported, not removed: the candidate ledger is aligned row for row with its
    embedded matrix and every later curation file keys on these ids, so
    dropping lines here would corrupt the rest. The report names what a
    curation rebuild has to drop.
    """
    found = []
    for name in (CANDIDATES, QUARANTINE):
        for row in jsonl_rows(curation / name):
            sources = row.get("sources") or []
            if any(source.get("conversation_id") in conversation_ids for source in sources):
                found.append(str(row.get("candidate_id")))
    return found
