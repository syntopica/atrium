-- One counter that moves whenever the set of embedded vectors changes. A
-- resident reader keeps a copy of every vector in memory; it compares this
-- number instead of rescanning a multi-gigabyte index to learn whether its
-- copy is still current. Derived like everything else here: dropping it only
-- costs the next reader one rebuild.
CREATE TABLE IF NOT EXISTS dense_generation (
    k  INTEGER PRIMARY KEY CHECK (k = 1),
    n  INTEGER NOT NULL
)
