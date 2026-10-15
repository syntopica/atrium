INSERT INTO archive_generation (singleton, generation_id) VALUES (1, :generation_id)
ON CONFLICT (singleton) DO UPDATE SET generation_id = excluded.generation_id
