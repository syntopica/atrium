"""Every statement the engine loads exists, and every statement file is loaded."""

import ast
from pathlib import Path

from atrium.sql.load_sql import load_sql

_ROOT = Path(__file__).resolve().parents[1]
_PACKAGE = _ROOT / "atrium"
_SQL = _PACKAGE / "sql"


def _loaded_names() -> set[str]:
    names = set()
    for source in _PACKAGE.rglob("*.py"):
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "load_sql"
            ):
                argument = node.args[0]
                assert isinstance(argument, ast.Constant), f"{source}: computed SQL name"
                names.add(argument.value)
    return names


def test_every_loaded_statement_exists() -> None:
    for name in _loaded_names():
        assert load_sql(name).strip(), name


def test_no_statement_file_is_orphaned() -> None:
    files = {path.relative_to(_SQL).with_suffix("").as_posix() for path in _SQL.rglob("*.sql")}
    assert files == _loaded_names()
