"""Whether an episode is a machine job that no person took part in."""

import re
from typing import Any

from atrium.ingest.machine_job_prefixes import MACHINE_JOB_PREFIXES

_WHITESPACE = re.compile(r"\s+")


def is_machine_job_episode(event_indexes: list[int], events: list[dict[str, Any]]) -> bool:
    """True when the episode has user messages and every one opens a machine job.

    Ingest already keeps these prompts out of the index; synthesizing the job's
    answer spent quota on a security review or a mail classification that no
    one asked to remember. An episode where a person also speaks is kept.
    """
    prompts = [
        events[i].get("text") or "" for i in event_indexes if events[i].get("role") == "user"
    ]
    return bool(prompts) and all(
        _WHITESPACE.sub(" ", text[:240]).strip().startswith(MACHINE_JOB_PREFIXES)
        for text in prompts
    )
