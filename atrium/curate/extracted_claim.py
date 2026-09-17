"""Turn one screened candidate into a structured claim with a local model."""

from typing import Any

from atrium.curate.claim_extraction_tool import claim_extraction_tool
from atrium.curate.optional_field import optional_field
from atrium.curate.structured_claim import StructuredClaim
from atrium.synthesize.lane_prompt import LanePrompt
from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL, local_lane_call

_SYSTEM = (
    "You structure one already-extracted statement into fields. You do not "
    "judge whether it is worth keeping, you do not add anything it does not "
    "say, and you do not correct it. Quote its own words wherever a field "
    "allows it. If the statement names no condition, no scope name or no "
    "value, use null or an empty string rather than guessing one.\n"
    "Scope, which decides where the claim can ever be reused:\n"
    "- project: it is about one codebase -- its files, functions, tests, "
    "migrations, configuration or incidents. Any statement quoting a source "
    "path or a symbol from the work itself is project scope.\n"
    "- tool: it is about a third-party tool, CLI, library, service or model, "
    "and would hold for anyone using that tool. Name the tool, not the "
    "function that called it.\n"
    "- general: it holds regardless of tool and codebase.\n"
    "Leave scope_name null for project scope: the project is already known "
    "and is not yours to guess."
)
_INSTRUCTION = (
    "Now express that single statement as ONE JSON object matching this schema, "
    "based entirely on the statement itself and no outside knowledge."
)


def extracted_claim(
    record: dict[str, Any], model: str = LOCAL_DEFAULT_MODEL, project: str | None = None
) -> StructuredClaim:
    """Return the structured form of one candidate ledger line.

    The dates, the episode count and the project are copied in, never asked
    for: stage one established the dates from the registry and the project is
    joined through the index, and a model given the chance to restate either
    will eventually restate it wrongly.
    """
    answer = local_lane_call(
        LanePrompt(_SYSTEM, record["text"], _INSTRUCTION, "STATEMENT"),
        claim_extraction_tool(),
        model=model,
    )
    fields = answer["input"]
    return StructuredClaim(
        candidate_id=record["candidate_id"],
        text=record["text"],
        subject=str(fields["subject"]),
        predicate=str(fields["predicate"]),
        value=str(fields["value"]),
        conditions=optional_field(fields["conditions"]),
        scope=str(fields["scope"]),
        scope_name=optional_field(fields["scope_name"]),
        project=project,
        durability=str(fields["durability"]),
        first_seen=record["first_seen"],
        last_seen=record["last_seen"],
        episodes=int(record.get("episodes") or len(record.get("sources") or ())),
        model=answer["model"],
    )
