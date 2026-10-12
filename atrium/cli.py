"""Atrium command line — the core surface every adapter wraps."""

import sys

from atrium.cli_parser.build_parser import build_parser
from atrium.commands.run_command import run_command
from atrium.erase.hold_writer_gate import hold_writer_gate
from atrium.erase.writes_instance import writes_instance
from atrium.state.archive_path import archive_path
from atrium.state.state_directory import state_directory


def main(argv: list[str] | None = None) -> int:
    """Parse one subcommand and run it, under the erase lock when it writes."""
    # Resolved here, not at import: the instance is chosen by the environment
    # and the working directory of this invocation, and the archive of an
    # instance sits beside its config, never under the home directory.
    state = state_directory()
    refresh_stamp = state / "last-refresh"
    archive = archive_path()
    parser = build_parser(state, archive, refresh_stamp, __doc__)
    args = parser.parse_args(argv)
    if not writes_instance(args):
        return run_command(args, parser, state, refresh_stamp, archive)
    try:
        gate = hold_writer_gate(state)
    except BlockingIOError:
        print("refused: an erase holds the instance; run again after it", file=sys.stderr)
        return 3
    with gate:
        return run_command(args, parser, state, refresh_stamp, archive)


if __name__ == "__main__":
    sys.exit(main())
