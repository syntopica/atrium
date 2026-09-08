"""The console scripts the installed distributions declare, by name."""

from importlib.metadata import entry_points


def installed_console_scripts() -> dict[str, str]:
    """Map every installed console script name to its ``module:attribute`` target."""
    return {point.name: point.value for point in entry_points(group="console_scripts")}
