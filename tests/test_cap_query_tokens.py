"""A query too long for the pair length is cut to its head, a short one is kept."""

from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

from atrium.rerank.cap_query_tokens import cap_query_tokens


def _tokenizer():
    tokenizer = Tokenizer(WordLevel({"[UNK]": 0, "a": 1, "b": 2}, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    return tokenizer


def test_a_query_within_the_budget_is_unchanged():
    assert cap_query_tokens(_tokenizer(), "a b a", 3) == "a b a"


def test_a_longer_query_keeps_its_head_verbatim():
    assert cap_query_tokens(_tokenizer(), "a  b a b", 2) == "a  b"
