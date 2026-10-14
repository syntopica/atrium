"""Tell the reader which retired things the answer touches, and what replaced them."""

from typing import Any

from atrium.context.names_retirement import names_retirement
from atrium.context.retirement import Retirement


def annotate_retired(
    response: dict[str, Any], mentions: dict[str, Retirement], retirements: list[Retirement]
) -> None:
    """Mark each evidence item naming a retired term, and list every retirement touched."""
    touched = [one for one in retirements if names_retirement(response["query"], one)]
    for item in response["evidence"]:
        retirement = mentions.get(item["record_id"])
        if retirement is None:
            continue
        item["retired"] = retirement.terms[0]
        if retirement not in touched:
            touched.append(retirement)
    response["retired"] = [
        {
            "terms": list(one.terms),
            "since": one.since,
            "replaced_by": one.replaced_by,
            "note": one.note,
        }
        for one in touched
    ]
