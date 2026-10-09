SELECT record_id, event_id, conversation_id, source_sha256, provider, role, text,
       authored_at, workspace, title, event_index
FROM records
WHERE conversation_id = ?
ORDER BY record_id
