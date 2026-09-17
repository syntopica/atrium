"""The `curate-publishable` command: what each claim is, before any page."""

import json
import time

from atrium.curate.claim_publishability import claim_publishability
from atrium.curate.claims_ledger_path import claims_ledger_path
from atrium.curate.curation_directory import curation_directory
from atrium.curate.publishable_claims import publishable_claims
from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL

PUBLISHABILITY = "publishability.jsonl"


def run_curate_publishable_cli(budget: int, model: str = LOCAL_DEFAULT_MODEL) -> int:
    """Classify every claim as durable knowledge, incident evidence or session noise.

    This replaces the debris regexes as the real filter. Hand-written patterns
    caught the shapes they were written from and the next grading pass always
    found more; asking what a claim asserts generalises to shapes nobody has
    seen yet. The patterns stay as a cheap first pass because they cost
    nothing.
    """
    directory = curation_directory()
    claims_path = claims_ledger_path(directory)
    if not claims_path.exists():
        print(f"  no claim ledger at {claims_path}; run `atrium curate-extract` first")
        return 1
    claims, dropped = publishable_claims(claims_path)
    print(f"  {len(claims):,} claims, {sum(dropped.values()):,} dropped by pattern", flush=True)
    started = time.monotonic()
    rows = []
    counts: dict[str, int] = {}
    for done, claim in enumerate(claims[:budget], start=1):
        verdict, fields = claim_publishability(claim["text"], model=model)
        counts[verdict] = counts.get(verdict, 0) + 1
        rows.append(
            {
                "candidate_id": claim["candidate_id"],
                "text": claim["text"],
                "project": claim["project"],
                "durability": claim["durability"],
                "verdict": verdict,
                "asserted": fields["asserted"],
            }
        )
        if done % 50 == 0 or done == min(len(claims), budget):
            rate = done / max(time.monotonic() - started, 1e-9)
            print(
                f"  [{done}/{min(len(claims), budget)}] {rate * 3600:,.0f} claims/hour", flush=True
            )
    (directory / PUBLISHABILITY).write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    )
    print(f"  verdicts {counts}")
    agreed = sum(
        1
        for row in rows
        if (row["verdict"] == "durable_knowledge") == (row["durability"] == "durable")
    )
    print(f"  agrees with stage two's durability on {agreed:,}/{len(rows):,}")
    print(f"  publishability {directory / PUBLISHABILITY}")
    return 0
