"""Serialise one judged pair, with the decided relation winning over the model's."""

from typing import Any


def relation_row(
    left_id: str, right_id: str, score: float, relation: str, fields: dict[str, Any]
) -> dict[str, object]:
    """Return the JSONL row for one adjudicated pair.

    The model's own `relation` key is dropped rather than merged: a numeric veto
    decides what the pair may do, and spreading `fields` over the row used to
    overwrite the decided relation with the raw answer, which is why no row in
    the 191-pair run carried the veto it had been given.
    """
    return {
        **{key: fields[key] for key in sorted(fields) if key != "relation"},
        "left": left_id,
        "right": right_id,
        "similarity": round(score, 4),
        "relation": relation,
    }
