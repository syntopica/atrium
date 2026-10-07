"""Register the `status` subcommand on the atrium parser."""

from pathlib import Path

from atrium.cli_parser.sub_parsers import SubParsers


def add_status_parser(subcommands: SubParsers, archive: Path, refresh_stamp: Path) -> None:
    """Register `status` and its flags."""
    status = subcommands.add_parser("status", help="Show what the index holds, and how stale")
    status.add_argument("--archive", type=Path, default=archive)
    status.add_argument("--refresh-stamp", type=Path, default=refresh_stamp)
    status.add_argument("--synthesis-registry", type=Path, default=None)
    status.add_argument(
        "--coverage",
        action="store_true",
        help="Also report how many real projects have synthesized memory. Off by "
        "default: it scans every record and costs ~44s, and the answer moves slowly",
    )
    status.add_argument(
        "--publish",
        action="store_true",
        help="Also publish status/refresh.json atomically. Only the refresh job passes "
        "this, at its end, so the file has exactly one writer",
    )
    status.add_argument(
        "--json",
        action="store_true",
        help="Print the same redacted document --publish writes (counts, ages, "
        "populations) instead of the text report",
    )
