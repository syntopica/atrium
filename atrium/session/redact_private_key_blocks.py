"""Drop every PEM private key block from a text, as the exporter does."""

from atrium.session.closes_private_key_on_same_line import closes_private_key_on_same_line
from atrium.session.escaped_private_key_pattern import ESCAPED_PRIVATE_KEY_PATTERN
from atrium.session.holds_escaped_private_key import holds_escaped_private_key
from atrium.session.is_pem_body_line import is_pem_body_line
from atrium.session.is_private_key_marker_line import is_private_key_marker_line


def redact_private_key_blocks(text: str) -> str:
    """Replace each ``-----BEGIN ... PRIVATE KEY-----`` block with one marker.

    Same rule as scribe's `redactPrivateKeyBlocks.ts`: a key escaped onto one
    line is replaced within that line, END marker or not; a block opens only on
    a line that holds neither, and its body lines go up to its END line; a line
    that cannot be part of a key ends the block and stays.
    """
    output: list[str] = []
    inside = False
    for line in text.split("\n"):
        if inside and is_private_key_marker_line(line, "END"):
            inside = False
            continue
        if inside and is_pem_body_line(line):
            continue
        inside = False
        if holds_escaped_private_key(line):
            output.append(ESCAPED_PRIVATE_KEY_PATTERN.sub("[REDACTED:private-key]", line))
            continue
        if not is_private_key_marker_line(line, "BEGIN") or closes_private_key_on_same_line(line):
            output.append(line)
            continue
        output.append("[REDACTED:private-key]")
        inside = True
    return "\n".join(output)
