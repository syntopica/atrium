"""Tell a PEM private key marker line."""


def is_private_key_marker_line(line: str, edge: str) -> bool:
    """Whether the line starts with a ``-----BEGIN`` or ``-----END`` private key marker."""
    return line.startswith(f"-----{edge} ") and "PRIVATE KEY-----" in line
