"""Load a SQL statement the tests run, kept as a resource file."""

from pathlib import Path

_QUERIES = Path(__file__).parent / "sql"


def load_test_sql(name: str) -> str:
    """Return the statement stored in ``tests/sql/<name>.sql``."""
    return (_QUERIES / f"{name}.sql").read_text(encoding="utf-8")
