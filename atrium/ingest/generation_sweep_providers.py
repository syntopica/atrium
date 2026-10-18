"""The archive providers a full ingest must sweep beyond those its export carries."""

import sqlite3
from collections.abc import Mapping
from typing import Any

from atrium.store.read_archive_revision_providers import read_archive_revision_providers


def generation_sweep_providers(
    connection: sqlite3.Connection, manifest: Mapping[str, Any]
) -> set[str]:
    """Every archive provider when the export is a generation's, else none.

    A generation's full export speaks for every archive provider, including one
    it no longer holds any conversation of. A v1 archive keeps the narrower
    sweep, so an export that lost a provider by accident cannot empty it.
    """
    if manifest.get("generationId") is None:
        return set()
    return read_archive_revision_providers(connection)
