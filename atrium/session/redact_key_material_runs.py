"""Replace long runs of key characters, keeping the text around them."""

import re

from atrium.session.key_material_run_min_length import KEY_MATERIAL_RUN_MIN_LENGTH

_RUN = re.compile(rf"(?:\\+[rn]|[A-Za-z0-9+/=]){{{KEY_MATERIAL_RUN_MIN_LENGTH},}}")


def redact_key_material_runs(text: str) -> str:
    r"""Replace every run of base64 characters and ``\n`` escapes of the minimum length.

    A key truncated to ``...`` or split across quoted lines goes, the prose
    between stays. Same rule as scribe's `redactKeyMaterialRuns`.
    """
    return _RUN.sub("[REDACTED:private-key]", text)
