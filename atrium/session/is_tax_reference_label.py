"""Tell a Spanish tax reference label from a password label."""


def is_tax_reference_label(words: list[str]) -> bool:
    """Whether a "clave ..." label names the AEAT's settlement reference.

    "Clave de liquidación" is a public reference, not a password: 269 of the
    conversation archive's "clave" matches on 2026-11-06.
    """
    return any(word.startswith("liquid") for word in words)
