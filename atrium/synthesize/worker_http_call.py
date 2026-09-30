"""One authenticated JSON request to the worker coordinator, stdlib only."""

import json
import os
import urllib.request
from pathlib import Path
from typing import Any


def worker_http_call(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    """Send one request; return the decoded JSON body, or None when it is empty."""
    base = os.environ.get("ATRIUM_WORKER_URL", "http://127.0.0.1:8765").rstrip("/")
    token = Path(os.environ["ATRIUM_WORKER_TOKEN_FILE"]).read_text().strip()
    # UTF-8, not ASCII escapes: an escaped accent costs six bytes, which took a
    # Spanish transcript under the 512 KiB prompt ceiling past the coordinator's
    # 1 MiB body limit, answered by a closed socket (2026-10-01).
    data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    request = urllib.request.Request(base + path, data, headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
        return json.loads(raw) if raw else None
