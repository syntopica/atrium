"""Judge whether one claim is durable knowledge, evidence, or session noise."""

from typing import Any

from atrium.curate.publishability_tool import publishability_tool
from atrium.synthesize.lane_prompt import LanePrompt
from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL, local_lane_call

_SYSTEM = (
    "You decide what a statement is, not whether it is true. The statements "
    "come from one operator's engineering sessions, and most of them are not "
    "knowledge: they report what a command printed, where a session ran, or "
    "what happened once. Say what the statement asserts before you classify "
    "it, and if you cannot state an assertion, it has none."
)
_INSTRUCTION = "Now classify that statement as ONE JSON object matching this schema."


def claim_publishability(text: str, model: str = LOCAL_DEFAULT_MODEL) -> tuple[str, dict[str, Any]]:
    """Return the verdict and the assertion the model read out of the claim.

    A positive test, deliberately, after enumerating debris patterns by hand
    stopped paying: each pattern caught the shapes it was written from and the
    next grading pass found four more. Asking what a claim asserts scales to
    shapes nobody has seen, and a claim whose assertion comes back empty
    answers the question by itself.
    """
    answer = local_lane_call(
        LanePrompt(_SYSTEM, text, _INSTRUCTION, "STATEMENT"),
        publishability_tool(),
        model=model,
    )
    fields = answer["input"]
    return str(fields["verdict"]), fields
