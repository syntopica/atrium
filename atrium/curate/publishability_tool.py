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
                        "durable_knowledge: it states how something IS or WORKS and would still "
                        "be worth reading months from now. A statement about what a script, a "
                        "service, a function or a configuration DOES is durable knowledge even "
                        "though it describes an action -- 'deploy.sh copies the build to the "
                        "server' is how the system works. incident_evidence: it reports what "
                        "happened in one run -- a result, a count, a failure, a step taken -- "
                        "true but tied to that moment. session_mechanics: it is about the working "
                        "session rather than the subject: where it ran, which file it edited, "
                        "what it was asked to do, what a command printed, how many commits it "
                        "left behind."
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
