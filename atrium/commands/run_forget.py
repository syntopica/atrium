"""The `forget` handler of the atrium CLI."""

import json
from datetime import UTC, datetime
from pathlib import Path

from atrium.erase.hold_locks import hold_locks
from atrium.forget.append_ledger import append_ledger
from atrium.forget.forget_ledger_file import forget_ledger_file
from atrium.forget.forget_plan import forget_plan


def run_forget(index: Path, state: Path, *, restore: str | None, apply: bool) -> int:
    """Forget what the retirement rule selects, or restore a selection.

    Reports first and writes only with ``apply``, holding the refresh lock so
    no ingest reads the ledger mid-append. Nothing leaves the index here: the
    next ingest turns ledgered records away and the conversation's rows are
    rewritten through the ordinary reconciliation path.
    """
    ledger = forget_ledger_file()
    today = datetime.now(UTC).date().isoformat()
    events, report = forget_plan(index, ledger, restore, today)
    if apply:
        try:
            with hold_locks([state / "refresh.lock"]):
                # Planned again under the lock: a refresh may have changed the index.
                events, report = forget_plan(index, ledger, restore, today)
                append_ledger(ledger, events)
        except BlockingIOError:
            print("refused: a refresh holds the instance; run again after it")
            return 3
        report["applied"] = True
    report["ledger"] = str(ledger)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if apply and events:
        print("takes effect at the next ingest; until then the index still serves these records")
    return 0
