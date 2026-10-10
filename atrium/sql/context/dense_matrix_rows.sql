-- Every embedded record with only what ranking needs: no text. Driven from the
-- (role, workspace) index so `workspace`, stored after the text column, comes
-- from the index instead of walking each record's overflow pages.
SELECT r.record_id, r.role, r.workspace, v.vector
FROM records r
JOIN vectors v ON v.record_id = r.record_id
WHERE r.role IN ({placeholders})
ORDER BY r.record_id
