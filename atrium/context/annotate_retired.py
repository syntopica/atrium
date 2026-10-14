"""Tell the reader which retired things the answer touches, and what replaced them."""

from collections.abc import Callable, Mapping
from typing import Any

from atrium.context.names_retirement import names_retirement
from atrium.context.retirement import Retirement


def annotate_retired(
    response: dict[str, Any],
    mentions: dict[str, Retirement],
    retirements: list[Retirement],
    forgotten: Callable[[], Mapping[str, int]],
) -> None:
    """Mark each evidence item naming a retired term, and list every retirement touched.

    A question naming a retired term may be after records the forget ledger
    keeps out, so its entry says how many and how to bring them back.
    ``forgotten`` is only called then: it reads the ledger, and most questions
    name nothing retired.
    """
    asked = [one for one in retirements if names_retirement(response["query"], one)]
    touched = list(asked)
    counts = forgotten() if asked else {}
    for item in response["evidence"]:
        retirement = mentions.get(item["record_id"])
        if retirement is None:
            continue
        item["retired"] = retirement.terms[0]
        if retirement not in touched:
            touched.append(retirement)
    response["retired"] = []
    for one in touched:
        entry: dict[str, Any] = {
            "terms": list(one.terms),
            "since": one.since,
            "replaced_by": one.replaced_by,
            "note": one.note,
        }
        if counts.get(one.terms[0]):
            entry["forgotten"] = counts[one.terms[0]]
            entry["restore"] = f"atrium forget --restore retired:{one.terms[0]} --apply"
        response["retired"].append(entry)
