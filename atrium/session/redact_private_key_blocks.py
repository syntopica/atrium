"""Drop every PEM private key block from a text, as the exporter does."""

from atrium.session.escaped_private_key_pattern import ESCAPED_PRIVATE_KEY_PATTERN
from atrium.session.holds_escaped_private_key import holds_escaped_private_key
from atrium.session.is_private_key_marker_line import is_private_key_marker_line
from atrium.session.opens_private_key_block import opens_private_key_block


def redact_private_key_blocks(text: str) -> str:
    """Replace each ``-----BEGIN ... PRIVATE KEY-----`` block with one marker.

    Same rule as scribe's `redactPrivateKeyBlocks.ts`: a key escaped onto one
    line is replaced within that line, END marker or not; a block opens only on
    a bare BEGIN marker line and everything up to its END line goes, failing
    closed.
    """
    output: list[str] = []
    inside = False
    for line in text.split("\n"):
        if inside:
            inside = not is_private_key_marker_line(line, "END")
            continue
        if holds_escaped_private_key(line):
            output.append(ESCAPED_PRIVATE_KEY_PATTERN.sub("[REDACTED:private-key]", line))
            continue
        if not opens_private_key_block(line):
            output.append(line)
            continue
        output.append("[REDACTED:private-key]")
        inside = True
    return "\n".join(output)
