"""The `curate-extract` command: stage two of the promotion pipeline."""

import json
import time

from atrium.curate.append_claim import append_claim
from atrium.curate.claims_ledger_path import claims_ledger_path
from atrium.curate.conversation_workspaces import conversation_workspaces
from atrium.curate.curation_directory import curation_directory
from atrium.curate.done_claim_ids import done_claim_ids
from atrium.curate.extracted_claim import extracted_claim
from atrium.curate.project_of_workspace import project_of_workspace
from atrium.curate.sampled_candidates import sampled_candidates
from atrium.curate.write_ledger import CANDIDATES
from atrium.state.state_directory import state_directory
from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL

HOLDOUT = "holdout.jsonl"


def run_curate_extract_cli(size: int, holdout: int, model: str = LOCAL_DEFAULT_MODEL) -> int:
    """Structure a stratified sample of the candidate ledger, and say what it cost.

    The holdout is written out but never extracted: it is what measures the
    stage after this one has been tuned on the working set, so touching it
    here would spend the only unbiased sample there is.
    """
    directory = curation_directory()
    ledger = directory / CANDIDATES
    if not ledger.exists():
        print(f"  no candidate ledger at {ledger}; run `atrium curate-screen` first")
        return 1
    working, held = sampled_candidates(ledger, size, holdout)
    (directory / HOLDOUT).write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in held)
    )
    claims = claims_ledger_path(directory)
    already = done_claim_ids(claims)
    pending = [record for record in working if record["candidate_id"] not in already]
    workspaces = conversation_workspaces(
        state_directory() / "index.sqlite3",
        [source["conversation_id"] for record in pending for source in record["sources"]],
    )
    print(
        f"  sample {len(working):,} working, {len(held):,} holdout, {len(already):,} already done"
    )
    started = time.monotonic()
    failed = 0
    for done, record in enumerate(pending, start=1):
        try:
            project = project_of_workspace(workspaces.get(record["sources"][0]["conversation_id"]))
            append_claim(claims, extracted_claim(record, model=model, project=project))
        except (RuntimeError, KeyError, ValueError) as error:
            failed += 1
            print(f"  [{done}/{len(pending)}] {record['candidate_id']} failed: {error}")
            continue
        if done % 25 == 0 or done == len(pending):
            rate = done / max(time.monotonic() - started, 1e-9)
            print(
                f"  [{done}/{len(pending)}] {rate * 3600:,.0f} claims/hour, {failed} failed",
                flush=True,
            )
    print(f"  claims {claims}")
    print(f"  holdout {directory / HOLDOUT}")
    return 0
