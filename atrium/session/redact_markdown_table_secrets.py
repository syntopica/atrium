"""Redact credential value cells in key/value and column-header tables."""

import re

from atrium.session.is_secret_table_label import is_secret_table_label
from atrium.session.markdown_table_cells import markdown_table_cells


def redact_markdown_table_secrets(text: str) -> str:
    """Remove whole value cells before any note chunking or output truncation."""
    lines = text.split("\n")
    output = []
    columns: set[int] = set()
    for index, line in enumerate(lines):
        cells = markdown_table_cells(line)
        if len(cells) == 1:
            columns = set()
            output.append(line)
            continue
        separator = all(
            not cell.strip() or re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells
        )
        following = markdown_table_cells(lines[index + 1]) if index + 1 < len(lines) else []
        header = len(following) > 1 and all(
            not cell.strip() or re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in following
        )
        if header:
            columns = {
                position for position, cell in enumerate(cells) if is_secret_table_label(cell)
            }
        elif not separator:
            targets = columns | {
                position + 1
                for position, cell in enumerate(cells[:-1])
                if is_secret_table_label(cell)
            }
            for position in targets:
                if position < len(cells) and cells[position].strip():
                    cells[position] = " [REDACTED:secret] "
        output.append("|".join(cells))
    return "\n".join(output)
