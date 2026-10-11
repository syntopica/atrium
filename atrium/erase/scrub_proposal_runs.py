"""Discard the proposal runs that drew on erased material."""

import shutil
from collections.abc import Collection
from pathlib import Path


def scrub_proposal_runs(proposals: Path, needles: Collection[str]) -> int:
    """Delete every run directory any file of which names a needle; return how many.

    A run is one unit: its ``manifest.json`` names each claim's candidate id, but
    ``review.md`` repeats the refused claims' text without one, so the sheet
    cannot be cleaned line by line and the run goes whole.
    """
    removed = 0
    if not proposals.is_dir():
        return removed
    for run in sorted(path for path in proposals.iterdir() if path.is_dir()):
        texts = (
            p.read_text(encoding="utf-8", errors="ignore") for p in run.rglob("*") if p.is_file()
        )
        if any(needle in text for text in texts for needle in needles):
            shutil.rmtree(run)
            removed += 1
    return removed
