"""The size bound on one note chunk."""

# Chunks bounded so one section cannot monopolise a vector: the embedder
# truncates at 2,048 tokens, and a chunk far past that embeds only its head.
MAX_CHUNK_CHARS = 2000
