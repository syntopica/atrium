CREATE INDEX IF NOT EXISTS conversation_revisions_provider
ON conversation_revisions (provider, conversation_id)
