"""Group claims that every member agrees is the same claim."""


def equivalence_clusters(equivalent: list[tuple[int, int]]) -> list[tuple[int, ...]]:
    """Return clusters in which every pair was judged equivalent.

    Not connected components. One mistaken edge in a component merges two
    unrelated clusters and the mistake is invisible afterwards, so a claim
    joins a cluster only when it was judged equivalent to every member already
    in it. The cost is a merge lost when adjudication is incomplete, which is
    recoverable, instead of a merge invented, which is not.

    Greedy over the given edge order, so the caller decides precedence by
    sorting its edges -- strongest similarity first keeps the safest pairs as
    cluster seeds.
    """
    edges = {(min(a, b), max(a, b)) for a, b in equivalent}
    clusters: list[set[int]] = []
    for left, right in ((a, b) for a, b in equivalent):
        for cluster in clusters:
            if left in cluster or right in cluster:
                joining = right if left in cluster else left
                if all((min(joining, member), max(joining, member)) in edges for member in cluster):
                    cluster.add(joining)
                break
        else:
            clusters.append({left, right})
    return [tuple(sorted(cluster)) for cluster in clusters if len(cluster) > 1]
