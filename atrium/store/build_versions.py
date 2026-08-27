"""What produced this index, so machines can tell content from pipeline drift."""

# Bump `schema` when schema.py changes shape (tables, tokenizers, triggers).
# Bump `pipeline` when ingest semantics change (admission rules, identity
# derivation, text normalization). Either bump makes existing indexes refuse to
# open instead of silently disagreeing with an index built by newer code -- the
# index is disposable, so the remedy is always: delete it and re-ingest.
BUILD_VERSIONS = {
    "schema": "2",
    "pipeline": "1",
}
