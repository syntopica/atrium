"""Recognize the label of an inline ``Label: value`` credential line."""

from atrium.session.is_secret_table_label import is_secret_table_label

# Inline, a bare "key" usually is one ("Merchant key: ...", "app_key: ..."), but
# these qualifiers name things that are not secrets: a Turnstile site key ships
# to the browser, an idempotency key is a request id, a cache or WebSocket
# handshake key is a digest.
_PUBLIC_KEY_QUALIFIERS = (
    "public",
    "publishable",
    "primary",
    "foreign",
    "host",
    "ssh host",
    "site",
    "idempotency",
    "cache",
    "websocket",
    "input",
)
# Spanish puts the noun first ("Token de Hetzner", "Token API Hetzner Cloud"); a
# bare leading "token" is not enough, or "Token count" would be a credential.
_SPANISH_TOKEN_LINKS = ("de", "del", "api", "para")


def is_inline_secret_label(label: str) -> bool:
    """Accept a table credential label, "Token de/API ...", or a non-public "... key"."""
    if is_secret_table_label(label):
        return True
    words = label.replace("_", " ").replace("-", " ").casefold().split()
    if len(words) > 1 and words[0] == "token" and words[1] in _SPANISH_TOKEN_LINKS:
        return True
    if not words or words[-1] not in ("key", "keys"):
        return False
    # Any qualifying word: "next public turnstile site key", "cache restored from
    # key". A label naming a credential outright was accepted above.
    return " ".join(words[:-1]) not in _PUBLIC_KEY_QUALIFIERS and not any(
        word in _PUBLIC_KEY_QUALIFIERS for word in words
    )
