"""Whether a conversation is the pipeline's own machine traffic."""

import re

from atrium.ingest.atrium_codex_workspace import ATRIUM_CODEX_WORKSPACE


def is_excluded_automation(provider: str | None, workspace: str | None) -> bool:
    """Return True for a conversation the index must not serve or synthesize.

    ``workspace`` is the archive's own value, before canonicalisation: the
    temporary directory is the evidence, and nothing downstream should be able to
    rewrite it away.
    """
    return (
        provider == "codex"
        and bool(workspace)
        and bool(re.match(ATRIUM_CODEX_WORKSPACE, workspace or ""))
    )
