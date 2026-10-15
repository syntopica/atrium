SELECT r.text, r.workspace, v.record_id IS NOT NULL FROM records r
LEFT JOIN vectors v USING (record_id) WHERE r.record_id = ?
