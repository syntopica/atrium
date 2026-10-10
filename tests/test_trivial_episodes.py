from pathlib import Path

from atrium.synthesize.is_trivial_episode import is_trivial_episode
from atrium.synthesize.synthesize_conversation import synthesize_conversation

ECHO = "Structured output provided successfully"


def _conversation(events: list[dict]) -> dict:
    return {
        "id": "c" * 64,
        "source": "claude-code",
        "schemaVersion": 2,
        "provenance": {"contentSha256": "a" * 64},
        "startedAt": "2026-10-10T10:00:00Z",
        "events": events,
    }


def test_a_lone_harness_echo_is_trivial() -> None:
    assert is_trivial_episode([0], [{"role": "user", "text": ECHO}])


def test_a_short_lone_message_from_the_operator_is_not_trivial() -> None:
    text = "Please remember the deployment is paused until finance approves it"
    assert not is_trivial_episode([0], [{"role": "user", "text": text}])


def test_a_short_exchange_is_not_trivial() -> None:
    events = [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "hello"}]
    assert not is_trivial_episode([0, 1], events)


def test_a_trivial_episode_costs_no_call_and_writes_no_record(tmp_path: Path) -> None:
    calls = []

    def producer(_system: str, _user: str, _tool: dict) -> dict:
        calls.append(1)
        return {"input": {"title": "t", "summary": "s"}, "model": "fake", "usage": {}}

    counts = synthesize_conversation(
        _conversation([{"id": "e1", "kind": "message", "role": "user", "text": ECHO}]),
        producer,
        "fake",
        tmp_path,
    )
    assert calls == []
    assert counts == {"synthesized": 0, "skipped": 0, "trivial": 1}
    assert not (tmp_path / "partials").exists() or not list((tmp_path / "partials").rglob("*"))


def test_a_pass_line_carries_its_harness_echo_count() -> None:
    from atrium.ledger.parse_pass_log import parse_pass_log

    lines = [
        "2026-10-10 08:00:00 pass start: local --producer local --workers 4",
        "2026-10-10 08:05:00 pass done: local exit 0;  synthesized 1, already present 2, "
        "failed conversations 0, deferred 0, harness echoes not synthesized 5, registry /r",
        "2026-10-10 09:00:00 pass start: local --producer local --workers 4",
        "2026-10-10 09:05:00 pass done: local exit 0;  synthesized 1, already present 2, "
        "failed conversations 0, deferred 0, registry /r",
    ]
    new, old = parse_pass_log(lines)
    assert (new["synthesized"], new["trivial"]) == (1, 5)
    assert (old["synthesized"], old["trivial"]) == (1, None)


def test_the_published_status_carries_the_harness_echo_count() -> None:
    from atrium.status.synthesis_pass import SynthesisPass
    from atrium.status.synthesis_status import synthesis_status

    document = synthesis_status(SynthesisPass("local", 0.0, 1.0, 3, 1, 0, 0, 0, 2), 1.0)
    assert document["lastPass"]["trivial"] == 2
