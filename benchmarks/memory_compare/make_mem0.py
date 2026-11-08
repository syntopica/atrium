"""Create the real Mem0 stack with offline embedding and inference dependencies."""

from pathlib import Path
from unittest.mock import patch

from mem0 import Memory
from mem0.utils.factory import EmbedderFactory, LlmFactory

from benchmarks.memory_compare.reject_inference import RejectInference


def make_mem0(directory: Path, embedder):
    """Inject frozen vectors while leaving storage and ranking unmodified."""
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "paired_memory",
                "embedding_model_dims": 384,
                "path": ":memory:",
                "on_disk": False,
            },
        },
        "embedder": {"provider": "ollama", "config": {}},
        "llm": {"provider": "ollama", "config": {}},
        "history_db_path": str(directory / "mem0-history.sqlite3"),
    }
    with (
        patch.object(EmbedderFactory, "create", return_value=embedder),
        patch.object(LlmFactory, "create", return_value=RejectInference()),
    ):
        return Memory.from_config(config)
