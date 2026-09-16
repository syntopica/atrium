"""The instruction a refused Stop hands the model: the whole contract."""

import json

from atrium.synthesize.synthesis_schema import SYNTHESIS_TOOL


def refusal_reason(checkpoint_id: str, since: str | None, *, retry: bool) -> str:
    """Return the reason text; self-contained, the model has no other context.

    Changing this text is a recipe change: bump ``SESSION_RECIPE_VERSION``.
    """
    schema = json.dumps(SYNTHESIS_TOOL["input_schema"], ensure_ascii=False)
    window = f"since {since}" if since else "since this session began"
    head = (
        "The previous turn did not record the episode; do it now. "
        if retry
        else "Before stopping, record this session's episode in the memory registry. "
    )
    return (
        f"{head}You are the agent who did the work {window}, so you know what mattered. "
        "Run exactly this command, with the JSON on stdin:\n\n"
        f"atrium record-session --checkpoint {checkpoint_id} <<'JSON'\n"
        '{"title": ..., "summary": ..., "facts": [...], "open_ends": [...]}\n'
        "JSON\n\n"
        f"The JSON must match this schema and nothing else: {schema}\n"
        "Write in the episode's dominant language. Keep names, versions, paths, "
        "commands and numbers exactly as they appeared; state outcomes, not "
        "narration; put decisions with their why and measured numbers in facts; "
        "put what was left unfinished or blocked in open_ends; never invent "
        "content absent from the session. If the interval produced nothing worth "
        f"keeping, run `atrium record-session --checkpoint {checkpoint_id} "
        "--nothing-durable` instead. If the command reports an invalid payload, "
        "fix the JSON and run it again. Then stop: no other work, no reply "
        "beyond the command."
    )
