SELECT conversation_id, rows_sha256, canonical_workspace, disposition
FROM conversation_revisions
WHERE provider = ?
