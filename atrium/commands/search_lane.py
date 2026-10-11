"""Which lane the `search` flags select."""

import argparse


def search_lane(args: argparse.Namespace) -> str:
    """Return the lane named by the mutually exclusive flags, ``auto`` by default."""
    if args.substring:
        return "substring"
    if args.words:
        return "words"
    if args.dense:
        return "dense"
    return "auto"
