"""Judge one pair of claims, with the quantities as a veto over the answer."""

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
    "when they are worded almost identically."
)
_INSTRUCTION = (
    "Now judge how statement B relates to statement A as ONE JSON object matching this schema."
)


def pair_relation(
    left: str, right: str, model: str = LOCAL_DEFAULT_MODEL
) -> tuple[str, dict[str, Any]]:
    """Return the relation and the model's own account of it.

    The quantities veto the answer: if the two claims carry different numbers,
    comparisons, signs or negations, `equivalent` is downgraded to
    `conflicting`, because a merge there would silently destroy one of two
    genuinely different findings. A model is allowed to find a difference the
    signature missed; it is not allowed to overrule one the signature found.
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
        return "conflicting", {**fields, "vetoed_by": "numeric_signature"}
    return relation, fields
