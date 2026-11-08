"""Measure paired differences without treating two query sets as independent."""

import numpy as np


def paired_differences(results: dict[str, list[dict]]) -> dict:
    """Bootstrap query-level recall deltas with a fixed seed; retain win/loss counts."""
    output = {}
    for split in ("acceptance", "holdout"):
        baseline = {row["id"]: row for row in results["atrium_reranked"] if row["split"] == split}
        for name, rows in results.items():
            if name == "atrium_reranked":
                continue
            other = {row["id"]: row for row in rows if row["split"] == split}
            if baseline.keys() != other.keys():
                raise ValueError("paired comparison requires identical query IDs")
            differences = np.array(
                [
                    int(baseline[key]["rank"] is not None) - int(other[key]["rank"] is not None)
                    for key in baseline
                ]
            )
            rng = np.random.default_rng(20261021)
            sampled = rng.choice(differences, size=(2000, len(differences))).mean(axis=1)
            output[f"{split}/atrium_reranked-minus-{name}"] = {
                "n": len(differences),
                "recall_delta": float(differences.mean()),
                "wins": int((differences > 0).sum()),
                "losses": int((differences < 0).sum()),
                "bootstrap_95_percent": np.percentile(sampled, [2.5, 97.5]).tolist(),
            }
    return output
