"""Which tool calls count as work that a session should record."""

from atrium.session.is_work_tool_use import is_work_tool_use


def _call(name, **tool_input):
    return {"type": "tool_use", "name": name, "input": tool_input}


def test_file_edits_and_commits_are_work():
    assert is_work_tool_use(_call("Edit", file_path="a"))
    assert is_work_tool_use(_call("Write", file_path="a"))
    assert is_work_tool_use(_call("Bash", command="git add a && git commit -qm x"))
    assert is_work_tool_use(_call("Bash", command="git -C ~/p commit -m x"))


def test_reads_and_other_shell_commands_are_not_work():
    assert not is_work_tool_use(_call("Read", file_path="a"))
    assert not is_work_tool_use(_call("Bash", command="git log --oneline"))
    assert not is_work_tool_use(_call("Bash", command="echo committed"))
    assert not is_work_tool_use({"type": "text", "text": "git commit"})
    assert not is_work_tool_use("Edit")
