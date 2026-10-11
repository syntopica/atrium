-- The excluded set is read on every status and doctor run; this keeps that read
-- off a scan of the whole table.
CREATE INDEX IF NOT EXISTS conversation_revisions_disposition
ON conversation_revisions (disposition, conversation_id)
