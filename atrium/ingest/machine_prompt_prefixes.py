"""Openings of user-role messages that a harness or an app wrote, not a person."""

# Each entry is a template's whole opening sentence, never a phrase a person
# might type: "Review this change for security vulnerabilities." alone is.
# Measured 2026-10-16 over the 102,613 admitted user records: these openings
# carried 69.5% of the role's text (the security-review template alone 39%, the
# Vexa classifier 11.5%), against 7.9% for human-sized prompts. `<system-reminder>`
# is left out: 194 of its 236 messages carry text after the tag, which may be the
# person's own prompt. A compaction summary ("This session is being continued")
# is left out too: it is machine-written but restates real work.
MACHINE_PROMPT_PREFIXES = (
    "<recommended_plugins> Here is a list of plugins that are available but not installed.",
    "# AGENTS.md instructions",
    "Base directory for this skill:",
    "[SYSTEM NOTIFICATION - NOT USER INPUT] This is an automated background-task event",
    # The "user request" variant is left out: it relays the person's own words.
    "[Workflow harness \u2014 computed task] The task text below was computed at runtime",
    "# How the owner answers Mined from the owner's own replies",
    "Review this change for security vulnerabilities. Changed files (you may Read these",
    "You previously flagged these candidate vulnerabilities: [",
    "You are an email classifier for Vexa, a personal email intelligence tool.",
    "You are an expert invoice schema formatter. SECURITY PREAMBLE",
    "<role> You are an expert invoice extraction and reconciliation engine.",
)
