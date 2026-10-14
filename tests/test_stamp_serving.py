"""A context response says which path answered it and how long it took."""

import time

from atrium.context.stamp_serving import stamp_serving


def test_stamp_names_the_path_and_the_elapsed_milliseconds():
    started = time.perf_counter() - 0.25
    result = stamp_serving({"evidence": []}, "service_timeout", started)
    assert result["served_by"] == "service_timeout"
    assert 240 <= result["elapsed_ms"] < 5000
