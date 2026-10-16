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
)
