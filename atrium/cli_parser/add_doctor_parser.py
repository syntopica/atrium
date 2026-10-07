"""Register the `doctor` subcommand on the atrium parser."""

from pathlib import Path

from atrium.cli_parser.sub_parsers import SubParsers


def add_doctor_parser(subcommands: SubParsers, archive: Path) -> None:
    """Register `doctor` and its flags."""
    doctor = subcommands.add_parser(
        "doctor", help="Check whether the memory would answer from a world that still exists"
    )
    doctor.add_argument("--archive", type=Path, default=archive)
    doctor.add_argument(
        "--json",
        action="store_true",
        help="Print checks as JSON (name, ok, severity, fixed code) instead of prose",
    )
    doctor.add_argument(
        "--publish",
        action="store_true",
        help="Also publish status/doctor.json atomically. Only the refresh job passes "
        "this, at its end: the run costs minutes, too slow for a reader to poll",
    )
