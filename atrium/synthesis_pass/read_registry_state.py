"""Read the registry once into the sets a pass consults."""

from atrium.synthesis_pass.registry_state import RegistryState
from atrium.synthesize.default_registry import default_registry


def read_registry_state(*, include_session_covered: bool) -> RegistryState:
    """Index every record by episode, result and (conversation, revision)."""
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
    return RegistryState(done_episodes, covered, recorded_results, recorded_revisions)
