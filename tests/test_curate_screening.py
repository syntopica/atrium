"""Stage one screens the registry deterministically, and quarantines the rest."""

import json
from pathlib import Path

import pytest

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
    """Measured: `Repository: ~/p/project-after` led the corpus at 59 episodes."""
    assert runtime_debris("Repository: `/Users/operator/p/project-after`.") == (
        "context_restatement"
    )
    assert runtime_debris("Project path: `/Users/operator/p/project-after`") == (
        "context_restatement"
    )
    # A sentence that merely starts with the same word keeps its place.
    assert (
        runtime_debris("Repository `~/p/atrium` refuses a push whose lockfile pin has drifted")
        is None
    )


@pytest.mark.parametrize(
    ("fact", "reason"),
    [
        ("The shell working directory was reset to `[HOME]/p/busirocket`.", "session_mechanics"),
        ("21 commits locales sin push al cierre del episodio.", "session_mechanics"),
        (
            "Final review verdicts: `SPEC COMPLIANCE`, `TASK QUALITY: Approved`. No findings.",
            "session_mechanics",
        ),
        (
            "Task report is documented at [HOME]/p/inbox-companion/sdd/task-7-report.md.",
            "path_pointer",
        ),
        (
            "Ruta de estado: clips/needs-claude/2026/07/2026-07-30-pub-towardsai-net.",
            "path_pointer",
        ),
        (
            "`selectQuoteMatch` reside en `src/lib/findings/selectors/selectQuoteMatch.ts`.",
            "path_pointer",
        ),
    ],
)
def test_the_debris_graded_by_hand_is_now_named(fact: str, reason: str) -> None:
    """Each of these reached stage two in the 60-claim hand grading of 2026-09-17."""
    assert runtime_debris(fact) == reason


@pytest.mark.parametrize(
    "fact",
    [
        "scripts/deploy-nova.sh deploys the SaaS to a cPanel account via rsync to /home/x/build.",
        "The `familia con dueño` rule is implemented in `checks/rule_family_owner.py`, using"
        " `family_frames.py`, and wired into `checks/run.py`.",
        "El cliente HTTP se creó en `services/sales/deleteSalesDraft.ts` y ejecuta"
        " `DELETE /api/sales/drafts/${invoiceId}`.",
    ],
)
def test_a_claim_that_says_something_about_a_path_survives(fact: str) -> None:
    """The pointer patterns must not eat a claim whose content happens to be a path."""
    assert runtime_debris(fact) is None


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("retention limit -3 days", "retention limit 3 days"),
        ("the check is x >= 3", "the check is x < 3"),
        ("the check is x != 3", "the check is x = 3"),
        ("pnpm version 1.2 pinned", "pnpm version 1-2 pinned"),
        ("coverage floor is 54%", "coverage floor is 54"),
        ("the window is 12:30 long", "the window is 12.30 long"),
    ],
)
def test_a_sign_a_comparison_and_a_separator_are_not_punctuation(first: str, second: str) -> None:
    """All six collided in the shipped normalizer, found by a second opinion 2026-09-17."""
    assert normalized_claim(first) != normalized_claim(second)


def test_folding_still_collapses_markup_and_case() -> None:
    assert normalized_claim("Ran at `7.4 GB`") == normalized_claim("ran at 7.4 gb")


@pytest.mark.parametrize(
    ("fact", "reason"),
    [
        ("Session working directory: [HOME]/p/rocket-agents", "context_restatement"),
        ("Updated `[HOME]/p/project-after/src/lib/report-pdf/builders.ts`.", "file_touched"),
        (
            "Plan 4a1220e8 generation job monitor: total=0 succeeded=0 running=0 queued=0.",
            "empty_metric",
        ),
        ("Código fuente de referencia consultado: ~/p/qlcplus/plugins/dmxusb/src/", "path_pointer"),
    ],
)
def test_the_second_grading_pass_debris_is_named(fact: str, reason: str) -> None:
    """Each shape passed the first pattern set and was found grading 30 claims again."""
    assert runtime_debris(fact) == reason


@pytest.mark.parametrize(
    "fact",
    [
        "Updated the pnpm pin to 12.4.2 in package.json so the lockfile records the dependency.",
        "La suite de pruebas ejecutó 102 tests con 102 pasados, 0 fallados y tsc-exit=0.",
        "`matrix_step_count.py` overrides continuous Plasma and Noise with PLASMA_STEPS = 40.",
    ],
)
def test_a_claim_that_reports_a_change_or_a_count_survives(fact: str) -> None:
    """`file_touched` and `empty_metric` must not eat a change that says what changed."""
    assert runtime_debris(fact) is None
