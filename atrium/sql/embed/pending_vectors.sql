-- The semantic-layer records that still need a vector. The roles arrive as one
-- JSON array, so the statement stays static however many roles earn a vector.
-- Ordered by text length so each sub-batch pads to a similar length: the
-- ONNX graph's attention cost grows with the square of the padded length,
-- and one long chunk in a batch of short ones prices the whole batch at
-- the long one's padding.
SELECT record_id, source_sha256, text FROM records
WHERE role IN (SELECT value FROM json_each(?))
  AND record_id NOT IN (SELECT record_id FROM vectors)
ORDER BY length(text), record_id
