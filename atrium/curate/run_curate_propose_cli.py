"""The `curate-propose` command: stage four, page proposals a human reviews."""

import json
import time
from typing import Any

from atrium.curate.claim_destination import claim_destination
from atrium.curate.claims_ledger_path import claims_ledger_path
from atrium.curate.curation_directory import curation_directory
from atrium.curate.jsonl_rows import jsonl_rows
from atrium.curate.load_page_library import load_page_library
from atrium.curate.proposal_directory import proposal_directory
from atrium.curate.proposal_review import proposal_review
from atrium.embed.embedder import Embedder
from atrium.state.instance_directory import instance_directory
from atrium.state.state_directory import state_directory
from atrium.store.open_store import open_store
from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL

PUBLISHABILITY = "publishability.jsonl"
DURABLE = "durable_knowledge"
MANIFEST = "manifest.json"
REVIEW = "review.md"


def run_curate_propose_cli(budget: int, model: str = LOCAL_DEFAULT_MODEL) -> int:
    """Place each durable claim on a curated page and write the run for review.

    Nothing here touches the wiki, by the rule this pipeline exists under: the
    run writes a manifest and a review sheet into the derived curation
    directory, and a human decides what becomes a page edit.
    """
    data = instance_directory()
    if data is None:
        print("no instance: set SYNTOPICA_DATA or run inside one")
        return 1
    directory = curation_directory()
    verdicts = {
        row["candidate_id"]: row["verdict"]
        for row in jsonl_rows(directory / PUBLISHABILITY)
        if row.get("verdict")
    }
    claims = [
        claim
        for claim in jsonl_rows(claims_ledger_path(directory))
        if verdicts.get(claim["candidate_id"]) == DURABLE
    ]
    if not claims:
        print(f"no durable claims: run curate-publishable first ({directory / PUBLISHABILITY})")
        return 1
    # The index lives in the instance's derived state, not beside its pages:
    # `data` is the wiki root the page paths resolve against.
    library = load_page_library(
        open_store(state_directory() / "index.sqlite3", read_only=True), Embedder(), data
    )
    placed: dict[str, list[dict[str, Any]]] = {}
    refused: list[dict[str, Any]] = []
    started = time.monotonic()
    for done, claim in enumerate(claims[:budget], start=1):
        project = claim.get("project")
        page = f"brain/projects/{str(project).lower()}.md" if project else None
        chosen, why, shortlist = claim_destination(library, claim["text"], page, model=model)
        row = {**claim, "why": why, "shortlist": shortlist, "destination": chosen}
        if chosen is None:
            refused.append(row)
        else:
            placed.setdefault(chosen, []).append(row)
        if done % 25 == 0 or done == min(len(claims), budget):
            rate = done / max(time.monotonic() - started, 1e-9)
            print(
                f"  [{done}/{min(len(claims), budget)}] {rate * 3600:,.0f} claims/hour", flush=True
            )
    run = proposal_directory()
    (run / MANIFEST).write_text(
        json.dumps(
            {"placed": placed, "refused": refused, "model": model, "pages": len(placed)},
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        )
    )
    (run / REVIEW).write_text(proposal_review(placed, refused))
    print(f"  {sum(len(rows) for rows in placed.values()):,} claims on {len(placed):,} pages")
    print(f"  {len(refused):,} refused a destination")
    print(f"  review {run / REVIEW}")
    return 0
