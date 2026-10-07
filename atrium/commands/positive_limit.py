"""The argument type every `--limit`-style CLI flag uses."""

import argparse


def positive_limit(raw: str) -> int:
    """Reject a limit that would uncap the query.

    SQLite treats a negative LIMIT as no limit, so `--limit -1` quietly returns
    the whole result set instead of failing.
    """
    value = int(raw)
    if value < 1:
        raise argparse.ArgumentTypeError("--limit must be 1 or greater")
    return value
