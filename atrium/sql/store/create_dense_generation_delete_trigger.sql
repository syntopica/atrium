-- Fires for the ON DELETE CASCADE from records as well, which is how a
-- reconciled conversation removes its vectors.
CREATE TRIGGER IF NOT EXISTS vectors_generation_ad AFTER DELETE ON vectors BEGIN
    UPDATE dense_generation SET n = n + 1 WHERE k = 1;
END
