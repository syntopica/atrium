"""The prompt a retrieval query is embedded under."""

from atrium.embed.document_prefix import DOCUMENT_PREFIX

# Separate from the document prefix so the two can differ, which is what
# EmbeddingGemma's retrieval prompts ask for ("task: search result | query: ").
# It stays equal to the document prefix until the end-to-end evaluation in
# docs/plans/2026-10-15-retrieval-prompt-and-rerank.md says otherwise: the
# 2026-10-14 numbers came from an evaluation that routed by the answer's kind.
QUERY_PREFIX = DOCUMENT_PREFIX
