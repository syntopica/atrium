"""The `synthesize` handler of the atrium CLI."""

import os
from pathlib import Path
from typing import Any

from atrium.ingest.read_archive import read_archive
from atrium.ingest.workspace_aliases import workspace_aliases
from atrium.state.state_directory import state_directory
from atrium.synthesize.default_registry import default_registry


def run_synthesize(  # noqa: PLR0912, PLR0913, PLR0917, PLR0915 -- the CLI surface: each argument is one flag
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
    import functools
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    from atrium.ingest.canonical_workspace import canonical_workspace
    from atrium.recall.project_workspace import project_workspace
    from atrium.recall.workspace_matches import workspace_matches
    from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError
    from atrium.synthesize.record_worker_submission import record_worker_submission
    from atrium.synthesize.segment_episodes import segment_episodes
    from atrium.synthesize.synthesize_conversation import synthesize_conversation

    target = workspace
    if project is not None:
        target = project_workspace(project)
        if target is None:
            print(f"  {project} is in no repository, so it names no project")
            return 1

    conversations = sorted(
        read_archive(archive),
        key=lambda c: c.get("updatedAt") or c.get("startedAt") or "",
        reverse=True,
    )
    if target is not None:
        # The same aliases the ingest applies, or this filter would miss exactly
        # the renamed history that makes a project whole: project-after's first
        # month is archived under `p/project-before`.
        aliases = workspace_aliases()
        conversations = [
            conversation
            for conversation in conversations
            if workspace_matches(
                canonical_workspace(
                    conversation.get("workspace"),
                    aliases=aliases,
                    started_at=conversation.get("startedAt"),
                ),
                target,
            )
        ]
        print(f"  {len(conversations)} conversations in {target}")
    if limit is not None:
        conversations = conversations[:limit]
    if dry_run:
        episodes = sum(len(segment_episodes(c.get("events") or [])) for c in conversations)
        print(f"  {len(conversations)} conversations -> {episodes} episodes (no calls made)")
        return 0
    worker_queue: str | None = None
    # A worker lane journals each job it submits against its conversation, so
    # a later pass can find which conversation an uncollected result is for.
    journal = default_registry() / "worker-submissions.jsonl"
    if producer == "max":
        from atrium.synthesize.max_lane_call import MODEL, max_lane_call
        from atrium.synthesize.max_lane_tokens import max_lane_tokens

        tokens = max_lane_tokens()

        def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
            return max_lane_call(tokens, system_text, user_text, tool)

        model_id = MODEL
    elif producer == "codex":
        from atrium.synthesize.codex_lane_call import codex_lane_call
        from atrium.synthesize.codex_lane_model_id import codex_lane_model_id

        def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
            return codex_lane_call(system_text, user_text, tool, model, effort)

        model_id = codex_lane_model_id(model, effort)
    elif producer == "local":
        from atrium.synthesize.lane_prompt import LanePrompt
        from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL, local_lane_call
        from atrium.synthesize.local_lane_model_id import local_lane_model_id

        local_model = model or LOCAL_DEFAULT_MODEL

        if os.environ.get("ATRIUM_LOCAL_TRANSPORT") == "worker":
            from atrium.synthesize.worker_lane_call import (
                WORKER_SYNTHESIS_QUEUE,
                worker_lane_call,
            )

            worker_queue = WORKER_SYNTHESIS_QUEUE

            def journaled_call(
                system_text: str, user_text: str, tool: dict[str, Any], on_submit: Any
            ) -> dict[str, Any]:
                return worker_lane_call(
                    LanePrompt(system_text, user_text), tool, local_model, on_submit
                )

            def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
                return journaled_call(system_text, user_text, tool, None)
        else:

            def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
                return local_lane_call(LanePrompt(system_text, user_text), tool, local_model)

        model_id = local_lane_model_id(local_model)
    elif producer == "task":
        from atrium.synthesize.lane_prompt import LanePrompt
        from atrium.synthesize.worker_task_lane_call import (
            WORKER_TASK_DEFAULT_PROFILE,
            WORKER_TASK_QUEUE,
            worker_task_lane_call,
        )
        from atrium.synthesize.worker_task_lane_model_id import worker_task_lane_model_id

        task_profile = model or WORKER_TASK_DEFAULT_PROFILE
        worker_queue = WORKER_TASK_QUEUE

        def journaled_call(
            system_text: str, user_text: str, tool: dict[str, Any], on_submit: Any
        ) -> dict[str, Any]:
            return worker_task_lane_call(
                LanePrompt(system_text, user_text), tool, task_profile, on_submit
            )

        def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
            return journaled_call(system_text, user_text, tool, None)

        model_id = worker_task_lane_model_id(task_profile)
    else:
        from atrium.synthesize.agy_lane_call import AGY_MODEL_ID, agy_lane_call
        from atrium.synthesize.agy_lane_model_id import agy_lane_model_id

        agy_model = model or AGY_MODEL_ID

        def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
            return agy_lane_call(system_text, user_text, tool, agy_model)

        model_id = agy_lane_model_id(agy_model)

    from atrium.session.session_covered_conversations import session_covered_conversations
    from atrium.synthesize.read_records import read_records

    done_episodes: set[str] = set()
    covered: set[str] = set()
    session_records = []
    recorded_results: set[str] = set()
    # (conversation, revision) pairs some record already synthesized: after a
    # wall, the cheap test for "nothing new here". Segmenting every remaining
    # conversation to count exact episodes took minutes, past the tick's box.
    recorded_revisions: set[tuple[str, str]] = set()
    for record in read_records(default_registry()):
        done_episodes.add(record["episode_id"])
        recorded_revisions.add(
            (record.get("conversation_id") or "", record.get("revision_sha256") or "")
        )
        recorded_results.update(r["result_id"] for r in record.get("worker_results") or [])
        if record.get("segmentation") == "session-self-v1":
            session_records.append(record)
    if not include_session_covered:
        covered = session_covered_conversations(session_records)
    holding: set[str] = set()
    if worker_queue is not None:
        from atrium.synthesize.ack_recorded_worker_results import ack_recorded_worker_results
        from atrium.synthesize.pending_worker_jobs import pending_worker_jobs
        from atrium.synthesize.read_worker_submissions import read_worker_submissions

        settled = ack_recorded_worker_results(worker_queue, recorded_results)
        if settled:
            print(f"  acked {settled} worker results the registry already held")
        # Results a pass stopped waiting for arrive unacknowledged and hold a
        # queue slot each. Walk their conversations first: re-submitting one
        # finds its job by idempotency key and collects the result, which a
        # full queue does not refuse. Left to the newest-first walk, they sat
        # behind the first refused submission until the worker expired them.
        submissions = read_worker_submissions(journal)
        holding = {
            submissions[job] for job in pending_worker_jobs(worker_queue) if job in submissions
        }
        if holding:
            print(
                f"  {len(holding)} conversations hold uncollected worker results; walking them first"
            )
            conversations.sort(key=lambda conversation: conversation["id"] not in holding)
    made = skipped = failed = deferred = 0
    total = len(conversations)
    started = time.time()
    # Once the quota window is spent (or the worker's queue is full, or every
    # runner rests) nothing left in the pass can succeed: stop calling, count
    # the rest as deferred -- still pending, not failed -- and let a later tick
    # pick them up instead of grinding failures.
    quota_wall = threading.Event()

    def run_one(item: tuple[int, dict[str, Any]]) -> dict[str, int]:
        position, conversation = item
        collecting = conversation["id"] in holding
        walled = quota_wall.is_set() and not collecting
        revision = (conversation.get("provenance") or {}).get("contentSha256") or ""
        # After a wall, a conversation already synthesized at its current
        # revision is present, not deferred: deferred means work left undone.
        if conversation["id"] in covered or (
            walled and (conversation["id"], revision) in recorded_revisions
        ):
            # Covered: the session that lived it already recorded it.
            return {"synthesized": 0, "skipped": 1, "failed": 0}
        if walled:
            return {"synthesized": 0, "skipped": 0, "failed": 0, "deferred": 1}
        producer_call = call
        if worker_queue is not None:
            on_submit = functools.partial(
                record_worker_submission, journal, conversation_id=conversation["id"]
            )
            producer_call = functools.partial(journaled_call, on_submit=on_submit)
        try:
            result = synthesize_conversation(
                conversation, producer_call, model_id, default_registry(), done_episodes
            )
        except QuotaExhaustedError as error:
            if collecting:
                # Only this conversation's new chunk was refused: the others
                # holding results are walked next and must not be stranded.
                print(f"  [{position}/{total}] queue full while collecting: {error}", flush=True)
                return {"synthesized": 0, "skipped": 0, "failed": 0, "deferred": 1}
            if not quota_wall.is_set():
                quota_wall.set()
                print(f"  [{position}/{total}] quota wall, aborting pass: {error}", flush=True)
            return {"synthesized": 0, "skipped": 0, "failed": 0, "deferred": 1}
        except Exception as error:
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
            deferred += result.get("deferred", 0)
    print(
        f"  synthesized {made}, already present {skipped}, failed conversations {failed}, "
        f"deferred {deferred}, "
        f"registry {default_registry()}"
    )
    from atrium.status.publish_json_atomically import publish_json_atomically
    from atrium.status.status_file import status_file
    from atrium.status.synthesis_pass import SynthesisPass
    from atrium.status.synthesis_status import synthesis_status

    finished = time.time()
    publish_json_atomically(
        status_file(state_directory(), "synthesis"),
        synthesis_status(
            SynthesisPass(producer, started, finished, total, made, skipped, failed, deferred),
            finished,
        ),
    )
    return 0 if failed == 0 else 1
