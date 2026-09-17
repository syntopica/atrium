"""Write a screening report as two JSONL ledgers, deterministically."""

import json
from pathlib import Path

from atrium.curate.screening_report import ScreeningReport

CANDIDATES = "candidates.jsonl"
QUARANTINE = "quarantine.jsonl"


def write_ledger(directory: Path, report: ScreeningReport) -> dict[str, Path]:
    """Write the candidates and what the screen rejected, and say where.

    Byte-identical for unchanged input: candidates are already sorted by id,
    quarantine keeps registry order, and both files end in a newline. A
    reviewer diffing two runs should see only what the registry added.
    """
    candidates = directory / CANDIDATES
    quarantine = directory / QUARANTINE
    candidates.write_text(
        "".join(
            json.dumps(candidate.as_json(), ensure_ascii=False, sort_keys=True) + "\n"
            for candidate in report.candidates
        )
    )
    quarantine.write_text(
        "".join(
            json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
            for entry in report.quarantined
        )
    )
    return {"candidates": candidates, "quarantine": quarantine}
