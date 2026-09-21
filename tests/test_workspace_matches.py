"""A project is itself and what is under it, never a name-prefix neighbour."""

from atrium.recall.workspace_matches import workspace_matches


def test_the_project_root_belongs_to_itself():
    assert workspace_matches("[HOME]/p/project-after", "[HOME]/p/project-after")


def test_a_subdirectory_belongs_to_the_project():
    assert workspace_matches("[HOME]/p/project-after/apps/web", "[HOME]/p/project-after")


def test_a_name_prefix_neighbour_does_not():
    """Both of these are real projects in this corpus, and folding the second
    into the first would silently synthesize 1,017 conversations of the wrong
    one."""
    assert not workspace_matches("[HOME]/p/project-after-backfill", "[HOME]/p/project-after")


def test_an_absent_workspace_matches_nothing():
    assert not workspace_matches(None, "[HOME]/p/project-after")
    assert not workspace_matches("", "[HOME]/p/project-after")


def test_a_trailing_slash_on_the_project_changes_nothing():
    assert workspace_matches("[HOME]/p/project-after/apps", "[HOME]/p/project-after/")
