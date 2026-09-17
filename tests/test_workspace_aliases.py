"""A renamed project keeps its memory, under the name it has now.

`p/project-before` holds 558 conversations from 2026-06-14 to 2026-07-10 and
`p/project-after` picks up on 2026-07-12 -- the same project, renamed. Without
folding the two, a session there recalls nothing from the project's first
month.
"""

import json

from atrium.ingest.canonical_workspace import canonical_workspace
from atrium.ingest.workspace_alias import WorkspaceAlias
from atrium.ingest.workspace_aliases import workspace_aliases

ALIASES = {"[HOME]/p/project-before": "[HOME]/p/project-after"}
HOME = "/Users/someone"


def test_the_old_name_becomes_the_current_one():
    assert canonical_workspace("[HOME]/p/project-before", HOME, ALIASES) == "[HOME]/p/project-after"


def test_subdirectories_of_the_old_name_move_too():
    """Worktrees and tool directories carry the old root as a prefix."""
    assert (
        canonical_workspace("[HOME]/p/project-before/.playwright-mcp", HOME, ALIASES)
        == "[HOME]/p/project-after/.playwright-mcp"
    )


def test_a_missed_redaction_is_aliased_after_being_folded_home():
    """The unredacted spelling of the old name must reach the new one too."""
    assert (
        canonical_workspace(f"{HOME}/p/project-before", HOME, ALIASES) == "[HOME]/p/project-after"
    )


def test_an_unrelated_project_is_untouched():
    assert canonical_workspace("[HOME]/p/vexa", HOME, ALIASES) == "[HOME]/p/vexa"


def test_a_name_prefix_neighbour_is_not_renamed():
    assert (
        canonical_workspace("[HOME]/p/project-before-archive", HOME, ALIASES)
        == "[HOME]/p/project-before-archive"
    )


def test_the_longest_alias_wins():
    """A nested rename must not be shadowed by a shorter one that also matches."""
    aliases = {"[HOME]/p/a": "[HOME]/p/x", "[HOME]/p/a/b": "[HOME]/p/y"}
    assert canonical_workspace("[HOME]/p/a/b/c", HOME, aliases) == "[HOME]/p/y/c"


def test_no_alias_file_means_no_aliases(tmp_path):
    assert workspace_aliases(tmp_path / "absent.json") == {}


def test_a_hand_edited_file_that_does_not_parse_never_stops_an_ingest(tmp_path):
    broken = tmp_path / "aliases.json"
    broken.write_text('{"[HOME]/p/a": "[HOME]/p/b",}')
    assert workspace_aliases(broken) == {}


def test_a_valid_file_is_read(tmp_path):
    path = tmp_path / "aliases.json"
    path.write_text(json.dumps(ALIASES))
    assert workspace_aliases(path) == {
        "[HOME]/p/project-before": WorkspaceAlias("[HOME]/p/project-after")
    }


def test_a_dated_alias_stops_at_its_date(tmp_path):
    """`p/brain` was the wiki until 2026-09-14 and the public engine after."""
    path = tmp_path / "aliases.json"
    path.write_text(json.dumps({"[HOME]/p/brain": {"to": "[HOME]/p/wiki", "until": "2026-09-14"}}))
    aliases = workspace_aliases(path)
    assert aliases == {"[HOME]/p/brain": WorkspaceAlias("[HOME]/p/wiki", "2026-09-14")}
    before = canonical_workspace("[HOME]/p/brain", HOME, aliases, "2026-09-13T23:59:00Z")
    after = canonical_workspace("[HOME]/p/brain/x", HOME, aliases, "2026-09-16T10:00:00Z")
    undated = canonical_workspace("[HOME]/p/brain", HOME, aliases)
    assert (before, after, undated) == ("[HOME]/p/wiki", "[HOME]/p/brain/x", "[HOME]/p/wiki")
