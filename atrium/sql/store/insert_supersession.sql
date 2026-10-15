-- The later statement wins, and on the same instant the larger record id, so
-- a retried older `remember` cannot undo a newer one and `remember` agrees with
-- what the next `ingest-synthesis` rebuilds.
INSERT INTO supersessions (record_id, superseded_by, at) VALUES (?, ?, ?)
ON CONFLICT (record_id) DO UPDATE SET superseded_by = excluded.superseded_by, at = excluded.at
WHERE (coalesce(excluded.at, ''), excluded.superseded_by)
    > (coalesce(supersessions.at, ''), supersessions.superseded_by)
