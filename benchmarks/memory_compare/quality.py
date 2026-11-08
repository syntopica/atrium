"""Offline entry point for the separate, expanded-budget quality pass."""

import os
import sys
from pathlib import Path

from benchmarks.memory_compare.block_network import block_network


def main():
    """Apply the same network and single-thread model controls as the main run."""
    os.umask(0o077)
    os.environ.update(
        {
            "HF_HUB_OFFLINE": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    sys.addaudithook(block_network)
    from benchmarks.memory_compare.quality_pass import quality_pass

    print("offline quality pass starting; rerank budget=120s", flush=True)
    quality_pass(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
