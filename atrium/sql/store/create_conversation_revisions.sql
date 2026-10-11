-- What each conversation last reconciled to, so an unchanged one is recognised
-- without reading its stored text back. `rows_sha256` hashes the exact rows the
-- ingest derived, so every input of that derivation -- the archive revision,
-- the admission rules, the alias map, a scratchpad whose project directory has
-- since disappeared -- changes it when it changes the rows, and nothing else
-- does. `disposition` keeps an excluded conversation's verdict after its rows
-- are gone, which the synthesis ingest needs: registry records carry no
-- workspace, so once a source's raw rows are deleted nothing else remembers it.
-- Derived like every table here: dropping it costs one full reconcile.
CREATE TABLE IF NOT EXISTS conversation_revisions (
    conversation_id      TEXT PRIMARY KEY,
    provider             TEXT NOT NULL,
    rows_sha256          TEXT NOT NULL,
    canonical_workspace  TEXT,
    disposition          TEXT NOT NULL
        CHECK (disposition IN ('indexed', 'empty', 'excluded_automation'))
)
