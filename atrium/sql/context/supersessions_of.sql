-- The supersessions of one candidate set. The ids arrive as one JSON array, so
-- the statement stays static however many candidates a context answer holds.
SELECT record_id, superseded_by, at FROM supersessions
WHERE record_id IN (SELECT value FROM json_each(?))
