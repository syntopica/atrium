"""Session-start recall is scoped to a project, not to an exact directory."""

from atrium.recall.project_workspace import project_workspace
from atrium.recall.recent_episodes import recent_episodes
from atrium.record import Record
from atrium.retrieve.hit import Hit
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation

HOME = "/Users/someone"


def test_a_live_cwd_is_written_the_way_the_exporter_redacted_it():
    assert project_workspace(f"{HOME}/p/atrium", HOME) == "[HOME]/p/atrium"


def test_a_subdirectory_recalls_its_project():
    assert project_workspace(f"{HOME}/p/consumer-y/apps/web", HOME) == (
        "[HOME]/p/consumer-y/apps/web"
    )


def test_both_worktree_layouts_belong_to_their_project():
    """A branch must not get memory of its own and hide the trunk's."""
    assert project_workspace(f"{HOME}/p/atc/.claude/worktrees/copilot-mcp", HOME) == "[HOME]/p/atc"
    assert (
        project_workspace(f"{HOME}/p/client-talk.worktrees/gha-build", HOME)
        == "[HOME]/p/client-talk"
    )


def test_a_path_outside_home_is_left_alone():
    assert project_workspace("/var/folders/k2/T/atrium-codex-xo4", HOME) == (
        "/var/folders/k2/T/atrium-codex-xo4"
    )


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
            [_episode(1, "synthesis/a", "[HOME]/p/atrium", "2026-08-01T00:00:00Z")],
        )
        write_conversation(
            connection,
            "synthesis/b",
            [_episode(2, "synthesis/b", "[HOME]/p/atrium/docs", "2026-08-02T00:00:00Z")],
        )
        # A sibling whose name merely starts with the project's must not leak in.
        write_conversation(
            connection,
            "synthesis/c",
            [_episode(3, "synthesis/c", "[HOME]/p/atrium-old", "2026-08-03T00:00:00Z")],
        )
    hits = recent_episodes(connection, "[HOME]/p/atrium", 10)
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
    block = render_snapshot("[HOME]/p/atrium", hits)
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
