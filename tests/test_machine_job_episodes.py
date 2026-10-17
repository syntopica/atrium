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


AGENTS = "# AGENTS.md instructions for /private/var/folders/x/T/job\n\n<INSTRUCTIONS>..."
INVOICE = "You are an expert invoice schema formatter. SECURITY PREAMBLE: ..."


def test_a_codex_job_with_injected_instructions_is_a_machine_job() -> None:
    events = [
        {"role": "user", "text": AGENTS},
        {
            "role": "user",
            "text": "<environment_context>\n  <cwd>/tmp/job</cwd>\n</environment_context>",
        },
        {"role": "user", "text": INVOICE},
        {"role": "assistant", "text": "{}"},
    ]
    assert is_machine_job_episode([0, 1, 2, 3], events)


def test_injected_instructions_alone_are_not_a_machine_job() -> None:
    events = [{"role": "user", "text": AGENTS}, {"role": "assistant", "text": "ok"}]
    assert not is_machine_job_episode([0, 1], events)


def test_a_person_after_injected_instructions_keeps_it() -> None:
    events = [
        {"role": "user", "text": AGENTS},
        {"role": "user", "text": INVOICE},
        {"role": "user", "text": "why did the total change?"},
    ]
    assert not is_machine_job_episode([0, 1, 2], events)


def test_atrium_own_stages_are_machine_jobs() -> None:
    from atrium.curate.claim_destination import _SYSTEM as DESTINATION
    from atrium.curate.claim_publishability import _SYSTEM as PUBLISHABILITY
    from atrium.curate.extracted_claim import _SYSTEM as EXTRACTION
    from atrium.curate.pair_relation import _SYSTEM as RELATION
    from atrium.synthesize.synthesis_prompt import SYNTHESIS_SYSTEM_TEXT

    for system in (DESTINATION, PUBLISHABILITY, EXTRACTION, RELATION, SYNTHESIS_SYSTEM_TEXT):
        events = [{"role": "user", "text": f"{system}\n\n=== BEGIN FACT ==="}]
        assert is_machine_job_episode([0], events), system[:60]


def test_a_person_writing_after_the_environment_block_keeps_it() -> None:
    events = [
        {"role": "user", "text": INVOICE},
        {"role": "user", "text": "<environment_context></environment_context>\nfix the totals"},
    ]
    assert not is_machine_job_episode([0, 1], events)
