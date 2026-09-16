"""Render recalled episodes into the block a session start injects."""

from atrium.retrieve.hit import Hit

# Roughly 900 tokens. The budget is the point of the whole mechanism: an
# injection large enough to be noticed is large enough to crowd out the work,
# and it is paid at the top of every single session in this project.
_BUDGET_CHARACTERS = 3600


def render_snapshot(project: str, hits: list[Hit]) -> str:
    """Return the recall block for ``project``, or an empty string when empty.

    An empty string rather than a "no memories yet" line: a session start that
    injects a sentence saying nothing is known has spent context to say nothing.

    Only the first line of each episode -- its title -- is rendered. The body is
    what search is for; this block exists to tell the session what ground has
    already been covered, so that it asks.
    """
    lines = []
    used = 0
    for hit in hits:
        stamp = (hit.authored_at or "")[:10]
        title = hit.text.splitlines()[0].strip()
        line = f"- {stamp} {title}"
        if used + len(line) > _BUDGET_CHARACTERS:
            break
        lines.append(line)
        used += len(line)
    if not lines:
        return ""
    return "\n".join(
        [
            f"# atrium recall ({project})",
            "",
            "This project has memory. Titles only, newest first; each one has a body,",
            "and the same index holds the curated notes these episodes came from.",
            "",
            "Before answering anything that sounds already established here -- a setup,",
            "a decision, a person, an incident, how something is deployed or accessed --",
            "retrieve it rather than re-deriving it, and say which of the two you did:",
            "",
            '    atrium context "<the question>" --project .',
            "",
            "A title below that is close to the question means the answer exists. So does",
            "silence: this list is one project's recent episodes, not everything indexed.",
            "",
            *lines,
        ]
    )
