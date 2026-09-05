"""The paths a git worktree does not ignore, or None when the root is not one."""

import subprocess
from pathlib import Path


def git_visible_paths(root: Path) -> set[str] | None:
    """Return every path under ``root`` that its repository does not ignore.

    Tracked files plus untracked ones that survive the ignore rules, as
    POSIX-relative paths. ``None`` means the question does not apply -- the
    root is not in a git worktree, or git could not answer -- and the caller
    should not filter at all rather than filter everything away.

    A curated notes tree says which of its files are content and which are
    scratch, and it says it in `.gitignore`. Reading that instead of a
    hand-kept exclude list is what stops the two from drifting apart: brain
    ignores `inbox/` ("a scratch drop-zone ... emptied after ingestion"),
    `reviews/` and `tools/offers/reports/`, all generated, and indexing them
    put 44 raw newsletter-triage dumps and a memstore graph export into the
    dense lane as curated knowledge. Because they are untracked they also
    differ per machine, so two hosts on the same brain commit indexed
    different note sets -- 268 against 243, measured 2026-09-05. An exclude
    list would have to be edited every time the notes repo adds an ignore
    rule, and a directory name is the wrong unit anyway: brain ignores
    `tools/offers/reports/` while `docs/reports/` is curated content.
    """
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            capture_output=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return {
        entry.decode("utf-8", errors="replace") for entry in completed.stdout.split(b"\0") if entry
    }
