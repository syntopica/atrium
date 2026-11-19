"""Pick the terms of a long query that are worth matching."""


def rarest_terms(frequencies: dict[str, int], limit: int) -> list[str]:
    """Return the ``limit`` least frequent indexed terms, in their original order.

    A term no record holds matches nothing, so it is dropped before the cut
    rather than spending one of the places. Ties keep the earlier term.
    """
    indexed = [term for term, frequency in frequencies.items() if frequency > 0]
    kept = set(sorted(indexed, key=frequencies.__getitem__)[:limit])
    return [term for term in indexed if term in kept]
