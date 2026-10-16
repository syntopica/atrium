"""A machine job is left unsynthesized; an episode where a person speaks is not."""

from atrium.synthesize.is_machine_job_episode import is_machine_job_episode

REVIEW = (
    "Review this change for security vulnerabilities.\n\nChanged files (you may Read these "
    "and any other file in the repo):\n  - worker/jobs/settle_unsuccessful.py"
)


def test_a_security_review_job_is_a_machine_job() -> None:
    events = [
        {"role": "user", "text": REVIEW},
        {"role": "assistant", "text": "No security sink is involved."},
    ]
    assert is_machine_job_episode([0, 1], events)


def test_a_person_speaking_in_the_episode_keeps_it() -> None:
    events = [
        {"role": "user", "text": REVIEW},
        {"role": "user", "text": "also check the migration"},
    ]
    assert not is_machine_job_episode([0, 1], events)


def test_an_episode_without_user_messages_is_kept() -> None:
    assert not is_machine_job_episode([0], [{"role": "assistant", "text": "done"}])
