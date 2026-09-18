"""Judge one pair of claims, with the quantities as a veto over merging them."""

from typing import Any

from atrium.curate.numeric_signature import numeric_signature
from atrium.curate.pair_relation_tool import pair_relation_tool
from atrium.synthesize.lane_prompt import LanePrompt
from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL, local_lane_call

_SYSTEM = (
    "You compare two statements taken from one operator's engineering sessions "
    "and say how they relate. Judge only what the statements say; do not use "
    "outside knowledge and do not decide which is true. Two statements about "
    "different files, different projects or different runs are unrelated even "
    "when they are worded almost identically. Reserve `conflicting` for the rare "
    "pair that pins both statements to the SAME occasion - the same run, the "
    "same commit, the same stated moment - and still cannot be reconciled. If "
    "the statements do not themselves say they describe the same occasion, they "
    "are not conflicting, however alike their wording: two lint runs, two test "
    "durations, two counts of the same kind of file, a required setting beside "
    "an observed one, and an instruction beside a report of obeying it are all "
    "NOT conflicting. Measured: of the 8 pairs called conflicting before this "
    "rule, 7 were the same measurement taken on different days."
)
_INSTRUCTION = (
    "Now judge how statement B relates to statement A as ONE JSON object matching this schema."
)


def pair_relation(
    left: str, right: str, model: str = LOCAL_DEFAULT_MODEL
) -> tuple[str, dict[str, Any]]:
    """Return the relation and the model's own account of it.

    The quantities veto the MERGE, not the classification: if two claims the
    model called `equivalent` carry different numbers, comparisons, signs or
    negations, the answer keeps its relation and gains `merge_blocked`, so the
    clustering pass leaves them apart. It used to return `conflicting` instead,
    which is what made the contradiction output unusable: 7 of the 8 pairs it
    produced were the same measurement taken on two different days, not two
    statements that cannot both be true. A differing quantity is a reason not
    to merge; it is not evidence of a contradiction.
    """
    answer = local_lane_call(
        LanePrompt(
            _SYSTEM,
            f"STATEMENT A:\n{left}\n\nSTATEMENT B:\n{right}",
            _INSTRUCTION,
            "STATEMENTS",
        ),
        pair_relation_tool(),
        model=model,
    )
    fields = answer["input"]
    relation = str(fields["relation"])
    if relation == "equivalent" and numeric_signature(left) != numeric_signature(right):
        return relation, {**fields, "merge_blocked": "numeric_signature"}
    return relation, fields
