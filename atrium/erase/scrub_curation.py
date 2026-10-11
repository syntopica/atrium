"""Remove from the curation stores everything built from erased conversations."""

from collections.abc import Collection
from pathlib import Path

from atrium.erase.scrub_aligned_matrix import scrub_aligned_matrix
from atrium.erase.scrub_jsonl import scrub_jsonl
from atrium.erase.scrub_proposal_runs import scrub_proposal_runs

_IDS = "candidate-ids.jsonl"
_MATRIX = "candidates.f32"
_PROPOSALS = "proposals"


def scrub_curation(curation: Path, needles: Collection[str]) -> dict[str, int]:
    """Drop affected rows from every JSONL store, delete affected other files.

    Every curation output is disposable derived state, and each later stage
    keys on candidate ids, so a line or file naming a needle -- an affected
    candidate, an erased conversation, or the job key or episode of an erased
    record -- goes. The embedded matrix loses the rows of the affected
    candidates and is rewritten with its id list so the two stay aligned.
    Returns counts for the report.
    """
    report = {
        "matrix_rows": scrub_aligned_matrix(curation / _IDS, curation / _MATRIX, needles),
        "lines": 0,
        "files": 0,
        "proposal_runs": 0,
    }
    if not curation.is_dir() or not needles:
        return report
    report["proposal_runs"] = scrub_proposal_runs(curation / _PROPOSALS, needles)
    for path in sorted(curation.rglob("*")):
        if (
            not path.is_file()
            or path.name in (_IDS, _MATRIX)
            or _PROPOSALS in path.relative_to(curation).parts
        ):
            continue
        if path.suffix == ".jsonl":
            report["lines"] += scrub_jsonl(path, needles)
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(needle in text for needle in needles):
            path.unlink()
            report["files"] += 1
    return report
