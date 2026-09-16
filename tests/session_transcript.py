"""A Claude Code transcript the session producer tests can grow line by line."""

import json
from pathlib import Path


class SessionTranscript:
    """Appends records carrying the fields the scan reads and nothing else."""

    def __init__(self, path: Path, entrypoint: str = "cli") -> None:
        self.path = path
        self.entrypoint = entrypoint

    def append(self, *records: dict) -> "SessionTranscript":
        with self.path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps({"entrypoint": self.entrypoint, **record}) + "\n")
        return self

    @staticmethod
    def prompt(uuid: str, text: str, at: str) -> dict:
        return {
            "type": "user",
            "uuid": uuid,
            "timestamp": at,
            "message": {"role": "user", "content": text},
        }

    @staticmethod
    def tool_result(uuid: str, at: str) -> dict:
        return {
            "type": "user",
            "uuid": uuid,
            "timestamp": at,
            "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
        }

    @staticmethod
    def answer(uuid: str, text: str, at: str, model: str = "claude-fable-5-1") -> dict:
        return {
            "type": "assistant",
            "uuid": uuid,
            "timestamp": at,
            "message": {
                "role": "assistant",
                "model": model,
                "content": [{"type": "text", "text": text}],
            },
        }

    @staticmethod
    def attachment(at: str, size: int = 40_000) -> dict:
        return {
            "type": "attachment",
            "uuid": "att",
            "timestamp": at,
            "attachment": {"x": "y" * size},
        }
