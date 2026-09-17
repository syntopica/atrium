"""The comparison form of a claim: what two phrasings must share to be one."""

import re
import unicodedata

from atrium.curate.protected_symbols import protected_symbols

_MARKUP = re.compile(r"[`*_\[\]()]+")
_SEPARATOR = re.compile(r"[^0-9a-z]+")


def normalized_claim(text: str) -> str:
    """Return the key two identical claims share, digits and all.

    Numbers, versions and dates survive on purpose: "38 orphans held 7.4 GB"
    and "3 orphans held 7.4 GB" are different findings, and a normalizer that
    strips digits merges them. Signs, comparisons and version separators
    survive for the same reason, spelled out by `protected_symbols` before the
    folding runs. Accents fold because the corpus mixes Spanish and English
    spellings of the same entity.
    """
    folded = unicodedata.normalize("NFKD", protected_symbols(text).lower())
    without_accents = "".join(c for c in folded if not unicodedata.combining(c))
    return _SEPARATOR.sub(" ", _MARKUP.sub(" ", without_accents)).strip()
