"""Atrium command line — the core surface every adapter wraps."""

import argparse
import sys
from pathlib import Path

from atrium.ingest.read_archive import read_archive
from atrium.ingest.to_records import to_records
from atrium.retrieve.search_substrings import search_substrings
from atrium.retrieve.search_words import search_words
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation

DEFAULT_INDEX = Path.home() / ".atrium" / "index.sqlite3"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atrium", description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    subcommands = parser.add_subparsers(dest="command", required=True)

    ingest = subcommands.add_parser("ingest", help="Index a canonical archive")
    ingest.add_argument("archive", type=Path)

    search = subcommands.add_parser("search", help="Search the index")
    search.add_argument("query")
    search.add_argument("--limit", type=_positive_limit, default=10)
    search.add_argument(
        "--substring",
        action="store_true",
        help="Match fragments inside words instead of whole words",
    )

    subcommands.add_parser("status", help="Show what the index holds")

    args = parser.parse_args(argv)
    if args.command == "ingest":
        return _ingest(args.index, args.archive)
    if args.command == "search":
        return _search(args.index, args.query, args.limit, args.substring)
    return _status(args.index)


def _ingest(index: Path, archive: Path) -> int:
    """Index an archive, or change nothing at all.

    One transaction for the whole run. A malformed line partway through an
    archive must not leave the index holding half a revision: the previous
    behaviour committed each conversation as it went, so a mid-file failure left
    records written but unsearchable, and the operator saw an error next to an
    index that looked populated.
    """
    connection = open_store(index)
    total = 0
    conversations = 0
    try:
        with connection:
            for conversation in read_archive(archive):
                conversations += 1
                total += write_conversation(
                    connection, conversation["id"], to_records(conversation)
                )
    finally:
        connection.close()
    print(f"  {conversations} conversations -> {total} records indexed at {index}")
    return 0


def _positive_limit(raw: str) -> int:
    """Reject a limit that would uncap the query.

    SQLite treats a negative LIMIT as no limit, so `--limit -1` quietly returns
    the whole result set instead of failing.
    """
    value = int(raw)
    if value < 1:
        raise argparse.ArgumentTypeError("--limit must be 1 or greater")
    return value


def _search(index: Path, query: str, limit: int, substring: bool = False) -> int:
    connection = open_store(index, read_only=True)
    hits = (
        search_substrings(connection, query, limit)
        if substring
        else search_words(connection, query, limit)
    )
    connection.close()
    if not hits:
        print("  no matches")
        return 0
    for position, hit in enumerate(hits, start=1):
        stamp = (hit.authored_at or "")[:10]
        print(f"\n  [{position}] {hit.provider} {stamp}  score={hit.score:.3f} lane={hit.lane}")
        print(f"      {hit.text[:200].strip()}")
        print(f"      source: {hit.source_sha256[:12]} conversation: {hit.conversation_id[:12]}")
    return 0


def _status(index: Path) -> int:
    connection = open_store(index, read_only=True)
    records = connection.execute("SELECT count(*) FROM records").fetchone()[0]
    providers = connection.execute(
        "SELECT provider, count(*) FROM records GROUP BY provider ORDER BY 2 DESC"
    ).fetchall()
    connection.close()
    print(f"  index: {index}")
    print(f"  records: {records:,}")
    for provider, count in providers:
        print(f"    {provider:<14} {count:>8,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
