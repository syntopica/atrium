-- The segment-archive generation the last full ingest read, from the
-- materialized export's manifest. One row at most; none after a v1 archive,
-- whose manifest names no generation. `doctor --segment-inventory` compares it
-- with what scribe holds now.
CREATE TABLE IF NOT EXISTS archive_generation (
    singleton      INTEGER PRIMARY KEY CHECK (singleton = 1),
    generation_id  TEXT NOT NULL
)
