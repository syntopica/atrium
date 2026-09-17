"""The schema a model must fill when it turns one stated fact into a claim."""

from typing import Any

SCOPES = ("general", "tool", "project")
DURABILITY = ("durable", "situational")


def claim_extraction_tool() -> dict[str, Any]:
    """Return the tool contract for structuring a single claim.

    The observation dates are deliberately absent: the ledger already knows
    when every episode stated the claim, and asking a model for a date it
    cannot read off the sentence is an invitation to invent one.
    """
    return {
        "name": "record_claim",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "What the claim is about: a file, a command, a service, a person, a setting.",
                },
                "predicate": {
                    "type": "string",
                    "description": "What is asserted about the subject, as a short verb phrase.",
                },
                "value": {
                    "type": "string",
                    "description": "The asserted outcome, number, path or name. Empty string if the predicate carries it alone.",
                },
                "conditions": {
                    "type": ["string", "null"],
                    "description": "Version, platform or precondition the claim depends on, quoted from the sentence. Null when the sentence states none.",
                },
                "scope": {
                    "type": "string",
                    "enum": list(SCOPES),
                    "description": "general: true regardless of tool or repository. tool: true of a named tool, CLI, library or service. project: true only inside one repository or codebase.",
                },
                "scope_name": {
                    "type": ["string", "null"],
                    "description": "The tool or project the claim is scoped to. Null when the scope is general.",
                },
                "durability": {
                    "type": "string",
                    "enum": list(DURABILITY),
                    "description": "durable: still useful months later. situational: true only of one run, one session or one transient state.",
                },
            },
            "required": [
                "subject",
                "predicate",
                "value",
                "conditions",
                "scope",
                "scope_name",
                "durability",
            ],
        },
    }
