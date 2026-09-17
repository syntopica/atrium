"""Stage two: sampling, project attribution and structuring one claim."""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from atrium.curate import extracted_claim as extracted_claim_module
from atrium.curate.conversation_workspaces import conversation_workspaces
from atrium.curate.done_claim_ids import done_claim_ids
from atrium.curate.extracted_claim import extracted_claim
from atrium.curate.optional_field import optional_field
from atrium.curate.project_of_workspace import project_of_workspace
from atrium.curate.sampled_candidates import sampled_candidates
from atrium.curate.stratum_quotas import stratum_quotas


def _candidate(index: int, month: str = "2026-09", episodes: int = 1) -> dict[str, Any]:
    return {
        "candidate_id": f"{index:024x}",
        "text": f"claim number {index}",
        "normalized": f"claim number {index}",
        "first_seen": f"{month}-01",
        "last_seen": f"{month}-02",
        "episodes": episodes,
        "sources": [{"conversation_id": f"c{index}", "job_key": f"j{index}"}],
    }


def _ledger(path: Path, records: list[dict[str, Any]]) -> Path:
    path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records))
    return path


def test_quotas_give_a_small_stratum_its_floor() -> None:
    quotas = stratum_quotas({"big": 100_000, "rare": 50}, 600, minimum=10)
    assert quotas["rare"] == 10
    assert sum(quotas.values()) == 600


def test_quotas_never_ask_for_more_than_a_stratum_holds() -> None:
    quotas = stratum_quotas({"a": 5, "b": 3}, 600)
    assert quotas == {"a": 5, "b": 3}


def test_sample_is_deterministic_and_disjoint(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path / "candidates.jsonl", [_candidate(index) for index in range(200)])
    working, holdout = sampled_candidates(ledger, 20, 5)
    again, again_holdout = sampled_candidates(ledger, 20, 5)
    assert [record["candidate_id"] for record in working] == [
        record["candidate_id"] for record in again
    ]
    assert [record["candidate_id"] for record in holdout] == [
        record["candidate_id"] for record in again_holdout
    ]
    assert not {record["candidate_id"] for record in working} & {
        record["candidate_id"] for record in holdout
    }


def test_a_growing_ledger_keeps_the_candidates_already_drawn(tmp_path: Path) -> None:
    """Hashing the id rather than shuffling is what lets a sample be extended."""
    first = [_candidate(index) for index in range(200)]
    ledger = _ledger(tmp_path / "candidates.jsonl", first)
    before = {record["candidate_id"] for record in sampled_candidates(ledger, 20, 0)[0]}
    _ledger(tmp_path / "candidates.jsonl", first + [_candidate(index) for index in range(200, 400)])
    after = {record["candidate_id"] for record in sampled_candidates(ledger, 40, 0)[0]}
    assert before <= after


def test_both_repetition_buckets_are_sampled(tmp_path: Path) -> None:
    records = [_candidate(index) for index in range(1_000)]
    records += [_candidate(index, episodes=4) for index in range(1_000, 1_010)]
    ledger = _ledger(tmp_path / "candidates.jsonl", records)
    working, _ = sampled_candidates(ledger, 60, 0)
    assert sum(1 for record in working if record["episodes"] > 1) >= 5


@pytest.mark.parametrize("value", [None, "", "  ", "null", "None", "n/a"])
def test_an_empty_answer_becomes_none(value: str | None) -> None:
    assert optional_field(value) is None


def test_a_worktree_belongs_to_its_repository() -> None:
    assert project_of_workspace("[HOME]/p/bot/.worktrees/repo-keeper") == "bot"
    assert project_of_workspace("[HOME]/p/atrium") == "atrium"
    assert project_of_workspace(None) is None


@pytest.mark.parametrize(
    "workspace",
    [
        "[HOME]",
        "/var/folders/k2/T/atrium-codex-2tn05jjb",
        "/tmp/scratch",
        "[HOME]/.wide-project-work/evaldiscrim/out-v19/_codex",
    ],
)
def test_a_workspace_with_no_project_says_so(workspace: str) -> None:
    """A page named after a scratch directory is named after nothing."""
    assert project_of_workspace(workspace) is None


def test_the_dominant_workspace_wins(tmp_path: Path) -> None:
    index = tmp_path / "index.sqlite3"
    connection = sqlite3.connect(index)
    connection.execute("CREATE TABLE records (conversation_id TEXT, workspace TEXT)")
    connection.executemany(
        "INSERT INTO records VALUES (?, ?)",
        [("c1", "/p/first"), ("c1", "/p/second"), ("c1", "/p/second"), ("c2", None)],
    )
    connection.commit()
    connection.close()
    assert conversation_workspaces(index, ["c1", "c2"]) == {"c1": "/p/second"}


def test_the_model_cannot_restate_a_date_or_a_project(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provenance comes from the ledger and the index, never from the answer."""

    def fake_call(*_: Any, **__: Any) -> dict[str, Any]:
        return {
            "input": {
                "subject": "the drip",
                "predicate": "runs at",
                "value": "594 records/hour",
                "conditions": "null",
                "scope": "project",
                "scope_name": "invented",
                "durability": "durable",
                "first_seen": "1999-01-01",
            },
            "model": "test-model",
            "usage": {},
        }

    monkeypatch.setattr(extracted_claim_module, "local_lane_call", fake_call)
    claim = extracted_claim(_candidate(7), project="atrium")
    assert claim.first_seen == "2026-09-01"
    assert claim.last_seen == "2026-09-02"
    assert claim.project == "atrium"
    assert claim.conditions is None
    assert claim.candidate_id == _candidate(7)["candidate_id"]


def test_a_truncated_last_line_does_not_stop_a_resume(tmp_path: Path) -> None:
    path = tmp_path / "claims.jsonl"
    path.write_text('{"candidate_id": "aa"}\n{"candidate_id": "bb"}\n{"candidate_i')
    assert done_claim_ids(path) == {"aa", "bb"}


def test_a_rare_stratum_is_split_like_every_other(tmp_path: Path) -> None:
    """The split has to happen inside each stratum, or the rare one lands in the holdout."""
    records = [_candidate(index) for index in range(5_000)]
    records += [_candidate(index, episodes=3) for index in range(5_000, 5_050)]
    ledger = _ledger(tmp_path / "candidates.jsonl", records)
    working, holdout = sampled_candidates(ledger, 500, 100)
    assert sum(1 for record in working if record["episodes"] > 1) >= 6
    assert sum(1 for record in holdout if record["episodes"] > 1) <= 4
