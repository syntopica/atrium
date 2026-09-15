"""The rebuildable covering indexes needed for bounded context reads."""


def context_index_specs() -> dict[str, tuple[str, ...]]:
    """Keep metadata-only scope scans out of the large text-bearing table."""
    return {
        "records_context_role_workspace": ("role", "workspace"),
        "records_context_workspace_role": ("workspace", "role"),
    }
