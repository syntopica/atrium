"""The schema a model fills when it judges two claims against each other."""

from typing import Any

RELATIONS = ("equivalent", "complementary", "conflicting", "unrelated")


def pair_relation_tool() -> dict[str, Any]:
    """Return the tool contract for one pairwise adjudication."""
    return {
        "name": "record_relation",
        "input_schema": {
            "type": "object",
            "properties": {
                "relation": {
                    "type": "string",
                    "enum": list(RELATIONS),
                    "description": (
                        "equivalent: the same assertion about the same thing, differently worded, "
                        "so one sentence could replace both. complementary: both true and about "
                        "the same subject, but each states something the other does not. "
                        "conflicting: they cannot both be true of the SAME thing on the SAME "
                        "occasion. Two measurements of the same quantity taken on different runs "
                        "or different days are NOT conflicting; a required setting against an "
                        "observed one is NOT conflicting; an instruction against a report of "
                        "following it is NOT conflicting; a count that grew between two sessions "
                        "is NOT conflicting. When you cannot tell from the statements whether "
                        "they describe the same occasion, answer complementary or unrelated. "
                        "unrelated: different subjects."
                    ),
                },
                "shared_subject": {
                    "type": "string",
                    "description": "The thing both claims are about, quoted from them. Empty when they share none.",
                },
                "difference": {
                    "type": "string",
                    "description": "What the second claim says that the first does not, quoted. Empty when nothing.",
                },
            },
            "required": ["relation", "shared_subject", "difference"],
        },
    }
