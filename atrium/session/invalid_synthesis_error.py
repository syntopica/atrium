"""A synthesis payload the record command refuses, with the reason."""


class InvalidSynthesisError(ValueError):
    """Raised with a one-line reason the model can act on."""
