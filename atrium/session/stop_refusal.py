"""The JSON a refused Stop prints: the instruction, as non-error hook feedback."""


def stop_refusal(reason: str) -> dict[str, object]:
    """Hand ``reason`` back as Stop ``additionalContext``, not as a block.

    Both keep the turn going under the same loop guards (`stop_hook_active`
    and the consecutive-continuation cap), but Claude Code draws
    ``decision: "block"`` as a hook error and ``systemMessage`` as a warning,
    which on the mobile client read as a failure after every recorded turn.
    ``additionalContext`` shows as dim "Stop hook feedback" instead.
    """
    return {"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": reason}}
