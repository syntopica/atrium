"""The conversation id of one remembered statement."""

import hashlib


def remembered_conversation_id(
    workspace: str | None, output_json: str, supersedes: list[str]
) -> str:
    """Hash the project, the exact statement and what it replaces.

    The same statement remembered twice for the same project is one record, so
    an agent that retries a call does not double what it said.
    """
    payload = "\x00".join(["remember", workspace or "", output_json, *supersedes])
    return hashlib.sha256(payload.encode()).hexdigest()
