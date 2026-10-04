"""Every worker job a pass submits is journaled against its conversation."""

from atrium.synthesize.read_worker_submissions import read_worker_submissions
from atrium.synthesize.record_worker_submission import record_worker_submission


def test_a_submission_is_read_back_by_job_id(tmp_path):
    journal = tmp_path / "registry" / "worker-submissions.jsonl"
    record_worker_submission(journal, "j1", "conv-a")
    record_worker_submission(journal, "j2", "conv-b")
    assert read_worker_submissions(journal) == {"j1": "conv-a", "j2": "conv-b"}


def test_a_missing_journal_reads_as_empty(tmp_path):
    assert read_worker_submissions(tmp_path / "absent.jsonl") == {}


def test_a_torn_last_line_is_ignored(tmp_path):
    journal = tmp_path / "worker-submissions.jsonl"
    record_worker_submission(journal, "j1", "conv-a")
    with journal.open("a") as handle:
        handle.write('{"job_id": "j2", "conv')
    assert read_worker_submissions(journal) == {"j1": "conv-a"}
