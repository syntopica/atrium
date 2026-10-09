"""Load a SQL statement kept as a resource file."""

from functools import cache
from importlib.resources import files


@cache
def load_sql(name: str) -> str:
    """Return the statement stored in ``atrium/sql/<name>.sql``.

    Read once per process: the hot paths run the same handful of statements on
    every query, and the files cannot change under a running engine.
    """
    return files("atrium.sql").joinpath(f"{name}.sql").read_text(encoding="utf-8")
