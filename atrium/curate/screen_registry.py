"""Read every synthesis record once and produce distinct claim candidates."""

from collections import Counter
from pathlib import Path
from typing import Any

from atrium.curate.candidate_identity import candidate_identity
from atrium.curate.claim_candidate import ClaimCandidate
from atrium.curate.normalized_claim import normalized_claim
from atrium.curate.record_facts import record_facts
from atrium.curate.runtime_debris import runtime_debris
from atrium.curate.screening_report import ScreeningReport
from atrium.synthesize.synthesis_registry import read_records


def screen_registry(registry: Path) -> ScreeningReport:
    """Flatten the registry's facts into distinct candidates, no model involved.

    This is the whole of stage one: deterministic, quota-free, and the only
    pass that reads all 45,900 records. Everything downstream works from the
    ledger it writes, so the expensive stages never re-read the corpus.
    """
    kept: dict[str, dict[str, Any]] = {}
    quarantined: list[dict[str, str]] = []
    reasons: Counter[str] = Counter()
    records = facts = 0
    for record in read_records(registry):
        records += 1
        job_key = record.get("job_key", "")
        episode_id = record.get("episode_id", "")
        conversation_id = record.get("conversation_id", "")
        authored_at = (record.get("authored_at") or "")[:10]
        model = record.get("model_requested", "")
        for fact in record_facts(record):
            facts += 1
            text = fact.strip()
            reason = runtime_debris(text)
            if reason is not None:
                reasons[reason] += 1
                quarantined.append({"text": text, "reason": reason, "job_key": job_key})
                continue
            normalized = normalized_claim(text)
            identity = candidate_identity(normalized)
            source = {
                "job_key": job_key,
                "episode_id": episode_id,
                "conversation_id": conversation_id,
                "authored_at": authored_at,
                "model": model,
            }
            entry = kept.get(identity)
            if entry is None:
                kept[identity] = {
                    "text": text,
                    "normalized": normalized,
                    "first_seen": authored_at,
                    "last_seen": authored_at,
                    "sources": [source],
                }
                continue
            entry["sources"].append(source)
            # The longest phrasing wins the display text: a claim stated twice
            # is usually stated once in full and once in shorthand, and the
            # shorthand is the one that loses its qualifications.
            if len(text) > len(entry["text"]):
                entry["text"] = text
            if authored_at and (not entry["first_seen"] or authored_at < entry["first_seen"]):
                entry["first_seen"] = authored_at
            entry["last_seen"] = max(entry["last_seen"], authored_at)
    candidates = tuple(
        ClaimCandidate(
            candidate_id=identity,
            text=entry["text"],
            normalized=entry["normalized"],
            first_seen=entry["first_seen"],
            last_seen=entry["last_seen"],
            sources=tuple(entry["sources"]),
        )
        for identity, entry in sorted(kept.items())
    )
    return ScreeningReport(
        records=records,
        facts=facts,
        candidates=candidates,
        quarantined=tuple(quarantined),
        reasons=dict(sorted(reasons.items())),
    )
