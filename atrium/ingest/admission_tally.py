"""Counts of what one ingest run admitted, and what each rule rejected."""

from dataclasses import dataclass, field


@dataclass
class AdmissionTally:
    """What an ingest admitted per role, and rejected per admission rule.

    A row count alone is exactly the number that looked healthy while 162,225
    tool-call, tool-result and thinking records were filed as conversation
    during the memstore recovery. Counting per role and per rejection rule
    turns a wrong admission rule from a post-hoc audit into the first line of
    output.
    """

    admitted: dict[str, int] = field(default_factory=dict)
    rejected: dict[str, int] = field(default_factory=dict)

    def admit(self, role: str) -> None:
        """Count one record admitted under ``role``."""
        self.admitted[role] = self.admitted.get(role, 0) + 1

    def reject(self, rule: str) -> None:
        """Count one event turned away by ``rule``."""
        self.rejected[rule] = self.rejected.get(rule, 0) + 1
