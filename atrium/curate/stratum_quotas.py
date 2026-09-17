"""How many candidates each stratum contributes to a sample."""

MINIMUM = 10


def stratum_quotas(sizes: dict[str, int], wanted: int, minimum: int = MINIMUM) -> dict[str, int]:
    """Proportional allocation over ``sizes``, with a floor for the small strata.

    Pure proportional allocation is representative and nearly useless here:
    claims stated by more than one episode are 1.0% of the ledger, so a sample
    of 600 would hold six of them, and they are exactly the population the
    merge stage has to be measured on. The floor buys coverage at the cost of
    representativeness, so any rate measured over the sample has to be
    reweighted by stratum before it is claimed of the corpus.
    """
    total = sum(sizes.values())
    if total == 0:
        return {}
    quotas = {
        stratum: min(size, max(minimum, wanted * size // total)) for stratum, size in sizes.items()
    }
    order = sorted(sizes, key=lambda stratum: (-sizes[stratum], stratum))
    while sum(quotas.values()) > wanted:
        shrank = False
        for stratum in order:
            if quotas[stratum] > minimum and sum(quotas.values()) > wanted:
                quotas[stratum] -= 1
                shrank = True
        if not shrank:
            break
    while sum(quotas.values()) < wanted:
        grew = False
        for stratum in order:
            if quotas[stratum] < sizes[stratum] and sum(quotas.values()) < wanted:
                quotas[stratum] += 1
                grew = True
        if not grew:
            break
    return quotas
