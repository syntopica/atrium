"""Validate observed hosts supplied by a canonical conversation."""

from typing import Any


def conversation_hosts(conversation: dict[str, Any]) -> tuple[str, ...] | None:
    """Keep unknown provenance unknown; canonical labels name observers, not origins."""
    hosts = conversation.get("hosts")
    if hosts is None:
        return None
    if not isinstance(hosts, list) or any(not isinstance(host, str) or not host for host in hosts):
        raise ValueError("conversation hosts must be a list of nonempty labels")
    return tuple(sorted(set(hosts)))
