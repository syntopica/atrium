"""Tools whose result is a document the episode is about, not a log."""

# An A/B on 2026-11-06 lost 6 of 11 facts when a `Read` of two voice-note
# transcripts (46k and 42k characters) was cut to its head and tail: what a
# session reads is often its subject. Command output, searches and skill
# bodies are not, and keep the tool cap.
DOCUMENT_TOOLS = frozenset({"Read", "WebFetch"})
