"""The retrieval lanes a caller may name."""

from typing import Literal

# A Literal, not a plain str, so the MCP input schema lists the lanes as an
# enum: a model shown only `lane: string` guessed "lexical", and the refusal
# came back as a bare "Error executing tool" it could not correct from.
Lane = Literal["auto", "words", "substring", "dense"]
