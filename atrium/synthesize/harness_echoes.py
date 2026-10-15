"""Lone messages a harness writes that carry nothing a synthesis can use."""

# Measured 2026-10-10 over the registry's 2,468 single-event episodes: these
# echoes alone were 2,213 of them ("Structured output provided successfully"
# 2,126, "[Request interrupted by user]" 87), and each paid a full synthesis
# call to produce a record about the echo. Matched exactly, never by length:
# a short lone message from the operator can still be worth remembering.
HARNESS_ECHOES = frozenset(
    {
        "Structured output provided successfully",
        "[Request interrupted by user]",
    }
)
