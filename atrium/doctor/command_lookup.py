"""What a PATH search found: the command the shell would run, and what it stepped over."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandLookup:
    """The first runnable candidate, plus every unusable one ahead of it.

    ``command`` is ``None`` when no PATH entry yields something runnable --
    the only state that makes the command genuinely unreachable. ``shadows``
    is context either way: with a command it explains a machine that works by
    luck, and without one it says why the name on PATH does not run.
    """

    command: Path | None
    shadows: tuple[str, ...]
