import subprocess

import pytest

from atrium.synthesize.codex_lane_call import codex_lane_call
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError
from atrium.synthesize.synthesis_schema import SYNTHESIS_TOOL


def _stub(stderr: str):
    def run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)

    return run


def test_usage_limit_is_a_quota_wall(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess, "run", _stub("You've hit your usage limit. Try again at 22:29.")
    )
    with pytest.raises(QuotaExhaustedError):
        codex_lane_call("system", "user", SYNTHESIS_TOOL)


def test_other_failures_stay_runtime_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", _stub("network unreachable"))
    with pytest.raises(RuntimeError) as caught:
        codex_lane_call("system", "user", SYNTHESIS_TOOL)
    assert not isinstance(caught.value, QuotaExhaustedError)
