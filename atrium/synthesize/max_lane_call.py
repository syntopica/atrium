"""One forced-tool Messages call on the Max OAuth lane, rotating accounts."""

import json
import time
import urllib.error
import urllib.request
from typing import Any

MODEL = "claude-sonnet-5"
_ENDPOINT = "https://api.anthropic.com/v1/messages"
# The Max lane only serves requests that identify as Claude Code: the beta
# pair, the CLI user agent, and the Claude Code line as the FIRST system
# block. Without them every call 429s regardless of quota.
_IDENTITY = "You are Claude Code, Anthropic's official CLI for Claude."
_MAX_ATTEMPTS_PER_TOKEN = 2
_BACKOFF_SECONDS = 20.0


def max_lane_call(
    tokens: list[str], system_text: str, user_text: str, tool: dict[str, Any]
) -> dict[str, Any]:
    """Return {"input": <tool_use input>, "model": <resolved id>, "usage": ...}.

    Rotates through the account tokens on 429/5xx -- one rate-limited Max
    account must not stall the run while another has headroom. Raises after
    every token has been exhausted.
    """
    body = json.dumps(
        {
            "model": MODEL,
            "max_tokens": 4000,
            "system": [
                {"type": "text", "text": _IDENTITY},
                {"type": "text", "text": system_text},
            ],
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": tool["name"]},
            "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": user_text}],
        }
    ).encode()

    last_error = "no attempt made"
    for attempt in range(_MAX_ATTEMPTS_PER_TOKEN):
        for token in tokens:
            request = urllib.request.Request(
                _ENDPOINT,
                data=body,
                headers={
                    "content-type": "application/json",
                    "anthropic-version": "2023-06-01",
                    "authorization": f"Bearer {token}",
                    "anthropic-beta": "oauth-2025-04-20,claude-code-20250219",
                    "x-app": "cli",
                    "user-agent": "claude-cli/2.1.0 (external, cli)",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=600) as response:
                    payload = json.loads(response.read())
            except urllib.error.HTTPError as error:
                last_error = f"{error.code} {error.read()[:300]!r}"
                if error.code in (429, 500, 502, 503, 529):
                    continue
                raise RuntimeError(f"max lane request failed: {last_error}") from error
            except urllib.error.URLError as error:
                last_error = str(error)
                continue
            tool_use = next(
                (block for block in payload.get("content", []) if block.get("type") == "tool_use"),
                None,
            )
            if tool_use is None:
                raise RuntimeError("max lane response carried no tool_use block")
            return {
                "input": tool_use["input"],
                "model": payload.get("model"),
                "usage": payload.get("usage", {}),
            }
        if attempt + 1 < _MAX_ATTEMPTS_PER_TOKEN:
            time.sleep(_BACKOFF_SECONDS)
    raise RuntimeError(f"every max lane account is exhausted; last error: {last_error}")
