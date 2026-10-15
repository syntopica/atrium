-- Which of the named records exist as synthesized episodes. Only those can be
-- superseded: a curated note has one human writer, and raw history is evidence
-- of what was said, not a claim a later statement corrects.
SELECT record_id FROM records
WHERE role IN ('synthesis') AND record_id IN (SELECT value FROM json_each(?))
