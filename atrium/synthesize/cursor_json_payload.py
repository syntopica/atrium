"""The last balanced JSON object inside a Cursor answer, parsed, or None."""

from typing import Any

from atrium.synthesize.end_of_json_string import end_of_json_string
from atrium.synthesize.parsed_json_object import parsed_json_object


def cursor_json_payload(text: str) -> dict[str, Any] | None:
    """Return the last JSON object in ``text`` that parses, or None.

    Cursor has no ``--output-schema``, so the contract is asked for in the
    prompt, and a tool-using model narrates before honouring it: the clips
    pipeline measured a ``result`` reading "Using the brain skill ... then
    return the required JSON.{...}" on its first real run (2026-09-11). The
    **last** balanced object is taken rather than the first because the
    narration quotes shapes of its own while the contract object is by
    construction the final thing said. Strings are skipped whole so a brace
    inside a title cannot unbalance the scan, and only inside an object,
    so a stray quote in the narration cannot swallow the rest of the text.
    """
    depth = 0
    start = -1
    last: dict[str, Any] | None = None
    index = 0
    while index < len(text):
        character = text[index]
        if character == '"' and depth > 0:
            index = end_of_json_string(text, index)
            continue
        if character == "{":
            if depth == 0:
                start = index
            depth += 1
        elif character == "}" and depth > 0:
            depth -= 1
            if depth == 0:
                last = parsed_json_object(text[start : index + 1]) or last
        index += 1
    return last
