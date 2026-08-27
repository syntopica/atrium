"""What produced this index, so machines can tell content from pipeline drift."""

# Bump `schema` when schema.py changes shape (tables, tokenizers, triggers).
# Bump `pipeline` when ingest semantics change (admission rules, identity
# derivation, text normalization). Either bump makes existing indexes refuse to
# open instead of silently disagreeing with an index built by newer code -- the
# index is disposable, so the remedy is always: delete it and re-ingest.
BUILD_VERSIONS = {
    "schema": "2",
    # pipeline 2: notes ingest gained node_modules/--exclude filtering and
    # oversized-paragraph splitting, and ingest gained the absent-conversation
    # sweep -- all of which change what an index holds for the same input.
    # (Bumping late for the first of those is the mistake the reviewer caught:
    # two commits claimed pipeline 1 with different admission rules. Any change
    # to admission, chunking, identity or reconciliation bumps this in the
    # same commit.)
    "pipeline": "2",
}
