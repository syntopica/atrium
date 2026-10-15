"""Openings of user-role messages that a harness or an app wrote, not a person."""

# Measured 2026-10-16 over the 102,613 admitted user records: these openings
# carried 69.5% of the role's text (the security-review template alone 39%, the
# Vexa classifier 11.5%), against 7.9% for human-sized prompts. `<system-reminder>`
# is left out: 194 of its 236 messages carry text after the tag, which may be the
# person's own prompt. A compaction summary ("This session is being continued")
# is left out too: it is machine-written but restates real work.
MACHINE_PROMPT_PREFIXES = (
    "<recommended_plugins>",
    "# AGENTS.md instructions",
    "Base directory for this skill:",
    "[SYSTEM NOTIFICATION - NOT USER INPUT]",
    "[Workflow harness",
    "# How the owner answers",
    "Review this change for security vulnerabilities.",
    "You previously flagged these candidate vulnerabilities:",
    "You are an email classifier for Vexa",
    "You are an expert invoice schema formatter.",
    "<role> You are an expert invoice extraction",
)
