import subprocess
from pathlib import Path

from atrium.ingest.read_notes import read_notes


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_a_note_the_repository_ignores_is_not_read(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    (tmp_path / ".gitignore").write_text("scratch/\n")
    (tmp_path / "keep.md").write_text("# kept")
    (tmp_path / "scratch").mkdir()
    (tmp_path / "scratch" / "raw.md").write_text("# raw dump")
    # A directory whose name matches an ignored one elsewhere still counts when
    # this repository tracks it -- the unit is the path, not the name.
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "scratch.md").write_text("# curated")

    paths = {note["path"] for note in read_notes(tmp_path)}
    assert paths == {"keep.md", "docs/scratch.md"}


def test_a_tree_that_is_not_a_repository_is_read_whole(tmp_path: Path) -> None:
    (tmp_path / "one.md").write_text("# one")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "two.md").write_text("# two")

    paths = {note["path"] for note in read_notes(tmp_path)}
    assert paths == {"one.md", "sub/two.md"}


def test_exclude_still_applies_inside_a_repository(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    (tmp_path / "keep.md").write_text("# kept")
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "raw.md").write_text("# tracked raw material")

    paths = {note["path"] for note in read_notes(tmp_path, exclude=("sources",))}
    assert paths == {"keep.md"}
