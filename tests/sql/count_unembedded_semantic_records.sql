SELECT count(*) FROM records WHERE role IN ({placeholders})
AND record_id NOT IN (SELECT record_id FROM vectors)
