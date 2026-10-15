"""The `atrium remember` command: one statement as JSON in, receipt out."""

import json
import sys
from pathlib import Path

from atrium.recall.project_workspace import project_workspace
from atrium.remember.remember import remember
from atrium.session.invalid_synthesis_error import InvalidSynthesisError


def run_remember_cli(index: Path, registry: Path, project: str, supersedes: list[str]) -> int:
    """Read the statement from stdin; exit 2 on a refused statement, with the reason."""
    from atrium.embed.embedder import Embedder

    workspace = project_workspace(project)
    if workspace is None:
        print(f"atrium remember: {project!r} is in no repository", file=sys.stderr)
        return 2
    try:
        payload = json.loads(sys.stdin.read() or "")
    except ValueError:
        print("atrium remember: stdin is not JSON", file=sys.stderr)
        return 2
    try:
        receipt = remember(
            payload,
            workspace,
            supersedes=supersedes,
            registry=registry,
            index=index,
            embedder=Embedder(),
        )
    except (InvalidSynthesisError, ValueError) as error:
        print(f"atrium remember: {error}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, ensure_ascii=False))
    return 0
