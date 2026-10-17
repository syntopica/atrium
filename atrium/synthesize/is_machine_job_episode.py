"""Whether an episode is a machine job that no person took part in."""

import re
from typing import Any

from atrium.ingest.machine_job_prefixes import MACHINE_JOB_PREFIXES
from atrium.ingest.machine_prompt_prefixes import MACHINE_PROMPT_PREFIXES
from atrium.synthesize.is_environment_context import is_environment_context

_WHITESPACE = re.compile(r"\s+")


def is_machine_job_episode(event_indexes: list[int], events: list[dict[str, Any]]) -> bool:
    """True when a user message opens a machine job and no person speaks.

    Ingest already keeps these prompts out of the index; synthesizing the job's
    answer spent quota on a security review or a mail classification that no
    one asked to remember. Harness injections (Codex's `# AGENTS.md
    instructions`, `<environment_context>`) are no person speaking, so they
    neither make the job nor keep it. An episode where a person speaks is kept.
    """
    openings = [
        _WHITESPACE.sub(" ", text[:240]).strip()
        for i in event_indexes
        if events[i].get("role") == "user"
        and not is_environment_context(text := events[i].get("text") or "")
    ]
    return any(text.startswith(MACHINE_JOB_PREFIXES) for text in openings) and all(
        text.startswith(MACHINE_PROMPT_PREFIXES) for text in openings
    )
