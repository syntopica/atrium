"""Recognize explicit credential field labels, never arbitrary prose."""

import re


def is_secret_table_label(cell: str) -> bool:
    """Accept common English/Spanish credential keys with Markdown decoration."""
    label = re.sub(r"[`*]", "", cell).replace("_", " ").strip().rstrip(":").casefold()
    label = re.sub(r"[-\s]+", " ", label)
    return label in {
        "password",
        "passwd",
        "passphrase",
        "contraseña",
        "contrasena",
        "clave",
        "api key",
        "apikey",
        "access token",
        "auth token",
        "client secret",
        "token",
        "secret",
        "smtp password",
        "imap password",
        "mailbox password",
    }
