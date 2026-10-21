"""Split table cells while preserving escaped pipes in a value."""


def markdown_table_cells(line: str) -> list[str]:
    """Return cells including empty boundary cells and original whitespace."""
    cells = []
    start = 0
    backslashes = 0
    for position, character in enumerate(line):
        if character == "|" and backslashes % 2 == 0:
            cells.append(line[start:position])
            start = position + 1
        backslashes = backslashes + 1 if character == "\\" else 0
    cells.append(line[start:])
    return cells
