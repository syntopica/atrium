"""Drop every PEM private key block from a text, as the exporter does."""


def redact_private_key_blocks(text: str) -> str:
    """Replace each ``-----BEGIN ... PRIVATE KEY-----`` block with one marker.

    Ported line for line from rocket-agents' `redactPrivateKeyBlocks.ts` so a
    record written during the session is redacted exactly as its transcript
    will be when the exporter archives it.
    """
    output: list[str] = []
    inside = False
    for line in text.split("\n"):
        if line.startswith("-----BEGIN ") and "PRIVATE KEY-----" in line:
            if not inside:
                output.append("[REDACTED:private-key]")
            inside = True
            continue
        if inside and line.startswith("-----END ") and "PRIVATE KEY-----" in line:
            inside = False
            continue
        if not inside:
            output.append(line)
    return "\n".join(output)
