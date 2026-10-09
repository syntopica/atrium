INSERT INTO records (
    record_id, event_id, conversation_id, source_sha256, provider, role, text,
    authored_at, workspace, title, event_index
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
