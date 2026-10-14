"""Turn a restore selector into restore events for the ledger."""

from collections.abc import Mapping
from typing import Any


def restore_events(
    selector: str, latest: Mapping[str, Mapping[str, Any]], today: str
) -> list[dict[str, Any]]:
    """Restore one record id, every record of a rule, or of a rule's detail.

    ``selector`` is a record id, ``<rule>`` or ``<rule>:<detail>`` (for
    example ``retired:Holded``). Only records whose latest event is ``forget``
    are restored; the restore event pins them, so no later pass forgets them
    again.
    """
    rule, _, detail = selector.partition(":")
    events = []
    for record_id, event in sorted(latest.items()):
        if event["event"] != "forget":
            continue
        by_id = record_id == selector
        by_rule = event.get("rule") == rule and (not detail or event.get("detail") == detail)
        if by_id or by_rule:
            events.append({"event": "restore", "record_id": record_id, "at": today})
    return events
