"""The `erase` handler of the atrium CLI."""

import json
from pathlib import Path

from atrium.erase.archive_generation import archive_generation
from atrium.erase.clear_partials import clear_partials
from atrium.erase.delete_erased_rows import delete_erased_rows
from atrium.erase.erase_lock_file import erase_lock_file
from atrium.erase.erased_curation_candidates import erased_curation_candidates
from atrium.erase.erased_record_files import erased_record_files
from atrium.erase.erased_record_identifiers import erased_record_identifiers
from atrium.erase.hold_locks import hold_locks
from atrium.erase.journaled_identifiers import journaled_identifiers
from atrium.erase.read_erasure_plan import read_erasure_plan
from atrium.erase.remember_erased import remember_erased
from atrium.erase.scrub_curation import scrub_curation
from atrium.serve.dense_matrix_file import dense_matrix_file
from atrium.sql.load_sql import load_sql
from atrium.state.state_directory import state_directory
from atrium.store.open_store import open_store
from atrium.synthesize.default_registry import default_registry


def run_erase(index: Path, plan_path: Path, archive: Path, *, apply: bool) -> int:
    """Remove what Atrium derived from the conversations an applied plan erased.

    The raw rows go with the next full ingest of the new generation anyway; the
    synthesis does not, because the registry still holds it and a session record
    exists before its conversation is archived, so absence cannot say "erased".

    Refuses an index other than the configured instance's: the registry,
    curation and matrix are that instance's, and erasing them against another
    index would leave the live one able to serve the text. Reports first and
    writes only with ``apply``, and only when the configured archive -- the one
    the next ingest reads -- names the plan's target generation as its own or
    an ancestor: an archive still holding the conversation would bring it back,
    and get it re-synthesized. Writes holding the erase lock exclusively, which
    every writing command takes shared, then the refresh and synthesis locks;
    every identifier is journaled before the first delete, so a run that fails
    partway is finished by running it again. The erased conversation ids are
    also kept for good, so a live session's hook cannot record one back later.
    """
    plan = read_erasure_plan(plan_path)
    conversation_ids = set(plan.conversation_ids)
    instance = state_directory()
    if index.resolve() != (instance / "index.sqlite3").resolve():
        print(f"refused: {index} is not the index of the configured instance {instance}")
        return 2
    registry = default_registry()
    curation = instance / "curation"
    files = erased_record_files(registry, conversation_ids)
    candidates = erased_curation_candidates(curation, conversation_ids)
    report: dict[str, object] = {
        "conversations": len(conversation_ids),
        "record_files": len(files),
        "curation_candidates": len(candidates),
        "applied": False,
    }
    generations = archive_generation(archive)
    if apply and plan.to_generation_id not in generations:
        print(json.dumps(report, sort_keys=True))
        print(
            f"refused: {archive} descends from {generations or 'no named generation'}, "
            f"which does not include the plan's target {plan.to_generation_id!r}"
        )
        return 1
    if not apply:
        print(json.dumps(report, sort_keys=True))
        return 0
    try:
        with hold_locks(
            [erase_lock_file(instance), instance / "refresh.lock", registry / "synthesis.lock"]
        ):
            # Found again under the locks: a writer may have added one since.
            files = erased_record_files(registry, conversation_ids)
            candidates = erased_curation_candidates(curation, conversation_ids)
            report["curation_candidates"] = len(candidates)
            remember_erased(instance, conversation_ids)
            journal = instance / f"erase-{plan.to_generation_id}.journal.json"
            needles = journaled_identifiers(
                journal, conversation_ids | erased_record_identifiers(files) | set(candidates)
            )
            # The registry goes first: while its files exist, any ingest-synthesis
            # would put the rows back, and the journal now holds their identifiers.
            for path in files:
                path.unlink(missing_ok=True)
            report["record_files"] = len(files)
            connection = open_store(index)
            try:
                with connection:
                    report["index_rows_removed"] = delete_erased_rows(
                        connection, sorted(conversation_ids)
                    )
                # The WAL still holds the pre-delete pages until a checkpoint
                # writes them back and truncates it; a reader holding an old
                # snapshot keeps it busy, which the report says.
                checkpoint = list(
                    connection.execute(load_sql("store/wal_checkpoint_truncate")).fetchone()
                )
                report["wal_checkpoint"] = checkpoint
            finally:
                connection.close()
            report["partials_removed"] = clear_partials(registry / "partials")
            report["curation"] = scrub_curation(curation, needles)
            # The saved matrix still holds the erased vectors on disk; the service
            # rebuilds from the index, whose generation the deletes just moved.
            dense_matrix_file(instance).unlink(missing_ok=True)
            journal.unlink()
    except BlockingIOError:
        print(
            "refused: a writer, a refresh or a synthesis pass holds the instance; run again after it"
        )
        return 3
    report["applied"] = True
    print(json.dumps(report, sort_keys=True))
    if checkpoint[0]:
        print("incomplete: a reader kept the WAL from truncating; run erase again once it is idle")
        return 4
    return 0
