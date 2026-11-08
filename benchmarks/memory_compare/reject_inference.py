"""Make an accidental inference call fail instead of spending a provider key."""


class RejectInference:
    """The retrieval-only experiment must never extract or generate memories."""

    def generate_response(self, *_args, **_kwargs):
        """Reject every call, regardless of provider-specific arguments."""
        raise RuntimeError("LLM inference is outside the retrieval-only protocol")
