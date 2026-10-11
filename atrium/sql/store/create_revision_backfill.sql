-- Set by the first full raw ingest that wrote a revision for every archived
-- conversation. Until then the revision table may hold only some conversations
-- (a partial slice, or the verdicts a purge wrote), and a reader that trusted it
-- for workspaces would strip every other synthesis record of its project.
CREATE TABLE IF NOT EXISTS revision_backfill (
    k   INTEGER PRIMARY KEY CHECK (k = 1),
    at  TEXT NOT NULL
)
