"""Where a command name resolves on a PATH, the way a POSIX shell resolves it."""

from atrium.doctor.classify_candidate import RUNNABLE, classify_candidate
from atrium.doctor.command_lookup import CommandLookup
from atrium.doctor.path_candidates import path_candidates


def locate_command(name: str, search_path: str) -> CommandLookup:
    """Return the first runnable ``name`` on ``search_path``, and what preceded it.

    A shell does not stop at the first entry bearing the name: it skips a
    directory, a dangling link and a file without the exec bit, and keeps
    walking PATH. Stopping early reports a healthy machine as broken -- a
    directory `atrium` in an early entry with the real wrapper in a later one
    runs fine under `/bin/sh` -- so the scan continues and the unusable
    candidates are carried back as context rather than as the verdict.

    ``search_path`` is required. Defaulting it hid the question of *whose*
    PATH is being asked about, which is the whole substance of this check.
    """
    shadows: list[str] = []
    for candidate in path_candidates(name, search_path):
        reason = classify_candidate(candidate)
        if reason == RUNNABLE:
            return CommandLookup(command=candidate, shadows=tuple(shadows))
        shadows.append(f"{candidate} {reason}")
    return CommandLookup(command=None, shadows=tuple(shadows))
