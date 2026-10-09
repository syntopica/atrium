SELECT r.record_id FROM substrings JOIN records r ON r.rowid = substrings.rowid
WHERE substrings MATCH 'wal'
