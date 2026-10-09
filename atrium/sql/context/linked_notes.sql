SELECT record_id, text, conversation_id, source_sha256, authored_at, provider, role
FROM records
WHERE role = 'note' AND provider = ? AND conversation_id = ?
ORDER BY event_index, record_id
LIMIT ?
