INSERT INTO conversation_revisions
    (conversation_id, provider, rows_sha256, canonical_workspace, disposition)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT (conversation_id) DO UPDATE SET
    provider = excluded.provider,
    rows_sha256 = excluded.rows_sha256,
    canonical_workspace = excluded.canonical_workspace,
    disposition = excluded.disposition
