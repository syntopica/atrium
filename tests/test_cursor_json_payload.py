"""The contract object is the last thing said, and narration does not break it."""

from atrium.synthesize.cursor_json_payload import cursor_json_payload


def test_the_last_object_wins_over_narration() -> None:
    text = 'I will return {"shape": "like this"} at the end.{"title": "t", "facts": []}'
    assert cursor_json_payload(text) == {"title": "t", "facts": []}


def test_braces_inside_strings_do_not_unbalance_the_scan() -> None:
    text = '{"title": "a {b} c", "summary": "}"}'
    assert cursor_json_payload(text) == {"title": "a {b} c", "summary": "}"}


def test_a_stray_quote_in_narration_does_not_swallow_the_object() -> None:
    text = 'He said "fine and moved on.\n{"title": "t"}'
    assert cursor_json_payload(text) == {"title": "t"}


def test_a_code_fence_is_not_an_obstacle() -> None:
    assert cursor_json_payload('```json\n{"title": "t"}\n```') == {"title": "t"}


def test_no_object_is_none() -> None:
    assert cursor_json_payload("Sorry, I cannot answer that.") is None


def test_an_unparseable_candidate_falls_back_to_the_previous_one() -> None:
    assert cursor_json_payload('{"ok": 1} then {broken}') == {"ok": 1}


def test_a_bare_array_is_not_an_object() -> None:
    assert cursor_json_payload('[{"title": "t"}]') == {"title": "t"}
