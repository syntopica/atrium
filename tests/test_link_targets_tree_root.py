"""A wiki link written from the root of the note's own tree resolves there."""

from atrium.context.link_targets import link_targets


def test_a_tree_rooted_link_is_tried_under_the_notes_top_directory():
    targets = link_targets("See [[topics/llm-wiki]].", "brain/projects/atrium.md")
    assert "brain/topics/llm-wiki.md" in targets[0]


def test_relative_and_instance_root_candidates_come_first():
    targets = link_targets("[[topics/llm-wiki]]", "brain/projects/atrium.md")
    assert targets[0][:2] == ("brain/projects/topics/llm-wiki.md", "topics/llm-wiki.md")


def test_a_note_at_the_instance_root_gains_no_extra_candidate():
    assert link_targets("[[topics/llm-wiki]]", "CLAUDE.md") == [("topics/llm-wiki.md",)]


def test_a_bracketed_citation_linking_to_its_own_section_is_not_a_page():
    assert link_targets("Fact. [[S1]](#sources)", "brain/topics/pacific.md") == []
