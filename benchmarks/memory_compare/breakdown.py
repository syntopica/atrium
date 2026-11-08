"""Describe language and question-type differences without exposing questions."""

from benchmarks.memory_compare.summarize import summarize


def breakdown(results):
    """Group by the dataset's original, pre-existing strata."""
    output = {}
    for name, rows in results.items():
        grouped = {}
        for position, dimension in enumerate(("language", "kind", "lexical", "age")):
            for category in sorted({row["strata"][position] for row in rows}):
                selected = [row for row in rows if row["strata"][position] == category]
                grouped[f"{dimension}/{category}"] = summarize(selected)
        output[name] = grouped
    return output
