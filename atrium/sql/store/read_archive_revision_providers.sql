-- A loose index scan: one seek on conversation_revisions_provider per distinct
-- provider, instead of reading the whole index for a handful of values.
WITH RECURSIVE providers(provider) AS (
  SELECT MIN(provider) FROM conversation_revisions
  UNION ALL
  SELECT (
    SELECT MIN(provider) FROM conversation_revisions
    WHERE provider > providers.provider
  )
  FROM providers
  WHERE providers.provider IS NOT NULL
)
SELECT provider FROM providers
WHERE provider IS NOT NULL AND provider != 'synthesis'
