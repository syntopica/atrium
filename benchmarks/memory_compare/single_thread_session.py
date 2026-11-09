"""An onnxruntime session factory that pins the caller's options to one thread."""

from collections.abc import Callable
from typing import Any


def single_thread_session(session_class: Any) -> Callable[..., Any]:
    """Wrap ``session_class`` so every session runs on one intra- and inter-op thread.

    The engine passes its own options positionally (the CPU arena off), so the
    wrapper edits those options instead of replacing them, and creates a set
    only when the caller passed none.
    """
    import onnxruntime

    def create(path: Any, sess_options: Any = None, *args: Any, **kwargs: Any) -> Any:
        options = sess_options if sess_options is not None else onnxruntime.SessionOptions()
        options.intra_op_num_threads = options.inter_op_num_threads = 1
        return session_class(path, options, *args, **kwargs)

    return create
