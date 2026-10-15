"""Count, per provider, how two indexes' records differ."""

from collections.abc import Mapping
from typing import Any

_DIFFERENCES = ("only_test", "only_live", "changed")


def compare_digests(
    test: Mapping[str, tuple[str, str]], live: Mapping[str, tuple[str, str]]
) -> dict[str, dict[str, Any]]:
    """Return provider to counts: in each index, only in one, and changed text.

    A changed record counts under the live index's provider. Each difference
    keeps up to three ids as a sample, enough to start a trace.
    """
    providers = {provider for provider, _ in live.values()} | {
        provider for provider, _ in test.values()
    }
    ids: dict[str, dict[str, list[str]]] = {
        provider: {kind: [] for kind in _DIFFERENCES} for provider in providers
    }
    totals = {provider: {"test": 0, "live": 0} for provider in providers}
    for record_id, (provider, digest) in live.items():
        totals[provider]["live"] += 1
        other = test.get(record_id)
        if other is None:
            ids[provider]["only_live"].append(record_id)
        elif other[1] != digest:
            ids[provider]["changed"].append(record_id)
    for record_id, (provider, _) in test.items():
        totals[provider]["test"] += 1
        if record_id not in live:
            ids[provider]["only_test"].append(record_id)
    return {
        provider: totals[provider]
        | {
            kind: {"count": len(found), "sample": sorted(found)[:3]}
            for kind, found in ids[provider].items()
        }
        for provider in sorted(providers)
    }
