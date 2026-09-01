"""Which record of each episode the index serves, by active-recipe priority."""

from collections.abc import Iterable


def choose_served_records(records: Iterable[dict], priority: list[str]) -> dict[str, dict]:
    """Return one record per episode, the highest-priority model winning.

    A model absent from the priority list ranks last rather than being
    dropped: an episode only that population covers is still served, because
    dropping it is how 3,686 already-paid-for episodes silently vanished from
    the index on 2026-08-30.
    """
    rank = {model: position for position, model in enumerate(priority)}
    chosen: dict[str, dict] = {}
    for record in records:
        episode = record["episode_id"]
        record_rank = rank.get(record.get("model_requested"), len(priority))
        best = chosen.get(episode)
        if best is None or record_rank < rank.get(best.get("model_requested"), len(priority)):
            chosen[episode] = record
    return chosen
