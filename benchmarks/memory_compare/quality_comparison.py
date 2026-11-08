"""Reuse the paired estimator with the expanded-budget pass as its reference."""

from benchmarks.memory_compare.paired_differences import paired_differences


def quality_comparison(results, quality):
    """Label the reference explicitly while preserving the estimator and seed."""
    # The estimator's reference key is fixed; alias only for its calculation.
    variants = {"atrium_reranked": quality, "production_3s": results["atrium_reranked"]}
    variants.update({name: rows for name, rows in results.items() if name != "atrium_reranked"})
    return {
        key.replace("atrium_reranked-minus-", "atrium_quality_120s-minus-"): value
        for key, value in paired_differences(variants).items()
    }
