"""The JSON a refused Stop prints: the reason for the model, one line for the person."""

# "2026-09-16T10:21" is 16 characters: an ISO timestamp long enough to show HH:MM.
_HH_MM_END = 16


def stop_refusal(
    reason: str, checkpoint_id: str, since: str | None, *, retry: bool = False
) -> dict[str, object]:
    """Wrap ``reason`` with a `systemMessage` and `suppressOutput`.

    Claude Code feeds ``reason`` to the model and also prints it in the
    terminal; ``systemMessage`` is the field it renders for the person, so
    the status they read is one line rather than the instruction. Rendering
    of `systemMessage` on Stop is best-effort in some builds (claude-code
    issue #50542), which is why the reason stays complete on its own.
    """
    window = f" since {since[11:16]} UTC" if since and len(since) >= _HH_MM_END else ""
    verb = "still waiting for" if retry else "recording"
    return {
        "decision": "block",
        "reason": reason,
        "systemMessage": f"atrium: {verb} this session's memory record{window} (checkpoint {checkpoint_id})",
        "suppressOutput": True,
    }
