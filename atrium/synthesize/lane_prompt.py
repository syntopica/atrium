"""What a lane asks a model for, apart from the schema."""

import dataclasses

# The default names an episode because the synthesis lanes pay for almost every
# call; the curation stages hand one screened sentence instead, and say so.
DEFAULT_INSTRUCTION = (
    "Now record the durable memory of that episode as ONE JSON object matching "
    "this schema, based entirely on the transcript and no outside knowledge."
)


@dataclasses.dataclass(frozen=True)
class LanePrompt:
    """The three moving parts of a lane prompt: framing, data, and the ask.

    Kept together because their order is the part that was learned the hard
    way: instructions first, the data fenced and labelled as data, the
    contract restated last, after a transcript that was itself an imperative
    outranked instructions placed before it.
    """

    system_text: str
    user_text: str
    instruction: str = DEFAULT_INSTRUCTION
    data_label: str = "EPISODE TRANSCRIPT"
