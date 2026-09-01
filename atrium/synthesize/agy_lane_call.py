"""One structured synthesis call through agy's Gemini bulk quota."""

import json
import re
import subprocess
import time
from typing import Any, cast

from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError

# The brain's routing rule: whole-corpus bulk goes to Gemini via agy -- its
# quota is the one that survives it. Newest Flash at medium effort; synthesis
# is extraction, not judgement, which is the one place the measured comparison
# preferred Pro.
AGY_MODEL_ID = "gemini-3.7-flash-medium"

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)
_ATTEMPTS = 3
_BACKOFF_SECONDS = 20.0
# Comfortably under macOS ARG_MAX (~1 MiB): the prompt rides on the --print
# flag itself, so an oversized episode must fail here, not as an opaque E2BIG.
_ARGV_CEILING = 700_000


def agy_lane_call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
    """Return {"input": ..., "model": ..., "usage": ...} from one agy print run.

    Gemini prompting inverts the usual order: the transcript goes FIRST and
    the instructions last, anchored to it -- instructions ahead of a large
    context get diluted. Slash expansion disabled because the prompt inlines
    captured conversation text (the brain's standing rule for passes over
    untrusted inline content; --mode plan is a no-op with it disabled and only
    polluted stderr). Retries with backoff absorb the 503 bursts that eight
    parallel workers provoke.
    """
    schema = {**tool["input_schema"], "additionalProperties": False}
    prompt = (
        f"EPISODE TRANSCRIPT:\n{user_text}\n\n---\n\n"
        f"{system_text}\n\n"
        "Based entirely on the transcript above, using no outside knowledge, "
        "answer with ONE JSON object matching this schema and nothing else -- "
        "no prose, no code fence:\n"
        f"{json.dumps(schema)}"
    )
    # agy does not read the prompt from stdin: it must be attached to the
    # flag itself (`--print='...'`). Episodes are ceiling-bounded well under
    # ARG_MAX, but guard anyway rather than fail with an opaque E2BIG.
    if len(prompt) > _ARGV_CEILING:
        raise RuntimeError(f"prompt too large for argv ({len(prompt)} chars)")
    last_error = "no attempt"
    for attempt in range(_ATTEMPTS):
        if attempt:
            time.sleep(_BACKOFF_SECONDS * attempt)
        completed = subprocess.run(  # noqa: PLW1510 -- returncode handled below
            [
                "agy",
                f"--print={prompt}",
                "--model",
                AGY_MODEL_ID,
                "--disable-slash-commands",
                "--print-timeout",
                "10m",
            ],
            capture_output=True,
            text=True,
            timeout=900,
        )
        if completed.returncode != 0:
            # A spent quota window cannot succeed until its reset: raising a
            # typed error lets the pass abort instead of failing every
            # remaining episode one by one through the whole backoff ladder.
            if "quota reached" in (completed.stderr + completed.stdout).lower():
                raise QuotaExhaustedError(completed.stderr.strip() or completed.stdout.strip())
            # stderr's tail is often only a benign warning; the real error
            # (503s, eligibility checks) rides stdout. Keep both.
            last_error = (
                f"agy failed ({completed.returncode}): "
                f"stdout={completed.stdout[-250:]!r} stderr={completed.stderr[-250:]!r}"
            )
            continue
        match = _JSON_BLOCK.search(completed.stdout)
        if match is None:
            last_error = f"agy returned no JSON object: {completed.stdout[-250:]!r}"
            continue
        try:
            output = _parse_loose_json(match.group(0))
        except json.JSONDecodeError as error:
            last_error = f"agy JSON did not parse: {error}"
            continue
        missing = [key for key in tool["input_schema"]["required"] if key not in output]
        if missing:
            last_error = f"agy output missing required keys: {missing}"
            continue
        return {"input": output, "model": AGY_MODEL_ID, "usage": {}}
    raise RuntimeError(last_error)


def _parse_loose_json(text: str) -> dict[str, Any]:
    """Parse Gemini's JSON, tolerating its two observed sloppinesses.

    Raw control characters inside strings (strict=False accepts them) and
    invalid backslash escapes (repaired to literal backslashes). Anything
    still broken raises and the retry loop takes another attempt.
    """
    try:
        return cast("dict[str, Any]", json.loads(text, strict=False))
    except json.JSONDecodeError:
        repaired = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", text)
        return cast("dict[str, Any]", json.loads(repaired, strict=False))
