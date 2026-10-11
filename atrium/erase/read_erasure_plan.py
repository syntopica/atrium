"""Read an applied scribe erasure plan, refusing anything else."""

import json
from pathlib import Path

from atrium.erase.erasure_plan import ErasurePlan

_KIND = "rocket-agents-conversation-erasure-plan"
_SCHEMA_VERSION = 2


def read_erasure_plan(path: Path) -> ErasurePlan:
    """Return the plan's ``conversationIds`` and ``toGenerationId``.

    Scribe pins the fields (``fixtures/archive-contract/v2/erasure-plan.json``):
    ``conversationIds`` is every conversation the plan removes any fragment of,
    including one that keeps other fragments, because a synthesis built from the
    erased fragment still carries its text. Only an applied plan is accepted --
    one with a ``toGenerationId`` -- so derived text is never deleted for an
    erasure the archive itself has not made.
    """
    plan = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict) or plan.get("kind") != _KIND:
        raise ValueError(f"{path} is not a {_KIND}")
    if plan.get("schemaVersion") != _SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported schemaVersion {plan.get('schemaVersion')!r}")
    generation = plan.get("toGenerationId")
    if not isinstance(generation, str) or not generation:
        raise ValueError(f"{path} has not been applied: it names no toGenerationId")
    ids = plan.get("conversationIds")
    if not isinstance(ids, list) or not all(isinstance(i, str) and i for i in ids):
        raise ValueError(f"{path}: conversationIds must be a list of non-empty strings")
    return ErasurePlan(tuple(ids), generation)
