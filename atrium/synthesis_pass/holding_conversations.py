"""Settle recorded worker results and name the conversations still holding some."""

from pathlib import Path


def holding_conversations(worker_queue: str, recorded_results: set[str], journal: Path) -> set[str]:
    """Ack what the registry already holds, then return conversations with uncollected results."""
    from atrium.synthesize.ack_recorded_worker_results import ack_recorded_worker_results
    from atrium.synthesize.pending_worker_jobs import pending_worker_jobs
    from atrium.synthesize.read_worker_submissions import read_worker_submissions

    settled = ack_recorded_worker_results(worker_queue, recorded_results)
    if settled:
        print(f"  acked {settled} worker results the registry already held")
    # Results a pass stopped waiting for arrive unacknowledged and hold a
    # queue slot each. Walk their conversations first: re-submitting one
    # finds its job by idempotency key and collects the result, which a
    # full queue does not refuse. Left to the newest-first walk, they sat
    # behind the first refused submission until the worker expired them.
    submissions = read_worker_submissions(journal)
    return {submissions[job] for job in pending_worker_jobs(worker_queue) if job in submissions}
