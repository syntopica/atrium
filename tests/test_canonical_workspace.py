"""A project must have one spelling, or half its memory is unreachable.

Measured 2026-09-01: 29 projects sat in the index under both `[HOME]/p/x` and
`/Users/<name>/p/x`, with 4,053 conversations under the unredacted spelling.
Project recall and `--project` search ask for the `[HOME]` form, so that half
answered nothing -- a third of intelifactu was invisible from inside
intelifactu.
"""

from atrium.ingest.canonical_workspace import canonical_workspace
from atrium.ingest.to_records import to_records

HOME = "/Users/someone"
LONG = "a sentinel passage long enough not to be an acknowledgement"


def test_a_missed_redaction_is_folded_back():
    assert canonical_workspace(f"{HOME}/p/intelifactu", HOME) == "[HOME]/p/intelifactu"


def test_an_already_redacted_workspace_is_untouched():
    assert canonical_workspace("[HOME]/p/intelifactu", HOME) == "[HOME]/p/intelifactu"


def test_the_home_directory_itself_folds_to_the_marker():
    assert canonical_workspace(HOME, HOME) == "[HOME]"


def test_a_path_outside_home_keeps_its_spelling():
    """Not every absolute path is a leaked home; /opt/src is simply /opt/src."""
    assert canonical_workspace("/opt/src/thing", HOME) == "/opt/src/thing"


def test_a_sibling_directory_is_not_a_prefix_match():
    """`/Users/someone-else` starts with `/Users/someone` as a string."""
    assert canonical_workspace(f"{HOME}-else/p/x", HOME) == f"{HOME}-else/p/x"


def test_absent_workspaces_stay_absent():
    assert canonical_workspace(None) is None
    assert canonical_workspace("") == ""


def test_ingest_stamps_the_canonical_spelling(monkeypatch):
    import pathlib

    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: pathlib.Path(HOME)))
    conversation = {
        "id": "conv",
        "source": "pi",
        "workspace": f"{HOME}/p/intelifactu",
        "provenance": {"contentSha256": "sha"},
        "events": [{"id": "e", "kind": "message", "role": "user", "text": LONG}],
    }
    records = list(to_records(conversation))
    assert [r.workspace for r in records] == ["[HOME]/p/intelifactu"]
