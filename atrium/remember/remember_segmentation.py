"""The segmentation mark of a record an agent wrote on purpose."""

# Not a cut of any transcript: the record is the agent's own statement, so no
# batch lane will ever synthesize it again and no archive event backs it.
REMEMBER_SEGMENTATION = "remember-v1"
