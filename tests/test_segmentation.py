"""episode-texttiling-v1 must be deterministic, reset-aware and bounded."""

from atrium.synthesize.episode_identity import episode_identity
from atrium.synthesize.segment_episodes import segment_episodes


def _message(index, role, text):
    return {"id": f"e{index}", "kind": "message", "role": role, "text": text}


def _session(topic_a_turns=4, topic_b_turns=4):
    events = []
    for i in range(topic_a_turns):
        events.append(
            _message(len(events), "user", f"la factura de acme del trimestre {i} falta")
        )
        events.append(_message(len(events), "assistant", "reviso acme"))
    for i in range(topic_b_turns):
        events.append(
            _message(len(events), "user", f"el deploy de server-a con docker fallo otra vez {i}")
        )
        events.append(_message(len(events), "assistant", "miro el deploy"))
    return events


def test_segmentation_is_deterministic():
    events = _session()
    first = segment_episodes(events)
    second = segment_episodes(events)
    assert first == second


def test_every_event_lands_in_exactly_one_episode():
    events = _session()
    episodes = segment_episodes(events)
    covered = [i for e in episodes for i in e["event_indexes"]]
    assert sorted(covered) == list(range(len(events)))
    assert len(covered) == len(set(covered))


def test_a_reset_marker_always_cuts():
    events = [
        _message(0, "user", "primera tarea sobre facturas"),
        _message(1, "assistant", "hecho"),
        _message(2, "user", "/clear"),
        _message(3, "user", "ahora otra cosa distinta"),
    ]
    episodes = segment_episodes(events)
    assert len(episodes) >= 2
    assert episodes[0]["event_indexes"] == [0, 1]


def test_an_oversized_episode_keeps_one_identity_with_map_chunks():
    huge = "palabra " * 30_000
    events = [
        _message(0, "user", huge),
        _message(1, "assistant", huge),
        _message(2, "user", huge),
    ]
    episodes = segment_episodes(events)
    oversized = [e for e in episodes if len(e["chunks"]) > 1]
    assert oversized, "the ceiling must produce map chunks, not silence"
    for episode in oversized:
        flattened = [i for chunk in episode["chunks"] for i in chunk]
        assert flattened == episode["event_indexes"]


def test_episode_identity_is_stable_and_cutter_versioned():
    ids = ["e0", "e1", "e2"]
    assert episode_identity("conv", ids) == episode_identity("conv", ids)
    assert episode_identity("conv", ids) != episode_identity("other", ids)
    assert episode_identity("conv", ids) != episode_identity("conv", ids[:2])


def test_events_without_messages_segment_to_nothing():
    assert segment_episodes([]) == []
    assert segment_episodes([{"kind": "artifact"}]) == []
