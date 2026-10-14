"""The commands that write a store an erasure cleans."""

# The index, the synthesis registry and the curation directory. A command that
# only reads, reports or publishes status is left out, and so is `erase`, which
# takes the same lock exclusively itself.
WRITER_COMMANDS = (
    "ingest",
    "ingest-notes",
    "embed",
    "prepare-context",
    "synthesize",
    "ingest-synthesis",
    "repair-index",
    "record-session",
    "rekey-synthesis",
    "curate-screen",
    "curate-extract",
    "curate-cluster",
    "curate-neighbours",
    "curate-publishable",
    "curate-propose",
)
