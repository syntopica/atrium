"""Harness <system-reminder> blocks are not the person's words and never reach the index."""

from atrium.ingest.admission_tally import AdmissionTally
from atrium.ingest.to_records import to_records

REMINDER = "<system-reminder>\nAccount context the harness injected.\n</system-reminder>"
SECOND = "<system-reminder>second block</system-reminder>"


def _texts(role, text):
    conversation = {
        "id": "conv-1",
        "source": "claude-code",
        "startedAt": "2026-08-01T00:00:00Z",
        "provenance": {"contentSha256": "abc123"},
        "events": [{"id": "e1", "kind": "message", "role": role, "text": text}],
    }
    tally = AdmissionTally()
    return [r.text for r in to_records(conversation, tally)], tally


def test_a_turn_of_only_reminders_yields_no_record():
    texts, tally = _texts("user", REMINDER + "\n" + SECOND)
    assert texts == []
    assert tally.admitted == {}


def test_person_text_after_a_reminder_is_kept():
    assert _texts("user", REMINDER + "\nWhy does the deploy fail?")[0] == [
        "Why does the deploy fail?"
    ]


def test_person_text_before_a_reminder_is_kept():
    assert _texts("user", "Why does the deploy fail?\n" + REMINDER)[0] == [
        "Why does the deploy fail?"
    ]


def test_two_reminders_around_person_text_are_both_stripped():
    assert _texts("user", REMINDER + "\nFix the build.\n" + SECOND)[0] == ["Fix the build."]


def test_an_unterminated_tag_does_not_swallow_person_text():
    text = "<system-reminder>never closed. Why does the deploy fail?"
    assert _texts("user", text)[0] == [text]


def test_assistant_text_is_left_alone():
    text = "Quoting the tag: " + REMINDER
    assert _texts("assistant", text)[0] == [text]
