"""The index schema. Every table here is derived and safe to drop."""

# Two lexical lanes, deliberately. `words` tokenizes on word boundaries and is the
# lane that answers "find the record that says WAL"; `substrings` is trigram and
# answers "find records containing this fragment". The system this replaces had
# only the trigram lane, so searching `WAL` returned nine `wall...` false
# positives and ranked the first exact hit seventh. Merging them back into one
# index recreates that.
SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    record_id        TEXT PRIMARY KEY,
    conversation_id  TEXT NOT NULL,
    source_sha256    TEXT NOT NULL,
    provider         TEXT NOT NULL,
    role             TEXT NOT NULL,
    text             TEXT NOT NULL,
    authored_at      TEXT,
    workspace        TEXT,
    title            TEXT,
    event_index      INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS records_conversation ON records (conversation_id);
CREATE INDEX IF NOT EXISTS records_authored_at ON records (authored_at);
CREATE INDEX IF NOT EXISTS records_provider ON records (provider);

CREATE VIRTUAL TABLE IF NOT EXISTS words USING fts5 (
    text,
    content='records',
    content_rowid='rowid',
    tokenize="unicode61 remove_diacritics 2"
);

CREATE VIRTUAL TABLE IF NOT EXISTS substrings USING fts5 (
    text,
    content='records',
    content_rowid='rowid',
    tokenize="trigram"
);

-- What produced the index, so a machine can tell "different content" from
-- "different pipeline" instead of silently disagreeing with its sibling.
CREATE TABLE IF NOT EXISTS build_metadata (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
"""
