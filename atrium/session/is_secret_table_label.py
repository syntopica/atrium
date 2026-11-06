"""Recognize explicit credential field labels, never arbitrary prose."""

import re

from atrium.session.credential_label_max_words import CREDENTIAL_LABEL_MAX_WORDS
from atrium.session.credential_label_prefixes import CREDENTIAL_LABEL_PREFIXES
from atrium.session.credential_label_suffixes import CREDENTIAL_LABEL_SUFFIXES
from atrium.session.is_tax_reference_label import is_tax_reference_label


def is_secret_table_label(cell: str) -> bool:
    """Accept English/Spanish credential keys, qualified or not, with Markdown decoration.

    A label is a short cell whose last words (English) or first word (Spanish)
    name a credential. Exact-only matching let "MySQL password", "HMAC secret"
    and "API token" rows reach context output with their values (2026-11-05).
    """
    label = re.sub(r"[`*]", "", cell).replace("_", " ").strip().rstrip(":").casefold()
    words = re.sub(r"[-\s]+", " ", label).strip().split(" ")
    if not words[0] or len(words) > CREDENTIAL_LABEL_MAX_WORDS:
        return False
    joined = " ".join(words)
    if any(joined == s or joined.endswith(f" {s}") for s in CREDENTIAL_LABEL_SUFFIXES):
        return True
    return words[0] in CREDENTIAL_LABEL_PREFIXES and not is_tax_reference_label(words)
