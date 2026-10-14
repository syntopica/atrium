"""The prompt every stored vector is embedded under."""

# The benchmark that produced the fusion weights embedded queries and documents
# through this same prefix, so changing it invalidates the measured weights and
# every stored vector: a change is a full re-embed, never a quiet edit.
DOCUMENT_PREFIX = "task: sentence similarity | query: "
