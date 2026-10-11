INSERT INTO revision_backfill (k, at) VALUES (1, ?)
ON CONFLICT (k) DO UPDATE SET at = excluded.at
