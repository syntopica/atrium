"""Say whether a parsed command writes a store that an erasure cleans."""

from argparse import Namespace

from atrium.erase.writer_commands import WRITER_COMMANDS


def writes_instance(args: Namespace) -> bool:
    """Return True for a command that writes the index, registry or curation.

    A dry run writes nothing, and `erase` takes the lock exclusively itself.
    """
    if args.command not in WRITER_COMMANDS:
        return False
    if args.command == "synthesize":
        return not args.dry_run
    if args.command == "rekey-synthesis":
        return bool(args.apply)
    return True
