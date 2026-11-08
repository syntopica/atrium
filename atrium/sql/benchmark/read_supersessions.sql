-- Preserve correction metadata in an isolated benchmark snapshot.
SELECT record_id, superseded_by, at FROM supersessions
