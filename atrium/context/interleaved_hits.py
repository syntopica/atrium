"""The order the reranker spends its budget in: one history hit, then one note."""

from atrium.retrieve.hit import Hit


def interleaved_hits(history: list[Hit], notes: list[Hit]) -> list[Hit]:
    """Alternate the two fused populations, best first in each."""
    hits: list[Hit] = []
    for position in range(max(len(history), len(notes))):
        hits.extend(
            population[position] for population in (history, notes) if position < len(population)
        )
    return hits
