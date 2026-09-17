"""Stage one screens the registry deterministically, and quarantines the rest."""

import json
from pathlib import Path

from atrium.curate.candidate_identity import candidate_identity
from atrium.curate.normalized_claim import normalized_claim
from atrium.curate.runtime_debris import runtime_debris
from atrium.curate.screen_registry import screen_registry
from atrium.curate.write_ledger import write_ledger


def _registry(tmp_path: Path, records: list[dict]) -> Path:
    directory = tmp_path / "synthesis" / "records"
    directory.mkdir(parents=True)
    for index, record in enumerate(records):
        (directory / f"{index:04d}.json").write_text(json.dumps(record))
    return tmp_path / "synthesis"


def _record(job: str, date: str, facts: list[str]) -> dict:
    return {
        "job_key": job,
        "episode_id": f"e-{job}",
        "conversation_id": f"c-{job}",
        "authored_at": f"{date}T10:00:00Z",
        "model_requested": "test-model",
        "output": {"title": "t", "summary": "s", "facts": facts, "open_ends": []},
    }


def test_numbers_keep_two_measurements_apart() -> None:
    """A normalizer that folded digits would merge these into one finding."""
    first = normalized_claim("38 orphaned processes held 7.4 GB")
    second = normalized_claim("3 orphaned processes held 7.4 GB")
    assert candidate_identity(first) != candidate_identity(second)


def test_accents_and_markup_do_not_split_one_claim() -> None:
    same = {
        candidate_identity(normalized_claim("El `matcher` dio 0 coincidencias")),
        candidate_identity(normalized_claim("El matcher dio 0 coincidencias")),
    }
    assert len(same) == 1


def test_debris_names_the_reason_it_rejects() -> None:
    assert runtime_debris("Background task b3ddu8k2q output path: /private/tmp/x.output") in {
        "scratch_path",
        "task_handle",
    }
    assert runtime_debris("Structured output was provided successfully by the model run") == (
        "empty_acknowledgement"
    )
    assert runtime_debris("short") == "too_short"
    assert runtime_debris("Enable Banking's CaixaBank consent expires every 90 days") is None


def test_one_claim_stated_twice_keeps_both_sources_and_the_fuller_wording(tmp_path: Path) -> None:
    registry = _registry(
        tmp_path,
        [
            _record("a", "2026-07-01", ["The drip left 38 orphaned worker-server processes"]),
            _record(
                "b",
                "2026-09-16",
                ["The drip left 38 orphaned worker-server processes holding 7.4 GB of memory"],
            ),
        ],
    )
    report = screen_registry(registry)
    # Different wording is a different candidate today: merging paraphrases is
    # stage three's job, with a model, not this pass's.
    assert report.facts == 2
    assert len(report.candidates) == 2
    assert report.records == 2


def test_the_same_fact_twice_collapses_and_dates_span_both(tmp_path: Path) -> None:
    fact = "Enable Banking's CaixaBank consent expires every 90 days and needs manual re-auth"
    registry = _registry(
        tmp_path, [_record("a", "2026-07-01", [fact]), _record("b", "2026-09-16", [fact])]
    )
    report = screen_registry(registry)
    assert len(report.candidates) == 1
    candidate = report.candidates[0]
    assert candidate.first_seen == "2026-07-01"
    assert candidate.last_seen == "2026-09-16"
    assert len(candidate.sources) == 2


def test_the_ledger_is_byte_identical_on_a_rerun(tmp_path: Path) -> None:
    """A reviewer diffing two runs must see only what the registry added."""
    registry = _registry(
        tmp_path,
        [
            _record("a", "2026-09-16", ["Commit 2757b9e fixes sudo-nopasswd.sh for no terminal"]),
            _record("b", "2026-09-16", ["Background with ID b3ddu8k2q started the pass"]),
        ],
    )
    first = tmp_path / "one"
    second = tmp_path / "two"
    first.mkdir()
    second.mkdir()
    write_ledger(first, screen_registry(registry))
    write_ledger(second, screen_registry(registry))
    assert (first / "candidates.jsonl").read_bytes() == (second / "candidates.jsonl").read_bytes()
    assert (first / "quarantine.jsonl").read_text().count("\n") == 1


def test_quarantine_keeps_what_it_rejected(tmp_path: Path) -> None:
    """Recoverable screening: the rejects are counted, not discarded."""
    registry = _registry(tmp_path, [_record("a", "2026-09-16", ["Session cwd remains ~/p/brain"])])
    report = screen_registry(registry)
    assert report.candidates == ()
    assert report.quarantined[0]["reason"] == "session_mechanics"
    assert report.reasons == {"session_mechanics": 1}


def test_a_string_of_facts_is_one_fact_not_a_hundred_letters(tmp_path: Path) -> None:
    """Measured: this shape inflated a real run to 418,246 facts, mostly letters."""
    registry = _registry(tmp_path, [_record("a", "2026-09-16", [])])
    (registry / "records" / "0000.json").write_text(
        json.dumps(
            {
                "job_key": "a",
                "episode_id": "e",
                "conversation_id": "c",
                "authored_at": "2026-09-16T10:00:00Z",
                "model_requested": "test-model",
                "output": {"facts": "The consent expires every 90 days and needs manual re-auth"},
            }
        )
    )
    report = screen_registry(registry)
    assert report.facts == 1
    assert len(report.candidates) == 1


def test_restating_where_the_session_ran_is_not_a_claim() -> None:
    """Measured: `Repository: ~/p/verticagtm` led the corpus at 59 episodes."""
    assert runtime_debris("Repository: `/Users/cristiandeluxe/p/verticagtm`.") == (
        "context_restatement"
    )
    assert runtime_debris("Project path: `/Users/cristiandeluxe/p/verticagtm`") == (
        "context_restatement"
    )
    # A sentence that merely starts with the same word keeps its place.
    assert (
        runtime_debris("Repository `~/p/atrium` refuses a push whose lockfile pin has drifted")
        is None
    )
