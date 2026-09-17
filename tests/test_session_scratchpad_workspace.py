"""A session scratchpad is not a project, but it names the project it served.

Measured 2026-09-01: 67 workspaces in the index, carrying 376 conversations,
were paths of the form
`/private/tmp/claude-501/<encoded project>/<session uuid>/scratchpad`, one per
session and per subdirectory a session made. They inflated the project count
behind a 2.1% coverage reading, and no `project_workspace` ever resolves to one,
so nothing could recall them. The segment before the uuid is the working
directory the session ran in, so the conversation is given back to that project
instead of being discarded -- project-after's 97 conversations under one such path are
project-after's. The 67 collapse to 19 real projects: 331 conversations remapped, 45
dropped because the project they name is gone from disk.
"""

from pathlib import Path

import pytest

from atrium.ingest.canonical_workspace import canonical_workspace

SESSION = "23913b75-b650-419a-b18d-91c2b36abb1f"


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """A home directory with the project shapes the real encoding is lossy over."""
    (tmp_path / "p" / "project-after").mkdir(parents=True)
    (tmp_path / "p" / "inbox-tool").mkdir(parents=True)
    (tmp_path / "p" / "arcade" / ".worktrees" / "bot-1").mkdir(parents=True)
    return tmp_path


def _encoded(path: Path) -> str:
    """The exporter's spelling of a directory: non-alphanumerics become hyphens."""
    import re

    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def _scratchpad(path: Path, root: str = "/private/tmp/claude-501") -> str:
    return f"{root}/{_encoded(path)}/{SESSION}/scratchpad"


def test_a_scratchpad_becomes_the_project_the_session_worked_in(home: Path):
    workspace = _scratchpad(home / "p" / "project-after")
    assert canonical_workspace(workspace, home) == "[HOME]/p/project-after"


def test_a_subdirectory_of_the_scratchpad_is_the_same_project(home: Path):
    """Sessions make their own directories under it; they are the same session."""
    workspace = _scratchpad(home / "p" / "project-after") + "/reading/group"
    assert canonical_workspace(workspace, home) == "[HOME]/p/project-after"


def test_a_hyphen_in_the_project_name_survives_the_encoding(home: Path):
    """`inbox-tool` and `inbox/companion` encode identically.

    Splitting on hyphens would invent `[HOME]/p/inbox/companion`, a phantom
    project of exactly the kind this removes, so the decode is a search of the
    real tree.
    """
    workspace = _scratchpad(home / "p" / "inbox-tool")
    assert canonical_workspace(workspace, home) == "[HOME]/p/inbox-tool"


def test_an_ambiguous_encoding_names_no_project(home: Path):
    """`inbox-tool` and `inbox/companion` cannot both be the answer.

    Preferring either one files a session run in the other's directory under
    this one: not a phantom project but a real project's memory, quietly
    absorbing another's conversations. Nothing is a safer answer than a guess.
    """
    (home / "p" / "inbox" / "companion").mkdir(parents=True)
    workspace = _scratchpad(home / "p" / "inbox-tool")
    assert canonical_workspace(workspace, home) is None


def test_a_home_sibling_directory_is_not_read_as_being_inside_home(home: Path):
    """The prefix test compares encoded strings, where `/` and `-` are the same.

    `<home>-backup/p/project-after` encodes with `<home>`'s encoding as a prefix, so the
    guard alone would let it through; it is dropped because no directory under
    the real home encodes to the whole segment.
    """
    outside = home.parent / (home.name + "-backup") / "p" / "project-after"
    assert canonical_workspace(_scratchpad(outside), home) is None


def test_a_worktree_under_a_dot_directory_resolves(home: Path):
    """A dot encodes to a hyphen too, so `arcade/.worktrees` reads `arcade--worktrees`."""
    workspace = _scratchpad(home / "p" / "arcade" / ".worktrees" / "bot-1")
    assert canonical_workspace(workspace, home) == "[HOME]/p/arcade/.worktrees/bot-1"


def test_a_scratchpad_under_another_temp_root_is_still_a_scratchpad(home: Path):
    """`/tmp/claude-0` appears in this archive beside `/private/tmp/claude-501`."""
    workspace = _scratchpad(home / "p" / "project-after", root="/tmp/claude-0")
    assert canonical_workspace(workspace, home) == "[HOME]/p/project-after"


def test_a_rename_is_still_folded_after_the_decode(home: Path):
    """The scratchpad decodes to the old name, and the alias must still apply."""
    (home / "p" / "consumer-pv").mkdir()
    workspace = _scratchpad(home / "p" / "consumer-pv")
    aliases = {"[HOME]/p/consumer-pv": "[HOME]/p/consumer-g"}
    assert canonical_workspace(workspace, home, aliases) == "[HOME]/p/consumer-g"


def test_an_unrecoverable_scratchpad_is_dropped(home: Path):
    """A project that is gone from disk cannot be named, and a guess is a phantom."""
    workspace = _scratchpad(home / "p" / "deleted-last-year")
    assert canonical_workspace(workspace, home) is None


def test_a_scratchpad_outside_the_home_directory_is_dropped(home: Path):
    """A session run in `/private/tmp` or at `/` was in no project at all."""
    assert canonical_workspace(f"/tmp/claude-0/-private-tmp/{SESSION}/scratchpad", home) is None
    assert canonical_workspace(f"/tmp/claude-0/-/{SESSION}/scratchpad", home) is None


def test_a_normal_workspace_is_untouched(home: Path):
    """Only the scratchpad shape is rewritten; every other path keeps its spelling."""
    assert canonical_workspace(f"{home}/p/project-after", home) == "[HOME]/p/project-after"
    assert canonical_workspace("[HOME]/p/project-after", home) == "[HOME]/p/project-after"
    assert canonical_workspace("/opt/src/thing", home) == "/opt/src/thing"


def test_a_temp_path_that_is_not_a_scratchpad_is_untouched(home: Path):
    """The uuid and the scratchpad directory are both part of the shape."""
    workspace = f"/private/tmp/claude-501/{_encoded(home / 'p' / 'project-after')}/{SESSION}/build"
    assert canonical_workspace(workspace, home) == workspace


def test_a_scratchpad_shape_outside_a_temp_root_is_untouched(home: Path):
    """The `claude-<uid>` parent is part of the shape too.

    Without it, a directory of this shape sitting inside a real project matches,
    and that project's records are re-filed under whatever the encoded segment
    names -- here atrium's would become project-after's.
    """
    workspace = f"{home}/p/mem/{_encoded(home / 'p' / 'project-after')}/{SESSION}/scratchpad"
    assert canonical_workspace(workspace, home) == workspace.replace(str(home), "[HOME]", 1)


def test_a_project_directory_that_is_a_symlink_still_decodes(tmp_path: Path) -> None:
    """A project on another volume is reached through a symlink, and is a project.

    The obvious guard against the encoded-prefix ambiguity -- resolving the
    decoded path and asserting it is still under home -- rejects exactly this
    case, and `~/p/client-site -> /Volumes/archive-volume/client-site` is a live
    example on this machine. `descend_encoded_segment` walks only real children of home, so
    the result is under home by construction and the guard buys nothing.
    """
    home = tmp_path / "home"
    (home / "p").mkdir(parents=True)
    elsewhere = tmp_path / "volume" / "client-site"
    elsewhere.mkdir(parents=True)
    (home / "p" / "client-site").symlink_to(elsewhere)

    workspace = (
        f"/private/tmp/claude-501/{_encoded(home / 'p' / 'client-site')}/{SESSION}/scratchpad"
    )
    assert canonical_workspace(workspace, home) == "[HOME]/p/client-site"
