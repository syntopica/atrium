"""The cutter name and recipe version stamped on every session record."""

# Session episodes are cut by the session itself at a transcript boundary,
# never by the TextTiling cutter, and must not pretend to be its episodes.
SESSION_SEGMENTATION = "session-self-v1"

# Names the instruction text the Stop refusal hands the model. Bump it when
# that text changes; it is part of the session job key, in place of the batch
# prompt hash, so a batch prompt edit does not re-key every session record.
SESSION_RECIPE_VERSION = "session-recipe-1"
