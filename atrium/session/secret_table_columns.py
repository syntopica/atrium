"""Locate credential columns and their explicitly named value columns."""

from atrium.session.is_secret_table_label import is_secret_table_label
from atrium.session.is_table_value_label import is_table_value_label


def secret_table_columns(cells: list[str]) -> set[int]:
    """Cover both column-shaped secrets and adjacent Secret/Value layouts."""
    return {
        target
        for position, cell in enumerate(cells)
        if is_secret_table_label(cell)
        for target in (
            (position, position + 1)
            if position + 1 < len(cells) and is_table_value_label(cells[position + 1])
            else (position,)
        )
    }
