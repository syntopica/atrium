"""Aggregate paired recall, reciprocal rank, latency and uncertainty."""

from collections import Counter

import numpy as np


def summarize(rows: list[dict]) -> dict:
    """Report all questions and the common answerable subset separately."""
    result = {}
    for split in sorted({row["split"] for row in rows}):
        for eligible in (False, True):
            selected = [
                row for row in rows if row["split"] == split and (not eligible or row["answerable"])
            ]
            if not selected:
                continue
            hits = np.array([float(row["rank"] is not None) for row in selected])
            ranks = [1 / row["rank"] if row["rank"] else 0 for row in selected]
            times = [row["elapsed_ms"] for row in selected]
            result[f"{split}/{'answerable' if eligible else 'all'}"] = {
                "n": len(selected),
                "hits": int(hits.sum()),
                "recall_at_8": float(hits.mean()),
                "mrr_at_8": float(np.mean(ranks)),
                "p50_ms": float(np.percentile(times, 50)),
                "p95_ms": float(np.percentile(times, 95)),
                "errors": sum(bool(row.get("error")) for row in selected),
                "warning_counts": dict(
                    Counter(warning for row in selected for warning in row.get("warnings", []))
                ),
            }
    return result
