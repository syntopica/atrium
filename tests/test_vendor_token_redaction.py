"""Vendor-prefixed credentials and inline labelled values never survive redaction.

Sentinels are assembled at run time, so this file holds no string a secret
scanner would flag. Shapes follow the gitleaks 8.30.1 rules each one names.
"""

import pytest

from atrium.session.redact_sensitive_text import redact_sensitive_text

_ALNUM = "aB3dE5fG7hJ9kL2mN4pQ6rS8tU1vW3xY5zA7bC9dE2fG4hJ6kL8mN1pQ3rS5tU7vW9xY2zA4bC6"
_HEX = "0123456789abcdef" * 8
_AGE = "QPZRY9X8GF2TVDW0S3JN54KHCE6MUA7L" * 2

_SENTINELS = {
    "stripe": "sk_" + "live_" + _ALNUM[:24],
    "gcp": "AI" + "za" + _ALNUM[:35],
    "sendgrid": "SG" + "." + _ALNUM[:22] + "." + _ALNUM[:43],
    "perplexity": "pplx" + "-" + _ALNUM[:48],
    "airtable": "pat" + _ALNUM[:14] + "." + _HEX[:64],
    "age": "AGE-SECRET-" + "KEY-1" + _AGE[:58],
    "jwt": "ey" + _ALNUM[:20] + ".ey" + _ALNUM[:20] + "." + _ALNUM[:16],
    "github-fine-grained": "github" + "_pat_" + (_ALNUM * 2)[:82],
    "gitlab": "gl" + "pat-" + _ALNUM[:20],
    "npm": "np" + "m_" + _ALNUM[:36],
    "digitalocean": "do" + "p_v1_" + _HEX[:64],
    "base64-pem": "LS0tLS1" + "CRUdJT" + _ALNUM[:60],
}


@pytest.mark.parametrize("name", sorted(_SENTINELS))
def test_a_vendor_token_is_redacted_in_prose_and_in_a_table(name: str) -> None:
    secret = _SENTINELS[name]
    for text in (f"the key is {secret} here", f"| Secret key (LIVE) | `{secret}` |"):
        assert secret not in redact_sensitive_text(text)


def test_a_json_escaped_private_key_is_redacted() -> None:
    body = "MII" + _ALNUM[:60]
    text = (
        '"private_key": "-----BEGIN '
        + "PRIVATE KEY-----\\n"
        + body
        + '\\n-----END PRIVATE KEY-----\\n"'
    )
    redacted = redact_sensitive_text(text)
    assert body not in redacted
    assert "[REDACTED:private-key]" in redacted


@pytest.mark.parametrize(
    "line",
    [
        "- Client secret: `{v}`",
        "Token API Hetzner Cloud: {v}",
        "- app_id: `71c12345` / app_key: `{v}`",
        "Merchant key: `{v}`",
        "export RESEND_API_KEY={v}",
    ],
)
def test_an_inline_labelled_credential_is_redacted(line: str) -> None:
    value = _ALNUM[:32]
    assert value not in redact_sensitive_text(line.format(v=value))


@pytest.mark.parametrize(
    "line",
    [
        "OAuth client ID: 2c0f1234-5678-90ab-cdef-1234567890ab",
        "Commit: 4f257ac8d3e1b2c4f5a6b7c8d9e0f1a2b3c4d5e6",
        "Supabase Public Key: sb_publishable_abc123def456ghi789",
        'STOP_ALL_KEY = "Escape"',
        "next_public_turnstile_site_key: " + "0x4AAAAAAA" + "Bc1dEf2gHi3j",
        "Idempotency-Key: " + "a1b2c3d4e5f6" + "g7h8i9j0",
        "Result: 12 of 34 passed",
    ],
)
def test_ids_hashes_public_keys_and_prose_stay(line: str) -> None:
    assert redact_sensitive_text(line) == line
