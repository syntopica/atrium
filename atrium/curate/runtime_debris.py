"""Whether a fact is session mechanics rather than knowledge, and why."""

import re

# Measured over 1,500 records sampled at random on 2026-09-17: 3.7% of the
# corpus is this shape. Each pattern names what it catches, because the
# quarantine file is read to count false negatives and a bare regex there
# would be unreviewable.
_PATTERNS = (
    ("scratch_path", re.compile(r"/private/tmp/|/tmp/claude-|\.output\b", re.I)),
    ("task_handle", re.compile(r"\b(background (task|with id)|backgrounded|task id)\b", re.I)),
    (
        "empty_acknowledgement",
        re.compile(
            r"structured output (was )?(provided|succeeded|completed)|"
            r"no (additional )?durable|nothing durable|no further (action|context)",
            re.I,
        ),
    ),
    ("session_mechanics", re.compile(r"\bsession cwd\b|\bexit code\b|\bcwd (was|remains)\b", re.I)),
    # Where the session ran is provenance the record already carries. Left in,
    # these dominate the ledger by repetition alone: "Repository:
    # `~/p/verticagtm`" was the most repeated claim in the corpus at 59
    # episodes, ahead of every real finding.
    (
        "context_restatement",
        re.compile(
            r"^\s*(the\s+)?(repository|repo|project (path|directory|root)|working directory|"
            r"directory|path|account|user|branch|workspace)\s*[:=]\s*\S+\s*\.?\s*$",
            re.I,
        ),
    ),
)
_MINIMUM_LENGTH = 40


def runtime_debris(fact: str) -> str | None:
    """Return the reason this fact is debris, or None when it may be knowledge.

    Quarantine, never deletion: the caller keeps what this rejects, with the
    reason, so the screen's false negatives can be counted instead of assumed.
    """
    # Patterns before length: a short line that is recognisably scratch is
    # quarantined as scratch, because "too_short" hides why it was rejected
    # and the reason breakdown is what makes the screen tunable.
    for reason, pattern in _PATTERNS:
        if pattern.search(fact):
            return reason
    if len(fact.strip()) < _MINIMUM_LENGTH:
        return "too_short"
    return None
