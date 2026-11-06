"""Drop every PEM private key block from a text, as the exporter does."""

from atrium.session.escaped_private_key_pattern import ESCAPED_PRIVATE_KEY_PATTERN
from atrium.session.holds_escaped_private_key import holds_escaped_private_key
from atrium.session.is_private_key_marker_line import is_private_key_marker_line
from atrium.session.opens_private_key_block import opens_private_key_block


def redact_private_key_blocks(text: str) -> str:
    """Replace each ``-----BEGIN ... PRIVATE KEY-----`` block with one marker.

    Same rule as scribe's `redactPrivateKeyBlocks.ts`: a key escaped onto one
    line is replaced within that line, END marker or not; otherwise a block opens
    where `opens_private_key_block` says, the text before the marker stays, and
    every line up to the END line goes, failing closed.
    """
    lines = text.split("\n")
    output: list[str] = []
    inside = False
    for index, line in enumerate(lines):
        if inside:
            inside = not is_private_key_marker_line(line, "END")
            continue
        if holds_escaped_private_key(line):
            output.append(ESCAPED_PRIVATE_KEY_PATTERN.sub("[REDACTED:private-key]", line))
            continue
        following = lines[index + 1] if index + 1 < len(lines) else None
        opening = opens_private_key_block(line, following)
        if opening is None:
            output.append(line)
            continue
        output.append(line[:opening] + "[REDACTED:private-key]")
        inside = True
    return "\n".join(output)
