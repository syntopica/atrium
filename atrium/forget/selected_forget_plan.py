"""Plan the forget pass the command line selected."""

from pathlib import Path
from typing import Any

from atrium.forget.echo_forget_plan import echo_forget_plan
from atrium.forget.forget_plan import forget_plan
from atrium.state.archive_path import archive_path
from atrium.synthesize.default_registry import default_registry


def selected_forget_plan(
    index: Path, ledger: Path, restore: str | None, today: str, *, echoes: bool
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """The echo rule with ``echoes``; else a restore, or the retirement rule."""
    if echoes and restore is None:
        return echo_forget_plan(default_registry(), archive_path(), ledger, today)
    return forget_plan(index, ledger, restore, today)
