"""When a stopping session owes a record: prompts, not transcript size."""

from datetime import UTC, datetime

from atrium.session.over_stop_limits import over_stop_limits
from atrium.session.stop_limits import MAX_UNRECORDED_SECONDS, MIN_NEW_PROMPTS

_NOW = datetime(2026, 9, 17, 21, 0, tzinfo=UTC)
_JUST_NOW = "2026-09-17T20:58:00.000Z"
_LONG_AGO = "2026-09-17T19:40:00.000Z"


def test_one_prompt_of_heavy_tool_work_is_not_a_record() -> None:
    """Measured on a real session: one prompt produced 89 KB to 690 KB of records.

    The old byte limit was 32 KiB, so every turn of an engineering session
    crossed it and the hook refused the stop after each one.
    """
    assert not over_stop_limits(690_000, 1, _JUST_NOW, _NOW)


def test_enough_prompts_is_a_record_however_short() -> None:
    assert over_stop_limits(5_000, MIN_NEW_PROMPTS, _JUST_NOW, _NOW)


def test_an_aged_interval_with_real_work_is_a_record() -> None:
    """The age rule bounds the loss: nothing waits longer than the window."""
    assert over_stop_limits(100_000, 1, _LONG_AGO, _NOW)
    assert (_NOW - datetime.fromisoformat(_LONG_AGO.replace("Z", "+00:00"))).total_seconds() >= (
        MAX_UNRECORDED_SECONDS
    )


def test_an_aged_interval_of_nothing_is_not_a_record() -> None:
    assert not over_stop_limits(500, 1, _LONG_AGO, _NOW)


def test_no_prompt_is_never_a_record() -> None:
    """The recording turn's own bookkeeping must not trigger the next reminder."""
    assert not over_stop_limits(1_000_000, 0, _LONG_AGO, _NOW)
