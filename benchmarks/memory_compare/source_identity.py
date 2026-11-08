"""Map raw and synthesized records onto the labeled source identity."""


def source_identity(value: str) -> str:
    """Strip only Atrium's synthesis namespace, keeping note paths intact."""
    return value.removeprefix("synthesis/")
