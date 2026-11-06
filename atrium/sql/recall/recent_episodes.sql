-- Shaped for the (role, workspace) index, not for brevity. Filtering on provider
-- alone made SQLite walk all 79k episodes through `records_provider` and fetch
-- each row from a 22 GB table to read its workspace: 0.1s warm, but over 20s on
-- a cold page cache, which timed out session-start recall forty minutes after a
-- reboot on 2026-10-09. `+provider` keeps the planner off that index, and the
-- range `[prefix, prefix || '0')` -- '0' is the byte after '/' -- lets it seek to
-- the project; the exact test below then drops siblings such as `atrium-x`.
-- The newest few are picked inside `records_recall_role_workspace_time` alone:
-- sorting the matching rows themselves read all 74,073 under `[HOME]/p` to keep
-- twelve, 21.9 s against the hook's 20 s (2026-11-06); this takes 0.06 s.
-- shortcut: provider is tested after the limit, which is exact while every
-- synthesis-role row is a synthesis record (76,177 of 76,177); move provider
-- into the index if another provider ever writes that role.
SELECT record_id, text, conversation_id, source_sha256, authored_at, provider, role
FROM records
WHERE rowid IN (
    SELECT rowid
    FROM records
    WHERE role = 'synthesis'
      AND workspace >= ? AND workspace < ? || '0'
      AND (workspace = ? OR substr(workspace, 1, length(?) + 1) = ? || '/')
    ORDER BY authored_at DESC, conversation_id, record_id
    LIMIT ?
)
  AND +provider = 'synthesis'
ORDER BY authored_at DESC, conversation_id, record_id
