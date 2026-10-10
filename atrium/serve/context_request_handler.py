"""Read one JSON request line from the socket and write one JSON reply line."""

import json
import socketserver
import sys
from typing import Any

from atrium.serve.serve_context_request import serve_context_request


class ContextRequestHandler(socketserver.StreamRequestHandler):
    """One request per connection; the server object carries the shared state."""

    def handle(self) -> None:
        """Answer, or reply with the error rather than dropping the connection."""
        try:
            request = json.loads(self.rfile.readline())
            # A ContextServer; typed loosely because the server imports this
            # handler, so naming the class here would be an import cycle.
            server: Any = self.server
            reply = serve_context_request(request, server.index, server.holder, server.embedder)
        except (ValueError, KeyError, TypeError) as error:
            reply = {"error": f"bad_request: {error}"}
        except Exception as error:
            print(f"atrium serve-context: request failed: {error!r}", file=sys.stderr, flush=True)
            reply = {"error": "service_failure"}
        try:
            self.wfile.write(
                json.dumps(reply, ensure_ascii=False, allow_nan=False).encode() + b"\n"
            )
        except (BrokenPipeError, ConnectionResetError):
            return
