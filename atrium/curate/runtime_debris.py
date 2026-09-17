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
    # `~/p/project-after`" was the most repeated claim in the corpus at 59
    # episodes, ahead of every real finding.
    # Graded by hand over 60 extracted claims on 2026-09-17: 12% of what
    # reached stage two was still this shape, and repetition does not save it
    # -- "The shell working directory was reset to `<path>`" carried 7
    # episodes, more than any real finding in the same sample.
    (
        "session_mechanics",
        re.compile(
            r"\b(shell )?working directory was reset\b|"
            r"\bcommits? locales sin push\b|\b(local )?commits? (not|un)pushed\b|"
            r"\bfinal review verdicts?\b|\bspec compliance\b",
            re.I,
        ),
    ),
    (
        "context_restatement",
        re.compile(
            r"^\s*(the\s+)?(session|current)?\s*"
            r"(repository|repo|project (path|directory|root)|working directory|"
            r"directory|path|account|user|branch|workspace)\s*[:=]\s*\S+\s*\.?\s*$",
            re.I,
        ),
    ),
    # A sentence that is a verb and a path records that a file was touched.
    # Which file changed is in the diff; a claim has to say what changed.
    (
        "file_touched",
        re.compile(
            r"^\s*(updated|created|modified|added|deleted|removed|touched|escrito|"
            r"actualizado|creado|modificado)\s+`?[~.\[\w/][^\s`]*/[^\s`]*`?\s*\.?\s*$",
            re.I,
        ),
    ),
    # A counter line whose every value is zero, and a monitor snapshot, say
    # that nothing happened. They are the shape a progress log has, not a
    # finding: "total=0 succeeded=0 running=0 failed=0 queued=0".
    (
        "empty_metric",
        re.compile(r"(\b\w+\s*[:=]\s*0\b[\s,;]*){3,}|\bjob monitor\b", re.I),
    ),
    # Order matters: `Project path: <path>` belongs to the class above, which
    # names why it is worthless, so the generic pointer is tried last.
    # A sentence whose whole content is "<something> is at <path>" states
    # where a file is and nothing about it. The path is in the transcript the
    # record already cites, so the claim adds a name and loses the content.
    # Pure location claims are caught too ("`selectQuoteMatch` reside en
    # `src/lib/.../selectQuoteMatch.ts`"): a symbol's location is what
    # codegraph answers from the live tree, where it cannot go stale.
    (
        "path_pointer",
        re.compile(
            r"^[^.]{0,60}?\b(is (located|documented|available) at|reside en|se encuentra en|"
            r"ruta( de \w+)?|task (brief|report)|path|consultad[oa]|de referencia)\b\s*[:=]?\s*`?[~.\[\w/][^\s`]*/[^\s`]*`?\s*\.?\s*$",
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
