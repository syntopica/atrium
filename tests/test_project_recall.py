"""Session-start recall is scoped to a project, not to an exact directory."""

from atrium.recall.project_workspace import project_workspace
from atrium.recall.recent_episodes import recent_episodes
from atrium.record import Record
from atrium.retrieve.hit import Hit
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation

HOME = "/Users/someone"


def _project(tmp_path, *segments):
    """Make a repository at tmp_path/p/<name> and return (home, path)."""
    home = tmp_path / "home"
    root = home.joinpath(*segments)
    root.mkdir(parents=True, exist_ok=True)
    return home, root


def test_a_live_cwd_is_written_the_way_the_exporter_redacted_it(tmp_path):
    home, root = _project(tmp_path, "p", "mem")
    (root / ".git").mkdir()
    assert project_workspace(root, home) == "[HOME]/p/mem"


def test_a_subdirectory_recalls_its_project_not_itself(tmp_path):
    """A session in apps/web is working on the project, and needs its memory."""
    home, root = _project(tmp_path, "p", "wide-project")
    (root / ".git").mkdir()
    deep = root / "apps" / "web"
    deep.mkdir(parents=True)
    assert project_workspace(deep, home) == "[HOME]/p/wide-project"


def test_both_worktree_layouts_belong_to_their_project(tmp_path):
    """A branch must not get memory of its own and hide the trunk's."""
    home, root = _project(tmp_path, "p", "atc")
    tree = root / ".claude" / "worktrees" / "copilot-mcp"
    tree.mkdir(parents=True)
    # A worktree carries a .git *file*, not a directory.
    (tree / ".git").write_text("gitdir: elsewhere\n")
    assert project_workspace(tree, home) == "[HOME]/p/atc"

    home2, sibling = _project(tmp_path, "p2", "favish-talk.worktrees", "gha-build")
    (sibling / ".git").write_text("gitdir: elsewhere\n")
    assert project_workspace(sibling, home2) == "[HOME]/p2/favish-talk"


def test_a_path_in_no_repository_names_no_project(tmp_path):
    """A bare path would match nothing, and a root path would match everything."""
    home = tmp_path / "home"
    loose = tmp_path / "var" / "T" / "atrium-codex-xo4"
    loose.mkdir(parents=True)
    assert project_workspace(loose, home) is None
    assert project_workspace("/", home) is None


def _episode(index, conversation_id, workspace, authored_at):
    return Record(
        record_id=f"{conversation_id}-{index}",
        event_id=f"ep{index}",
        conversation_id=conversation_id,
        source_sha256=f"s{index}",
        provider="synthesis",
        role="synthesis",
        text=f"episode {index}",
        authored_at=authored_at,
        workspace=workspace,
        title=None,
        event_index=0,
    )


def test_recall_covers_the_project_and_stops_at_its_edge(tmp_path):
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        write_conversation(
            connection,
            "synthesis/a",
            [_episode(1, "synthesis/a", "[HOME]/p/mem", "2026-08-01T00:00:00Z")],
        )
        write_conversation(
            connection,
            "synthesis/b",
            [_episode(2, "synthesis/b", "[HOME]/p/mem/docs", "2026-08-02T00:00:00Z")],
        )
        # A sibling whose name merely starts with the project's must not leak in.
        write_conversation(
            connection,
            "synthesis/c",
            [_episode(3, "synthesis/c", "[HOME]/p/atrium-old", "2026-08-03T00:00:00Z")],
        )
    hits = recent_episodes(connection, "[HOME]/p/mem", 10)
    connection.close()
    assert [hit.text for hit in hits] == ["episode 2", "episode 1"]


def test_the_snapshot_stays_inside_its_budget():
    """The block is paid at the top of every session in this project."""
    from atrium.recall.render_snapshot import render_snapshot

    hits = [
        Hit(
            record_id=f"r{index}",
            text=f"{'title ' * 20}\nbody that must never be rendered",
            score=float(-index),
            lane="recent",
            conversation_id="synthesis/a",
            source_sha256="s",
            authored_at="2026-08-01T00:00:00Z",
            provider="synthesis",
        )
        for index in range(200)
    ]
    block = render_snapshot("[HOME]/p/mem", hits)
    assert len(block) < 4200
    assert "body that must never be rendered" not in block


def test_a_project_with_no_episodes_injects_nothing():
    """Spending context to say nothing is known is worse than saying nothing."""
    from atrium.recall.render_snapshot import render_snapshot

    assert render_snapshot("[HOME]/p/nothing", []) == ""


def test_a_path_is_a_path_not_a_like_pattern(tmp_path):
    """`_` is a LIKE wildcard; 2,585 workspaces in the live index contain one."""
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        write_conversation(
            connection,
            "synthesis/mine",
            [_episode(1, "synthesis/mine", "[HOME]/p/my_app/src", "2026-08-01T00:00:00Z")],
        )
        write_conversation(
            connection,
            "synthesis/theirs",
            [_episode(2, "synthesis/theirs", "[HOME]/p/myXapp/src", "2026-08-02T00:00:00Z")],
        )
    hits = recent_episodes(connection, "[HOME]/p/my_app", 10)
    connection.close()
    assert [hit.text for hit in hits] == ["episode 1"]


def test_a_relative_path_names_the_same_project_as_an_absolute_one(tmp_path, monkeypatch):
    """`--project .` is the natural way to ask about the project you are in."""
    home, root = _project(tmp_path, "p", "mem")
    (root / ".git").mkdir()
    monkeypatch.chdir(root)
    assert project_workspace(".", home) == project_workspace(root, home) == "[HOME]/p/mem"


def test_a_symlinked_checkout_resolves_to_its_real_project(tmp_path):
    """Records were stored under the real path; the link has to reach them."""
    home, root = _project(tmp_path, "p", "mem")
    (root / ".git").mkdir()
    link = tmp_path / "home" / "shortcut"
    link.symlink_to(root)
    assert project_workspace(link, home) == "[HOME]/p/mem"


def test_the_home_directory_is_not_a_project(tmp_path):
    """`[HOME]` as a prefix would match every redacted path in the index."""
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    (home / ".git").mkdir()
    assert project_workspace(home, home) is None
