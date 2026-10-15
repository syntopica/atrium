"""The help text of `atrium remember`, which is its contract with the agent."""

REMEMBER_CONTRACT = """\
Keep one statement in this project's memory, searchable at once.

stdin is one JSON object: {"title": "...", "summary": "...", "facts": [...],
"open_ends": [...]}; facts and open_ends are optional. Write a decision, a
correction, a gotcha or a procedure the way a later session should read it:
self-contained, naming the files, commands and values it is about. Secrets are
redacted before anything is written.

--supersedes RECORD_ID (repeatable) marks an episode this statement replaces,
by the record_id that `atrium context` or `atrium search` printed for it. The
old episode stays searchable as history, ranked after current evidence and
marked with what replaced it.

Prints a JSON receipt. `searchable_now` is false when a refresh held the index;
the statement is already kept and is indexed by the next refresh.
"""
