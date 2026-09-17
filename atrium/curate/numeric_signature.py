"""The quantities a claim asserts, as a comparable signature."""

import re

# A quantity is a sign, digits, an optional decimal part and an optional unit,
# plus the comparison it sits behind. Versions keep their separators: "1.2" and
# "1-2" are different pins, which is the collision `protected_symbols` exists
# to stop at the identity level and this signature stops again at the merge.
_QUANTITY = re.compile(
    r"(?P<comparison>>=|<=|!=|>|<)?\s*"
    r"(?P<sign>-)?(?P<number>\d+(?:[.,:/-]\d+)*)\s*"
    r"(?P<unit>%|[a-zA-Z]{1,4}\b)?"
)
_NEGATIONS = ("not ", "no ", "never ", "sin ", "nunca ", "n't ", "cannot ", "without ")


def numeric_signature(text: str) -> tuple[str, ...]:
    """Return the sorted quantities and negations a claim carries.

    Two claims whose signatures differ cannot be the same claim, whatever a
    model says about them: "38 orphans held 7.4 GB" and "3 orphans held 7.4 GB"
    report different incidents, and "the flag is enabled" and "the flag is not
    enabled" contradict. The signature is deliberately coarse -- an unordered
    multiset -- because it is a veto, not a matcher.
    """
    lowered = text.lower()
    found = [
        "".join(
            (
                match.group("comparison") or "",
                match.group("sign") or "",
                match.group("number").replace(",", "."),
                (match.group("unit") or "").strip(),
            )
        )
        for match in _QUANTITY.finditer(lowered)
    ]
    found.extend(f"neg:{word.strip()}" for word in _NEGATIONS if word in lowered)
    return tuple(sorted(found))
