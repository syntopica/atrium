"""Atrium command line — the core surface every adapter wraps."""

import argparse
import sys
from pathlib import Path

from atrium.ingest.read_archive import read_archive
from atrium.ingest.read_notes import read_notes
from atrium.ingest.to_note_records import to_note_records
from atrium.ingest.to_records import to_records
from atrium.retrieve.search_substrings import search_substrings
from atrium.retrieve.search_words import search_words
from atrium.store.delete_absent_conversations import delete_absent_conversations
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation

DEFAULT_INDEX = Path.home() / ".atrium" / "index.sqlite3"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atrium", description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    subcommands = parser.add_subparsers(dest="command", required=True)

    ingest = subcommands.add_parser("ingest", help="Index a canonical archive")
    ingest.add_argument("archive", type=Path)
    ingest.add_argument(
        "--partial",
        action="store_true",
        help="The archive is a slice, not a source's full export: skip the sweep "
        "that removes conversations absent from it",
    )

    notes = subcommands.add_parser("ingest-notes", help="Index a tree of curated markdown notes")
    notes.add_argument("root", type=Path)
    notes.add_argument("--provider", default="brain")
    notes.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="DIR",
        help="Directory name to skip anywhere under the root (repeatable)",
    )
    notes.add_argument(
        "--partial",
        action="store_true",
        help="The root is a slice of the provider's notes: skip the sweep that "
        "removes notes absent from it",
    )

    subcommands.add_parser("embed", help="Embed semantic-layer records that lack a vector")

    search = subcommands.add_parser("search", help="Search the index")
    search.add_argument("query")
    search.add_argument("--limit", type=_positive_limit, default=10)
    lanes = search.add_mutually_exclusive_group()
    lanes.add_argument(
        "--substring",
        action="store_true",
        help="Match fragments inside words instead of whole words",
    )
    lanes.add_argument("--words", action="store_true", help="Lexical lane only, no fusion")
    lanes.add_argument("--dense", action="store_true", help="Semantic lane only, no fusion")

    subcommands.add_parser("status", help="Show what the index holds")

    args = parser.parse_args(argv)
    if args.command == "ingest":
        return _ingest(args.index, args.archive, sweep=not args.partial)
    if args.command == "ingest-notes":
        return _ingest_notes(
            args.index, args.root, args.provider, tuple(args.exclude), sweep=not args.partial
        )
    if args.command == "embed":
        return _embed(args.index)
    if args.command == "search":
        lane = (
            "substring"
            if args.substring
            else "words"
            if args.words
            else "dense"
            if args.dense
            else "auto"
        )
        return _search(args.index, args.query, args.limit, lane)
    return _status(args.index)


def _ingest(index: Path, archive: Path, *, sweep: bool = True) -> int:
    """Index an archive, or change nothing at all.

    One transaction for the whole run. A malformed line partway through an
    archive must not leave the index holding half a revision: the previous
    behaviour committed each conversation as it went, so a mid-file failure left
    records written but unsearchable, and the operator saw an error next to an
    index that looked populated.

    An archive is a source's full export, so after ingesting it the index must
    hold exactly its conversations for the providers it carries: conversations
    deleted or redacted away upstream never appear in the new input, and only
    the sweep removes them. `--partial` opts out for deliberate slices.
    """
    connection = open_store(index)
    total = 0
    conversations = 0
    removed = 0
    seen_by_provider: dict[str, set[str]] = {}
    try:
        with connection:
            for conversation in read_archive(archive):
                conversations += 1
                total += write_conversation(
                    connection, conversation["id"], to_records(conversation)
                )
                provider = conversation.get("source") or "unknown"
                seen_by_provider.setdefault(provider, set()).add(conversation["id"])
            if sweep:
                for provider, seen in seen_by_provider.items():
                    removed += delete_absent_conversations(connection, provider, seen)
    finally:
        connection.close()
    swept = f", {removed} absent removed" if removed else ""
    print(f"  {conversations} conversations -> {total} records indexed at {index}{swept}")
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


def _ingest_notes(
    index: Path,
    root: Path,
    provider: str,
    exclude: tuple[str, ...],
    *,
    sweep: bool = True,
) -> int:
    """Index a curated notes tree, same transactional and sweep contract as `_ingest`."""
    connection = open_store(index)
    total = 0
    files = 0
    removed = 0
    seen: set[str] = set()
    try:
        with connection:
            for note in read_notes(root, exclude):
                files += 1
                total += write_conversation(
                    connection, note["path"], to_note_records(note, provider)
                )
                seen.add(note["path"])
            if sweep:
                removed = delete_absent_conversations(connection, provider, seen)
    finally:
        connection.close()
    swept = f", {removed} absent removed" if removed else ""
    print(f"  {files} notes -> {total} records indexed at {index}{swept}")
    return 0


def _embed(index: Path) -> int:
    """Embed every semantic-layer record that has no vector yet.

    Vectors commit per batch rather than per run: an interrupted embed keeps
    what it finished (each vector is valid alone), and the next run resumes
    from the missing ones.
    """
    from atrium.embed.embedder import Embedder
    from atrium.embed.semantic_roles import SEMANTIC_ROLES
    from atrium.store.write_vectors import write_vectors

    connection = open_store(index)
    placeholders = ",".join("?" for _ in SEMANTIC_ROLES)
    # Ordered by text length so each sub-batch pads to a similar length: the
    # ONNX graph's attention cost grows with the square of the padded length,
    # and one long chunk in a batch of short ones prices the whole batch at
    # the long one's padding.
    pending = connection.execute(
        f"SELECT record_id, source_sha256, text FROM records WHERE role IN ({placeholders}) "
        "AND record_id NOT IN (SELECT record_id FROM vectors) "
        "ORDER BY length(text), record_id",
        SEMANTIC_ROLES,
    ).fetchall()
    if not pending:
        connection.close()
        print("  nothing to embed")
        return 0
    embedder = Embedder()
    written = 0
    processed = 0
    try:
        for start in range(0, len(pending), 256):
            batch = pending[start : start + 256]
            matrix = embedder.embed([text for _, _, text in batch])
            with connection:
                written += write_vectors(connection, [(rid, sha) for rid, sha, _ in batch], matrix)
            processed += len(batch)
            print(f"  embedded {written}/{len(pending)}", flush=True)
    finally:
        connection.close()
    if written < processed:
        print(f"  {processed - written} superseded mid-run and skipped; run embed again")
    return 0


def _search(index: Path, query: str, limit: int, lane: str) -> int:
    connection = open_store(index, read_only=True)
    if lane == "substring":
        hits = search_substrings(connection, query, limit)
    elif lane == "words":
        hits = search_words(connection, query, limit)
    elif lane == "dense":
        from atrium.embed.embedder import Embedder
        from atrium.retrieve.search_dense import search_dense

        hits = search_dense(connection, Embedder().embed([query])[0], limit)
    else:
        from atrium.embed.embedder import Embedder
        from atrium.retrieve.search_hybrid import search_hybrid

        hits = search_hybrid(connection, Embedder(), query, limit)
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
    build = dict(connection.execute("SELECT key, value FROM build_metadata"))
    connection.close()
    print(f"  index: {index}")
    print(f"  built by: schema {build.get('schema')}, pipeline {build.get('pipeline')}")
    print(f"  records: {records:,}")
    for provider, count in providers:
        print(f"    {provider:<14} {count:>8,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
