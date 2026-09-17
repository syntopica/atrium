"""The schema a model fills when it decides whether a claim is worth a page."""

from typing import Any

VERDICTS = ("durable_knowledge", "incident_evidence", "session_mechanics")


def publishability_tool() -> dict[str, Any]:
    """Return the tool contract for judging one claim's publishability."""
    return {
        "name": "record_publishability",
        "input_schema": {
            "type": "object",
            "properties": {
                "verdict": {
                    "type": "string",
                    "enum": list(VERDICTS),
                    "description": (
                        "durable_knowledge: it would still be true tomorrow and is worth "
                        "knowing again. How a system behaves, what a setting or an identifier "
                        "IS, what a script or a service DOES, a technique and when to use it, a "
                        "constraint, a defect that exists until someone fixes it, a rename or a "
                        "replacement. Learning it in one session does not make it temporary. "
                        "incident_evidence: it reports the outcome of one run and nothing that "
                        "outlives it -- a test count, a duration, a byte size, a file that was "
                        "edited, a step that was taken. session_mechanics: it is about the "
                        "working session rather than any subject: where it ran, which file was "
                        "read next, what a command printed, what it was asked to do, how many "
                        "commits it left behind.\n"
                        "A bare fact is durable knowledge too: <thing> is <value> -- an "
                        "identifier, an address, a version a project pins, a setting, a status "
                        "-- because someone will ask that question again. What the session's "
                        "own machine happened to be running is not that.\n"
                        "When a statement holds both -- a run that revealed how something "
                        "behaves -- classify by what survives the run."
                    ),
                },
                "asserted": {
                    "type": "string",
                    "description": (
                        "The assertion, in the claim's own words: what is said about what. Empty "
                        "when the claim asserts nothing, which is itself the answer."
                    ),
                },
            },
            "required": ["verdict", "asserted"],
        },
    }
