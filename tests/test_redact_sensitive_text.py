"""The session record passes through the archive's redaction policy."""

from atrium.session.redact_sensitive_text import redact_sensitive_text


def test_private_key_block_becomes_one_marker():
    text = (
        "before\n-----BEGIN RSA PRIVATE KEY-----\nMIIE\nAAAA\n-----END RSA PRIVATE KEY-----\nafter"
    )
    assert redact_sensitive_text(text) == "before\n[REDACTED:private-key]\nafter"


def test_assigned_password_and_api_key_lose_their_values():
    text = 'password: hunter2hunter2 and API_KEY="abcdefghijkl"'
    out = redact_sensitive_text(text)
    assert "hunter2hunter2" not in out
    assert "abcdefghijkl" not in out
    assert out.count("[REDACTED:secret]") == 2


def test_tokens_and_url_credentials_are_redacted():
    text = (
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ "
        "https://user:pass@example.com/x AKIAABCDEFGHIJKLMNOP"
    )
    out = redact_sensitive_text(text)
    assert "Bearer [REDACTED:token]" in out
    assert "ghp_" not in out
    assert "https://[REDACTED:credentials]@example.com/x" in out
    assert "[REDACTED:aws-access-key]" in out


def test_ordinary_prose_is_untouched():
    text = "The password rotation policy was decided on 2026-09-16; see docs/auth.md."
    assert redact_sensitive_text(text) == text
