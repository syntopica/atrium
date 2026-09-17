"""Keep private project and account names out of this public repository.

The pattern list lives in the private instance, not here: a denylist of client
names published beside the code it protects tells a reader exactly what to look
for in the history. `SYNTOPICA_PERSONAL_DATA_PATTERNS` points at it, and an
unset variable skips, so a contributor can run the suite without one. A skipped
scan is not clearance: the owner's publication check sets the variable, and the
scan fails there when the file is missing or empty.
"""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Three commit messages from 2026-09-17 carry the real names, and four older
# ones predate the policy. Rewriting shared history would not unpublish them -
# every existing clone keeps them - so they are recorded here and the scan
# covers what comes after.
KNOWN_EXPOSED_COMMITS = frozenset(
    {
        "8a3cead",
        "ab75687",
        "cad996d",
        "4c2b4e3",
        "92311ce",
        "7b2560e",
        "a97f991",
        "eb8ccc6",
    }
)


def _patterns() -> str:
    path = os.environ.get("SYNTOPICA_PERSONAL_DATA_PATTERNS")
    if not path:
        pytest.skip("SYNTOPICA_PERSONAL_DATA_PATTERNS is unset")
    assert Path(path).is_file(), f"pattern file missing: {path}"
    assert Path(path).read_text(encoding="utf-8").strip(), f"pattern file empty: {path}"
    return path


def test_no_private_name_in_tracked_files() -> None:
    patterns = _patterns()
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    files = [name for name in listed.stdout.split("\0") if name and (ROOT / name).exists()]
    assert files, "no tracked files to scan: the guard would pass vacuously"
    found = subprocess.run(
        ["rg", "-a", "-l", "-i", "-f", patterns, *files],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert found.returncode in (0, 1), found.stderr
    matches = sorted(found.stdout.splitlines())
    assert not matches, f"Private names in {len(matches)} files:\n" + "\n".join(matches)


def test_no_private_name_in_commit_messages() -> None:
    patterns = _patterns()
    messages = subprocess.run(
        ["git", "log", "--format=%h%x00%B%x00%x00"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    listed = [
        entry.split("\0", 1) for entry in messages.stdout.split("\0\0") if entry.strip("\0\n")
    ]
    expressions = [
        line
        for line in Path(patterns).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    offenders = sorted(
        sha.strip("\n")
        for sha, body in listed
        if sha.strip("\n") not in KNOWN_EXPOSED_COMMITS
        and any(word.lower() in body.lower() for word in expressions)
    )
    assert not offenders, "Private names in commit messages: " + ", ".join(offenders)
