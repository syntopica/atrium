"""The instruction a refused Stop hands the model, short: Claude Code shows it whole."""


def refusal_reason(checkpoint_id: str, since: str | None, *, retry: bool) -> str:
    """Return the reason text: the command, the contract in one line, then stop.

    Claude Code prints a Stop refusal in the terminal as "Stop hook error"
    followed by the whole reason, so a schema dump here is a wall of text the
    person reads every time. The full contract lives in
    `atrium record-session --help`. Changing this text is a recipe change:
    bump ``SESSION_RECIPE_VERSION``.
    """
    window = f"since {since}" if since else "since this session began"
    head = (
        "The episode is still unrecorded; record it now. "
        if retry
        else "Before stopping, record this session's episode in the memory registry. "
    )
    return (
        f"{head}You did the work {window}, so you know what mattered. Run "
        f"`atrium record-session --checkpoint {checkpoint_id}` with one JSON object on "
        'stdin: {"title", "summary", "facts": [...], "open_ends": [...]} in the '
        "episode's language, names, paths, commands and numbers exact, outcomes not "
        "narration, nothing invented (`--help` has the contract; `--nothing-durable` "
        "if nothing is worth keeping). Then stop: no other work."
    )
