"""Name segments that make a variable describe a credential rather than hold one."""

# A pattern or shape that matches tokens, where to send one, a limit on model
# tokens, a browser storage key, a key meant to be public. Found in the
# conversation archive on 2026-11-06 (`SCANNED_TOKEN_PATTERN`, `OAUTH_TOKEN_URI`,
# `MAX_TOKENS`, `CONTACT_FORM_STORAGE_KEY`, `NEXT_PUBLIC_TURNSTILE_SITE_KEY`).
NON_SECRET_VARIABLE_WORDS = frozenset(
    {
        "PATTERN",
        "SHAPE",
        "URI",
        "URL",
        "ENDPOINT",
        "MAX",
        "MIN",
        "STORAGE",
        "PUBLIC",
        "PUBLISHABLE",
        "SITE",
        "IDEMPOTENCY",
        "ID",
    }
)
