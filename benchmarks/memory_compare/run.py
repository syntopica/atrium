"""Offline command-line entry point for the paired memory benchmark."""

import argparse
import os
import sys
from pathlib import Path

from benchmarks.memory_compare.block_network import block_network


def main() -> None:
    """Set privacy and resource controls before importing third-party clients."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--evaluations", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    os.umask(0o077)
    for name in list(os.environ):
        if any(term in name.upper() for term in ("API_KEY", "TOKEN", "PASSWORD", "SECRET")):
            os.environ.pop(name)
    os.environ.update(
        {
            "MEM0_TELEMETRY": "false",
            "ANONYMIZED_TELEMETRY": "false",
            "MEM0_DIR": str(arguments.output.resolve() / "mem0-state"),
            "HF_HUB_OFFLINE": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    sys.addaudithook(block_network)
    from benchmarks.memory_compare.execute import execute

    print("offline benchmark starting", flush=True)
    execute(arguments.index, arguments.evaluations, arguments.output)


if __name__ == "__main__":
    main()
