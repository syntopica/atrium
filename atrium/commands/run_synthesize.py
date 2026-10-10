"""The `synthesize` handler of the atrium CLI."""

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from atrium.synthesis_pass.conversations_in_workspace import conversations_in_workspace
from atrium.synthesis_pass.holding_conversations import holding_conversations
from atrium.synthesis_pass.make_conversation_runner import make_conversation_runner
from atrium.synthesis_pass.newest_conversations import newest_conversations
from atrium.synthesis_pass.publish_pass_status import publish_pass_status
from atrium.synthesis_pass.read_registry_state import read_registry_state
from atrium.synthesis_pass.select_producer_lane import select_producer_lane
from atrium.synthesize.default_registry import default_registry
from atrium.synthesize.prune_partials import prune_partials
from atrium.synthesize.started_conversations import started_conversations


def run_synthesize(  # noqa: PLR0913, PLR0917 -- the CLI surface: each argument is one flag
    archive: Path,
    limit: int | None,
    dry_run: bool,
    producer: str,
    workers: int,
    model: str | None = None,
    effort: str | None = None,
    project: Path | None = None,
    workspace: str | None = None,
    *,
    include_session_covered: bool = False,
) -> int:
    """Synthesize episodes newest-first; resumable, so interruption is cheap.

    Conversations run in a small worker pool: registry writes are atomic and
    never overwrite, so the worst a race costs is one duplicate call.

    ``project`` and ``workspace`` narrow the pass to one project. Whole-corpus
    coverage costs about a dozen weekly quota cycles, while the projects that
    actually lack memory are a handful -- `status --coverage` names them, and
    this is how one gets filled without paying for the other 145,000 episodes.
    ``workspace`` takes the stored prefix directly, which is the only form that
    reaches a project whose directory is gone: three of the five largest
    uncovered projects here no longer exist on disk, and their conversations
    are exactly the ones nothing but this archive can still account for.
    """
    from atrium.recall.project_workspace import project_workspace
    from atrium.synthesize.is_trivial_episode import is_trivial_episode
    from atrium.synthesize.segment_episodes import segment_episodes

    target = workspace
    if project is not None:
        target = project_workspace(project)
        if target is None:
            print(f"  {project} is in no repository, so it names no project")
            return 1

    conversations = newest_conversations(archive)
    if target is not None:
        conversations = conversations_in_workspace(conversations, target)
        print(f"  {len(conversations)} conversations in {target}")
    if limit is not None:
        conversations = conversations[:limit]
    if dry_run:
        episodes = sum(
            not is_trivial_episode(episode["event_indexes"], c.get("events") or [])
            for c in conversations
            for episode in segment_episodes(c.get("events") or [])
        )
        print(f"  {len(conversations)} conversations -> {episodes} episodes (no calls made)")
        return 0
    # A worker lane journals each job it submits against its conversation, so
    # a later pass can find which conversation an uncollected result is for.
    journal = default_registry() / "worker-submissions.jsonl"
    lane = select_producer_lane(producer, model, effort)
    state = read_registry_state(include_session_covered=include_session_covered)
    partials = default_registry() / "partials"
    pruned = prune_partials(partials)
    if pruned:
        print(f"  pruned {pruned} kept partials older than 30 days")
    holding: set[str] = set()
    if lane.worker_queue is not None:
        holding = holding_conversations(lane.worker_queue, state.recorded_results, journal)
        if holding:
            print(
                f"  {len(holding)} conversations hold uncollected worker results; walking them first"
            )
    # A conversation that kept and acked its map chunks holds no worker result
    # any more, so only its started marker says it is half done. It goes first
    # too, but unlike a holding one it still stops at a quota wall.
    unfinished = started_conversations(partials) - holding
    if unfinished:
        print(f"  {len(unfinished)} conversations were left half done; walking them next")
    conversations.sort(
        key=lambda conversation: (
            conversation["id"] not in holding,
            conversation["id"] not in unfinished,
        )
    )
    made = skipped = failed = deferred = trivial = 0
    total = len(conversations)
    started = time.time()
    run_one = make_conversation_runner(lane, state, holding, journal, total)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(run_one, enumerate(conversations, start=1)):
            made += result["synthesized"]
            skipped += result["skipped"]
            failed += result["failed"]
            deferred += result.get("deferred", 0)
            trivial += result.get("trivial", 0)
    print(
        f"  synthesized {made}, already present {skipped}, failed conversations {failed}, "
        f"deferred {deferred}, harness echoes not synthesized {trivial}, "
        f"registry {default_registry()}"
    )
    publish_pass_status(
        producer, started, time.time(), (total, made, skipped, failed, deferred, trivial)
    )
    return 0 if failed == 0 else 1
