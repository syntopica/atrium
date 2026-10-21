-- Additive provenance migration. Existing rows keep unknown observing hosts
-- until their canonical conversations are ingested again.
CREATE TABLE IF NOT EXISTS record_hosts (
    record_id TEXT PRIMARY KEY REFERENCES records (record_id) ON DELETE CASCADE,
    hosts_json TEXT NOT NULL
)
