"""Coverage counted over real projects, not over every directory ever opened."""

from atrium.recall.project_coverage import project_coverage
from atrium.record import Record
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation


def _record(record_id, conversation, workspace, provider="claude-code"):
    return Record(
        record_id=record_id,
        event_id=record_id,
        conversation_id=conversation,
        source_sha256="sha",
        provider=provider,
        role="synthesis" if provider == "synthesis" else "user",
        text="body",
        authored_at=None,
        workspace=workspace,
        title=None,
        event_index=0,
    )


def _index(tmp_path, groups):
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        for conversation, records in groups:
            write_conversation(connection, conversation, records)
    return connection


def test_one_off_directories_do_not_drag_coverage_down(tmp_path):
    """13,162 of 13,269 real workspaces held under five conversations."""
    groups = []
    for n in range(4):
        groups.append((f"big-{n}", [_record(f"b{n}", f"big-{n}", "[HOME]/p/big")]))
    groups.append(("syn", [_record("s", "syn", "[HOME]/p/big", provider="synthesis")]))
    for n in range(40):
        groups.append((f"tiny-{n}", [_record(f"t{n}", f"tiny-{n}", f"[HOME]/tmp/{n}")]))
    connection = _index(tmp_path, groups)

    everything = project_coverage(connection, floor=1)
    real = project_coverage(connection, floor=4)
    connection.close()

    assert everything["projects"] == 41
    assert everything["covered"] == 1
    # Above the floor only the real project survives, and it is covered.
    assert real["projects"] == 1
    assert real["covered"] == 1


def test_the_biggest_uncovered_projects_are_named(tmp_path):
    groups = []
    for n in range(6):
        groups.append((f"a-{n}", [_record(f"a{n}", f"a-{n}", "[HOME]/p/silent")]))
    for n in range(4):
        groups.append((f"b-{n}", [_record(f"b{n}", f"b-{n}", "[HOME]/p/heard")]))
    groups.append(("syn", [_record("s", "syn", "[HOME]/p/heard", provider="synthesis")]))
    connection = _index(tmp_path, groups)

    coverage = project_coverage(connection, floor=4)
    connection.close()

    assert coverage["projects"] == 2
    assert coverage["covered"] == 1
    assert coverage["uncovered"] == [("[HOME]/p/silent", 6)]
