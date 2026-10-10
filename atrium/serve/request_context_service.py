"""Ask the resident context service, without ever waiting past a deadline."""

import json
import socket
import time
from pathlib import Path
from typing import Any


def request_context_service(
    socket_path: Path, request: dict[str, Any], timeout: float
) -> dict[str, Any] | None:
    """Return the service's reply, or None when no service is listening.

    Raises TimeoutError when a service is listening but the whole exchange does
    not finish within ``timeout`` seconds: the caller must report that rather
    than start the slow in-process retrieval the service exists to avoid.
    """
    if not socket_path.exists():
        return None
    deadline = time.monotonic() + timeout
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(timeout)
        try:
            client.connect(str(socket_path))
        except (ConnectionRefusedError, FileNotFoundError):
            return None
        client.sendall(json.dumps(request, ensure_ascii=False).encode() + b"\n")
        received = bytearray()
        while not received.endswith(b"\n"):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("context service did not answer in time")
            client.settimeout(remaining)
            chunk = client.recv(65536)
            if not chunk:
                return None
            received.extend(chunk)
    finally:
        client.close()
    reply: dict[str, Any] = json.loads(received)
    return reply
