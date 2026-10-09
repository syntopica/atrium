INSERT OR REPLACE INTO vectors (record_id, vector)
SELECT record_id, ? FROM records WHERE record_id = ? AND source_sha256 = ?
