"""Turn one canonical conversation into retrievable records."""

import re
from collections.abc import Iterator, Mapping
from typing import Any

from atrium.ingest.admission_tally import AdmissionTally
from atrium.ingest.canonical_workspace import canonical_workspace
from atrium.ingest.record_identity import record_identity
from atrium.ingest.tool_round import ToolRound
from atrium.ingest.workspace_alias import WorkspaceAlias
from atrium.record import Record

# Roles that carry conversation. Everything else in an archive event stream is
# machinery: tool invocations, system notices, and provider-specific chrome. The
# system this replaces indexed all of it and paid for it -- 251,568 drawers of
# serialized tool output, 18.8% of the whole index, competing with prose in every
# search.
CONVERSATIONAL_ROLES = frozenset({"user", "assistant"})

# Bare acknowledgements carry no retrievable claim. This is deliberately a
# pattern and not a length: measured over 882 real conversational messages,
# dropping everything under 120 characters would discard 43.4% of them, and the
# sample is full of short facts a memory exists to keep -- "63 tests verdes",
# "Commit hecho. Deploy a server-a.", "YAML roto: dos puntos dentro de scalar
# plano". The pattern below drops 1.0% of the same set.
_ACKNOWLEDGEMENT = re.compile(
    r"^(ok|okay|vale|dale|adelante|s[ií]|no|gracias|perfecto|genial|"
    r"contin[uú]a|continua|sigue|listo|hecho|bien|correcto|exacto|claro)"
    r"[\s.,!¡¿?]*$",
    re.IGNORECASE,
)


def to_records(
    conversation: dict[str, Any],
    tally: AdmissionTally | None = None,
    aliases: Mapping[str, str | WorkspaceAlias] | None = None,
    forgotten: frozenset[str] = frozenset(),
) -> Iterator[Record]:
    """Yield one record per conversational event worth retrieving.

    Skips non-conversational events, tool invocations rendered as messages
    with the results that answer them, and bare acknowledgements. Nothing is
    deleted by skipping: the archive keeps every event, and this only decides
    what earns a row in a derived index that can be rebuilt with a different
    rule tomorrow. ``forgotten`` holds the record ids the forget ledger keeps
    out. Pass a ``tally`` to learn what each rule turned away -- the
    admitted total alone looked healthy while 162,225 tool-call and thinking
    records were being filed as conversation.
    """
    conversation_id = conversation.get("id")
    provenance = conversation.get("provenance") or {}
    source_sha256 = provenance.get("contentSha256")
    if not conversation_id or not source_sha256:
        raise ValueError("conversation lacks id or provenance.contentSha256")

    provider = conversation.get("source") or "unknown"
    workspace = canonical_workspace(
        conversation.get("workspace"), aliases=aliases, started_at=conversation.get("startedAt")
    )
    title = conversation.get("title")
    tool_round = ToolRound()
    # Counting into a throwaway tally when the caller passed none keeps one code
    # path for every rule; nothing reads it.
    counts = tally if tally is not None else AdmissionTally()

    for index, event in enumerate(conversation.get("events") or []):
        text = (event.get("text") or "").strip()
        tool_rule = tool_round.classify(event.get("role"), event.get("kind"), text)
        if tool_rule:
            counts.reject(tool_rule)
            continue
        if event.get("kind") != "message":
            counts.reject(f"kind {event.get('kind') or 'absent'}")
            continue
        if event.get("role") not in CONVERSATIONAL_ROLES:
            counts.reject(f"role {event.get('role') or 'absent'}")
            continue
        if not text or _ACKNOWLEDGEMENT.match(text):
            counts.reject("empty or acknowledgement")
            continue
        event_id = event.get("id")
        if not event_id:
            counts.reject("missing event id")
            continue
        record_id = record_identity(conversation_id, event_id)
        if record_id in forgotten:
            counts.reject("forgotten")
            continue
        counts.admit(event["role"])
        yield Record(
            record_id=record_id,
            event_id=event_id,
            conversation_id=conversation_id,
            source_sha256=source_sha256,
            provider=provider,
            role=event["role"],
            text=text,
            authored_at=event.get("timestamp") or conversation.get("startedAt"),
            workspace=workspace,
            title=title,
            event_index=index,
        )
