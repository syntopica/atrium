"""An ingest that finished is what the staleness checks call a refresh."""

from pathlib import Path

from atrium.doctor.refresh_health import refresh_health
from atrium.state.record_refresh import record_refresh


def test_a_recorded_refresh_clears_the_never_ran_finding(tmp_path: Path) -> None:
    stamp = tmp_path / "state" / "last-refresh"
    assert refresh_health(stamp).severity == "broken"
    record_refresh(stamp)
    assert refresh_health(stamp).severity == "ok"
