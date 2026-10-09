SELECT r.record_id, r.text, r.conversation_id, r.source_sha256, r.authored_at, r.provider, r.role,
       v.vector
FROM records r
JOIN vectors v ON v.record_id = r.record_id
WHERE 1 = 1{scope}
ORDER BY r.record_id
