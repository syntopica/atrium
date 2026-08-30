"""Atrium command line — the core surface every adapter wraps."""

import argparse
import sys
from pathlib import Path

from atrium.ingest.read_archive import read_archive
from atrium.ingest.read_notes import read_notes
from atrium.ingest.to_note_records import to_note_records
from atrium.ingest.to_records import to_records
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

    synthesize = subcommands.add_parser(
        "synthesize", help="Synthesize archive episodes into the registry (Max lane)"
    )
    synthesize.add_argument("archive", type=Path)
    synthesize.add_argument("--limit", type=_positive_limit, default=None)
    synthesize.add_argument("--dry-run", action="store_true")
    synthesize.add_argument(
        "--producer",
        choices=("agy", "codex", "max"),
        default="agy",
        help="agy: Gemini bulk quota via the Antigravity CLI (default -- the "
        "standing routing rule for whole-corpus passes); codex: the Codex "
        "CLI's quota; max: the Claude Max OAuth lane",
    )
    synthesize.add_argument("--workers", type=_positive_limit, default=3)

    subcommands.add_parser("ingest-synthesis", help="Index every synthesis record in the registry")

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

    recall = subcommands.add_parser(
        "recall", help="Render this project's session-start recall block"
    )
    recall.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Directory whose project to recall (default: the working directory)",
    )
    recall.add_argument("--limit", type=_positive_limit, default=12)

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
    if args.command == "synthesize":
        return _synthesize(args.archive, args.limit, args.dry_run, args.producer, args.workers)
    if args.command == "ingest-synthesis":
        return _ingest_synthesis(args.index)
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
    if args.command == "recall":
        return _recall(args.index, args.cwd, args.limit)
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
    unchanged = 0
    removed = 0
    seen_by_provider: dict[str, set[str]] = {}
    try:
        with connection:
            for conversation in read_archive(archive):
                conversations += 1
                written = write_conversation(
                    connection, conversation["id"], to_records(conversation)
                )
                total += written
                unchanged += written == 0
                provider = conversation.get("source") or "unknown"
                seen_by_provider.setdefault(provider, set()).add(conversation["id"])
            if sweep:
                for provider, seen in seen_by_provider.items():
                    removed += delete_absent_conversations(connection, provider, seen)
    finally:
        connection.close()
    swept = f", {removed} absent removed" if removed else ""
    skipped = f", {unchanged} conversations unchanged" if unchanged else ""
    print(f"  {conversations} conversations -> {total} records written at {index}{skipped}{swept}")
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
    from atrium.store.commit_with_retry import commit_with_retry
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
            rows = [(rid, sha) for rid, sha, _ in batch]
            written += commit_with_retry(
                connection, lambda rows=rows, matrix=matrix: write_vectors(connection, rows, matrix)
            )
            processed += len(batch)
            print(f"  embedded {written}/{len(pending)}", flush=True)
    finally:
        connection.close()
    if written < processed:
        print(f"  {processed - written} superseded mid-run and skipped; run embed again")
    return 0


def _synthesize(
    archive: Path, limit: int | None, dry_run: bool, producer: str, workers: int
) -> int:
    """Synthesize episodes newest-first; resumable, so interruption is cheap.

    Conversations run in a small worker pool: registry writes are atomic and
    never overwrite, so the worst a race costs is one duplicate call.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from atrium.synthesize.quota_exhausted import QuotaExhausted
    from atrium.synthesize.segment_episodes import segment_episodes
    from atrium.synthesize.synthesis_registry import DEFAULT_REGISTRY
    from atrium.synthesize.synthesize_conversation import synthesize_conversation

    conversations = sorted(
        read_archive(archive),
        key=lambda c: c.get("updatedAt") or c.get("startedAt") or "",
        reverse=True,
    )
    if limit is not None:
        conversations = conversations[:limit]
    if dry_run:
        episodes = sum(len(segment_episodes(c.get("events") or [])) for c in conversations)
        print(f"  {len(conversations)} conversations -> {episodes} episodes (no calls made)")
        return 0
    if producer == "max":
        from atrium.synthesize.max_lane_call import MODEL, max_lane_call
        from atrium.synthesize.max_lane_tokens import max_lane_tokens

        tokens = max_lane_tokens()

        def call(system_text, user_text, tool):
            return max_lane_call(tokens, system_text, user_text, tool)

        model_id = MODEL
    elif producer == "codex":
        from atrium.synthesize.codex_lane_call import CODEX_MODEL_ID, codex_lane_call

        call = codex_lane_call
        model_id = CODEX_MODEL_ID
    else:
        from atrium.synthesize.agy_lane_call import AGY_MODEL_ID, agy_lane_call

        call = agy_lane_call
        model_id = AGY_MODEL_ID

    from atrium.synthesize.synthesis_registry import read_records

    done_episodes = {record["episode_id"] for record in read_records(DEFAULT_REGISTRY)}
    made = skipped = failed = 0
    total = len(conversations)
    # Once the quota window is spent nothing left in the pass can succeed:
    # stop calling, count the rest as failed (still pending), and let the
    # outer drip loop sleep until the reset instead of grinding failures.
    quota_wall = threading.Event()

    def run_one(item):
        position, conversation = item
        if quota_wall.is_set():
            return {"synthesized": 0, "skipped": 0, "failed": 1}
        try:
            result = synthesize_conversation(
                conversation, call, model_id, DEFAULT_REGISTRY, done_episodes
            )
        except QuotaExhausted as error:
            if not quota_wall.is_set():
                quota_wall.set()
                print(f"  [{position}/{total}] quota wall, aborting pass: {error}", flush=True)
            return {"synthesized": 0, "skipped": 0, "failed": 1}
        except Exception as error:  # noqa: BLE001 -- keep the run alive; the episode stays pending
            print(f"  [{position}/{total}] {conversation['id'][:12]} FAILED: {error}", flush=True)
            return {"synthesized": 0, "skipped": 0, "failed": 1}
        print(
            f"  [{position}/{total}] {conversation['id'][:12]} "
            f"+{result['synthesized']} (skipped {result['skipped']})",
            flush=True,
        )
        return {**result, "failed": 0}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(run_one, enumerate(conversations, start=1)):
            made += result["synthesized"]
            skipped += result["skipped"]
            failed += result["failed"]
    print(
        f"  synthesized {made}, already present {skipped}, failed conversations {failed}, "
        f"registry {DEFAULT_REGISTRY}"
    )
    return 0 if failed == 0 else 1


def _ingest_synthesis(index: Path) -> int:
    """Index one record per episode; same sweep contract as the other ingests.

    Several recipe populations may hold the same episode (different producers,
    different job keys). The active-recipe manifest picks which one the index
    serves, so coexistence in the registry never becomes a duplicate -- or a
    primary-key collision -- in the index.
    """
    from atrium.ingest.conversation_workspaces import conversation_workspaces
    from atrium.ingest.to_synthesis_records import to_synthesis_records
    from atrium.synthesize.active_recipe import active_recipe_priority
    from atrium.synthesize.synthesis_registry import DEFAULT_REGISTRY, read_records

    priority = active_recipe_priority(DEFAULT_REGISTRY)
    rank = {model: position for position, model in enumerate(priority)}
    chosen: dict[str, dict] = {}
    for record in read_records(DEFAULT_REGISTRY):
        episode = record["episode_id"]
        record_rank = rank.get(record.get("model_requested"), len(priority))
        best = chosen.get(episode)
        if best is None or record_rank < rank.get(best.get("model_requested"), len(priority)):
            chosen[episode] = record

    connection = open_store(index)
    total = 0
    unchanged = 0
    seen: set[str] = set()
    try:
        # Read the workspaces before writing anything: the map comes from the
        # raw conversations, which this pass never touches.
        workspaces = conversation_workspaces(connection)
        by_conversation: dict[str, list] = {}
        for record in chosen.values():
            workspace = workspaces.get(record["conversation_id"])
            for row in to_synthesis_records(record, workspace):
                by_conversation.setdefault(row.conversation_id, []).append(row)
        with connection:
            for conversation_id, rows in sorted(by_conversation.items()):
                written = write_conversation(connection, conversation_id, rows)
                total += written
                unchanged += written == 0
                seen.add(conversation_id)
            removed = delete_absent_conversations(connection, "synthesis", seen)
    finally:
        connection.close()
    swept = f", {removed} absent removed" if removed else ""
    skipped = f", {unchanged} unchanged" if unchanged else ""
    print(f"  {len(seen)} conversations -> {total} synthesis records written{skipped}{swept}")
    return 0


def _search(index: Path, query: str, limit: int, lane: str) -> int:
    from atrium.retrieve.search import search

    connection = open_store(index, read_only=True)
    hits = search(connection, query, limit, lane)
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


def _recall(index: Path, cwd: Path, limit: int) -> int:
    """Print the recall block for the project containing ``cwd``.

    Prints nothing and succeeds when the project has no synthesized episodes.
    A session start calls this, and a hook forced to tell "no memory" from
    "recall is broken" by reading prose would get it wrong: silence is the
    correct injection for a project nothing is known about.
    """
    from atrium.recall.project_workspace import project_workspace
    from atrium.recall.recent_episodes import recent_episodes
    from atrium.recall.render_snapshot import render_snapshot

    if not index.exists():
        return 0
    project = project_workspace(cwd)
    connection = open_store(index, read_only=True)
    try:
        hits = recent_episodes(connection, project, limit)
    finally:
        connection.close()
    block = render_snapshot(project, hits)
    if block:
        print(block)
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
