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
        "SESSION_SECRET=" + "crypto.randomBytes(32).toString(1)",
        "Google API key https:" + "//www.example.com/a/settings/apikey2",
        "key: '" + "exports/raw/2026-10-20/part_1/" + "manifest.json'",
    ],
)
def test_ids_hashes_public_keys_and_prose_stay(line: str) -> None:
    assert redact_sensitive_text(line) == line


@pytest.mark.parametrize(
    "line",
    [
        "export CF_API_TOKENS={v}",
        "ATOKEN={v}",
        "Primary API key: {v}",
    ],
)
def test_a_credential_variable_or_label_is_still_redacted(line: str) -> None:
    value = _ALNUM[:32]
    assert value not in redact_sensitive_text(line.format(v=value))


@pytest.mark.parametrize(
    "line",
    [
        "Clave de liquidación: " + "A0123456" + "78901234",
        "SECRETS=" + "/Users/someone/p/project-123/",
        "BETTER_AUTH_SECRET=" + "<run openssl1>",
        "SECRET_KEY=" + "{env.keys[0]}",
        "clave_liquidacion: " + "A0123456" + "78901234",
        "export SCANNED_TOKEN_PATTERN=" + "gh[ops]_[a-z0-9]{36}",
        "OAUTH_TOKEN_URI=" + "https://oauth2.example.com/token2",
        "MAX_TOKENS=" + "abc12345",
        "export TOKENIZER=" + "cl100k_base",
        "CONTACT_FORM_STORAGE_KEY=" + "contact-form-v2",
        "Sec-WebSocket-Key: " + "dGhlIHNhbXBsZSBub25j" + "ZQ1x",
        "Cache restored from key: " + "linux-node-" + "abc123def456ghi789",
    ],
)
def test_references_descriptions_and_digests_stay(line: str) -> None:
    assert redact_sensitive_text(line) == line


def test_the_lines_after_a_one_line_escaped_private_key_stay() -> None:
    body = "MII" + _ALNUM[:60]
    text = (
        "-----BEGIN "
        + "PRIVATE KEY-----\\n"
        + body
        + '\\n-----END PRIVATE KEY-----\\n", "client_email": "bot@example.com"\n'
        + "Run pnpm install from package.json next."
    )
    redacted = redact_sensitive_text(text)
    assert body not in redacted
    assert '"client_email": "bot@example.com"' in redacted
    assert redacted.endswith("Run pnpm install from package.json next.")


def test_a_truncated_one_line_escaped_private_key_goes_and_the_rest_stays() -> None:
    body = "b3Bl" + _ALNUM[:60]
    text = (
        '"key": "-----BEGIN OPENSSH '
        + "PRIVATE KEY-----\\n"
        + body
        + "\\n"
        + body
        + '..." (truncated)\n'
        + "Run pnpm install from package.json next."
    )
    redacted = redact_sensitive_text(text)
    assert body not in redacted
    assert '..." (truncated)' in redacted
    assert redacted.endswith("Run pnpm install from package.json next.")


def test_an_assignment_value_ends_at_an_escaped_newline() -> None:
    value = _ALNUM[:32]
    redacted = redact_sensitive_text(f"KEY={value}\\nSTART=$(date)")
    assert redacted == "KEY=[REDACTED:secret]\\nSTART=$(date)"
