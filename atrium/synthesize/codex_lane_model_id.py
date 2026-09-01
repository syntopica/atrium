"""The population name a codex-lane run writes into every job key."""

from atrium.synthesize.codex_lane_call import CODEX_MODEL_ID


def codex_lane_model_id(model: str | None, effort: str | None) -> str:
    """Name the population for ``model`` at ``effort``.

    The model id enters the job key, so this is what keeps populations from
    mixing: the same episode synthesized by a different model at a different
    effort is a different job, never a silent overwrite of the first. An
    unpinned run keeps the historical `codex-cli-default` name, because those
    records were produced by whatever the account default was at the time and
    renaming them now would orphan 10,967 paid-for records.
    """
    if not model and not effort:
        return CODEX_MODEL_ID
    return "-".join(part for part in (model or CODEX_MODEL_ID, effort) if part)
