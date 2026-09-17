"""The facts of one synthesis record, whatever shape the model returned."""

from typing import Any


def record_facts(record: dict[str, Any]) -> list[str]:
    """Return the record's facts as a list of strings.

    A model that answers ``"facts": "one sentence"`` instead of a list is not
    rare, and iterating that string yields characters: the first run of the
    screen reported 418,246 facts and quarantined 128,680 of them as
    ``too_short``, nearly all single letters, which is what exposed it.
    """
    facts = (record.get("output") or {}).get("facts")
    if isinstance(facts, str):
        return [facts]
    if not isinstance(facts, list):
        return []
    return [fact for fact in facts if isinstance(fact, str)]
