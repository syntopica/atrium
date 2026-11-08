"""Prevent benchmark inputs from leaving the local process."""


def block_network(event: str, _arguments: tuple) -> None:
    """Reject socket connections and datagrams, including telemetry."""
    if event in {"socket.connect", "socket.sendto", "socket.getaddrinfo"}:
        raise PermissionError("network is disabled for this private benchmark")
