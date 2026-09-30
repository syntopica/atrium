import json
from typing import Any

from atrium.synthesize.worker_http_call import worker_http_call


def test_the_body_is_utf8_not_ascii_escapes(monkeypatch, tmp_path):
    token = tmp_path / "atrium.token"
    token.write_text("tok")
    monkeypatch.setenv("ATRIUM_WORKER_TOKEN_FILE", str(token))
    sent: dict[str, Any] = {}

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def read(self) -> bytes:
            return b'{"ok": true}'

    def fake_urlopen(request: Any, timeout: float) -> Response:
        sent["data"] = request.data
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert worker_http_call("POST", "/v1/jobs", {"prompt": "análisis ñ"}) == {"ok": True}
    assert "análisis ñ".encode() in sent["data"]
    assert json.loads(sent["data"]) == {"prompt": "análisis ñ"}
