"""What the archive holds, split by whether the index could hold it too."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ArchiveAdmissions:
    """Archived conversation ids, and the subset that admits any record.

    A conversation made entirely of tool calls, system events and bare
    acknowledgements is archived and produces no index row -- correctly, by the
    admission rule. Counting it as missing coverage makes the doctor warn on
    every run about a permanent, expected class, and an operator warned every
    run stops reading warnings.
    """

    all_ids: set[str]
    admitting_ids: set[str]
