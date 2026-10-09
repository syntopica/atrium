"""Every conversation that submitted a job, not only the last one."""

from pathlib import Path

from atrium.synthesize.read_worker_job_owners import read_worker_job_owners
from atrium.synthesize.record_worker_submission import record_worker_submission


def test_a_job_submitted_by_two_conversations_names_both(tmp_path: Path):
    journal = tmp_path / "worker-submissions.jsonl"
    record_worker_submission(journal, "j1", "a")
    record_worker_submission(journal, "j1", "b")
    record_worker_submission(journal, "j2", "a")
    with journal.open("a") as handle:
        handle.write("{torn\n")
    assert read_worker_job_owners(journal) == {"j1": {"a", "b"}, "j2": {"a"}}


def test_a_missing_journal_names_nobody(tmp_path: Path):
    assert read_worker_job_owners(tmp_path / "absent.jsonl") == {}
