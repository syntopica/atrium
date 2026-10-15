-- Which records a later, explicit statement replaced. Derived from the
-- synthesis registry on every `ingest-synthesis`, and written at once by
-- `remember`; dropping it costs only the next ingest. A superseded record is
-- not deleted: it stays searchable as what was true before, ranked after
-- everything current and marked with what replaced it.
CREATE TABLE IF NOT EXISTS supersessions (
    record_id      TEXT PRIMARY KEY,
    superseded_by  TEXT NOT NULL,
    at             TEXT
)
