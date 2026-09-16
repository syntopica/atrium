"""Index just past the closing quote of a JSON string, honouring escapes."""


def end_of_json_string(text: str, opening: int) -> int:
    """Return the index after the string that opens at ``text[opening]``.

    A backslash skips the character it escapes, so an escaped quote never
    closes the string. An unterminated string ends with the text, which the
    caller reads as "no object here" rather than an error.
    """
    index = opening + 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == '"':
            return index + 1
        index += 1
    return len(text)
