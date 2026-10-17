"""Openings of prompts that are a whole machine job, not one turn of a person's session."""

# The conversation such a prompt opens is the job itself (a security review, a
# mail classification, an invoice extraction): no person speaks in it. Kept apart
# from the harness openings, which sit inside sessions a person drives.
MACHINE_JOB_PREFIXES = (
    "# How the owner answers Mined from the owner's own replies",
    "Review this change for security vulnerabilities. Changed files (you may Read these",
    "You previously flagged these candidate vulnerabilities: [",
    "You are an email classifier for Vexa, a personal email intelligence tool.",
    "You are an expert invoice schema formatter. SECURITY PREAMBLE",
    "<role> You are an expert invoice extraction and reconciliation engine.",
    # Atrium's own stages: run through Codex or the local lane, they land in the
    # archive as conversations of their own (3 of 10 Flash records, 2026-10-17).
    "You are the synthesis stage of a personal memory system.",
    "You structure one already-extracted statement into fields.",
    "You decide what a statement is, not whether it is true.",
    "You place one fact from an engineering session into a personal knowledge wiki.",
    "You compare two statements taken from one operator's engineering sessions and say how they relate.",
)
