"""The generations an export says it descends from, newest first."""

import json
from pathlib import Path


def archive_generation(path: Path) -> list[str]:
    """Return the manifest's ``generationId`` followed by its ``generationLineage``.

    Generation ids are content hashes, so nothing orders them: only the export
    can say which generations it descends from. The manifest is the first
    non-empty line. A v1 archive, or an export written before scribe stamped its
    generation, names none, and then nothing proves which generation it holds.
    """
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                manifest = json.loads(line)
                if not isinstance(manifest, dict):
                    return []
                current = manifest.get("generationId")
                lineage = manifest.get("generationLineage") or []
                named = [current, *lineage] if isinstance(lineage, list) else [current]
                return [g for g in named if isinstance(g, str) and g]
    return []
