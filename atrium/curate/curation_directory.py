"""Where the promotion pipeline keeps its derived ledgers."""

from pathlib import Path

from atrium.state.state_directory import state_directory


def curation_directory() -> Path:
    """The instance's ``curation`` directory, created on first use.

    Derived and rebuildable, so it sits beside the index rather than in the
    wiki: `AGENTS.md` forbids writing to the curated layer, and a proposal
    that lived there would be indistinguishable from a decision a human made.
    """
    directory = state_directory() / "curation"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory
