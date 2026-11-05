"""A qualified credential label is still a credential label."""

import pytest

from atrium.session.is_secret_table_label import is_secret_table_label
from atrium.session.redact_sensitive_text import redact_sensitive_text


@pytest.mark.parametrize(
    "label",
    [
        "Password",
        "MySQL password",
        "**HMAC secret**",
        "API token",
        "`DB_PASSWORD`",
        "Root passwd:",
        "Stripe secret key",
        "OpenRouter API key",
        "Contraseña MySQL",
        "Clave API",
        "contraseña del buzón",
    ],
)
def test_a_qualified_credential_label_is_recognized(label: str) -> None:
    assert is_secret_table_label(label)


@pytest.mark.parametrize(
    "label",
    [
        "Host",
        "Password manager",
        "Token count",
        "Rotation date",
        "Secret Santa list owner",
        "Notes about the token refresh flow in the old exporter",
        "Key",
        "Public key",
    ],
)
def test_prose_and_neighbouring_fields_are_not(label: str) -> None:
    assert not is_secret_table_label(label)


def test_a_key_value_row_with_a_qualified_label_loses_its_value() -> None:
    sentinel = "Zq7+v>Sentinel^;x91"
    text = f"| Field | Value |\n|---|---|\n| MySQL password | `{sentinel}` |\n| Host | db.local |"
    redacted = redact_sensitive_text(text)
    assert sentinel not in redacted
    assert "db.local" in redacted
