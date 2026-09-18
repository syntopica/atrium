"""The `curate-cluster` command: stage three's merge and contradiction pass."""

import json
import time

from atrium.curate.claim_pairs import claim_pairs
from atrium.curate.claims_ledger_path import claims_ledger_path
from atrium.curate.curation_directory import curation_directory
from atrium.curate.equivalence_clusters import equivalence_clusters
from atrium.curate.pair_relation import pair_relation
from atrium.curate.publishable_claims import publishable_claims
from atrium.curate.relation_row import relation_row
from atrium.curate.time_separated_conflict import time_separated_conflict
from atrium.embed.embedder import Embedder
from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL

CLUSTERS = "clusters.jsonl"
CONTRADICTIONS = "contradictions.jsonl"
RELATIONS = "relations.jsonl"


def run_curate_cluster_cli(
    threshold: float, neighbours: int, budget: int, model: str = LOCAL_DEFAULT_MODEL
) -> int:
    """Adjudicate the near pairs of the claim ledger and write what it found.

    Nothing here proposes a page yet: this pass establishes which claims are
    one claim, which disagree, and what that costs, because the merge rate is
    what decides whether a full pass over 288,844 claims is worth scheduling.
    """
    directory = curation_directory()
    claims_path = claims_ledger_path(directory)
    if not claims_path.exists():
        print(f"  no claim ledger at {claims_path}; run `atrium curate-extract` first")
        return 1
    claims, dropped = publishable_claims(claims_path)
    pairs = claim_pairs([claim["text"] for claim in claims], Embedder(), threshold, neighbours)
    print(f"  {len(claims):,} claims, {sum(dropped.values()):,} dropped as debris {dropped}")
    print(f"  {len(pairs):,} pairs above {threshold} (budget {budget})", flush=True)
    started = time.monotonic()
    relations: list[dict[str, object]] = []
    equivalent: list[tuple[int, int]] = []
    for done, (left, right, score) in enumerate(pairs[:budget], start=1):
        relation, fields = pair_relation(claims[left]["text"], claims[right]["text"], model=model)
        if relation == "conflicting" and time_separated_conflict(
            str(claims[left]["first_seen"]),
            str(claims[left]["last_seen"]),
            str(claims[right]["first_seen"]),
            str(claims[right]["last_seen"]),
        ):
            # Same thing, two moments: supersession or growth, not disagreement.
            relation = "superseded"
        relations.append(
            relation_row(
                str(claims[left]["candidate_id"]),
                str(claims[right]["candidate_id"]),
                score,
                relation,
                fields,
            )
        )
        if relation == "equivalent" and "merge_blocked" not in fields:
            equivalent.append((left, right))
        if done % 25 == 0 or done == min(len(pairs), budget):
            rate = done / max(time.monotonic() - started, 1e-9)
            print(f"  [{done}/{min(len(pairs), budget)}] {rate * 3600:,.0f} pairs/hour", flush=True)
    clusters = equivalence_clusters(equivalent)
    (directory / RELATIONS).write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in relations)
    )
    (directory / CLUSTERS).write_text(
        "".join(
            json.dumps(
                {
                    "members": [claims[index]["candidate_id"] for index in cluster],
                    "texts": [claims[index]["text"] for index in cluster],
                    "projects": sorted(
                        {claims[index]["project"] for index in cluster if claims[index]["project"]}
                    ),
                    "first_seen": min(claims[index]["first_seen"] for index in cluster),
                    "last_seen": max(claims[index]["last_seen"] for index in cluster),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
            for cluster in clusters
        )
    )
    (directory / CONTRADICTIONS).write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in relations
            if row["relation"] == "conflicting"
        )
    )
    counts: dict[str, int] = {}
    for row in relations:
        counts[str(row["relation"])] = counts.get(str(row["relation"]), 0) + 1
    print(f"  relations {counts}")
    merged = sum(len(cluster) for cluster in clusters)
    print(f"  {len(clusters):,} clusters covering {merged:,} claims")
    print(f"  relations {directory / RELATIONS}")
    print(f"  clusters {directory / CLUSTERS}")
    print(f"  contradictions {directory / CONTRADICTIONS}")
    return 0
