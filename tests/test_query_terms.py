"""The terms every word-lane expression is built from stay bounded."""

from atrium.retrieve.query_terms import query_terms


def test_a_repeated_word_is_one_term() -> None:
    assert query_terms("hook stop hook hook stop") == ['"hook"', '"stop"']


def test_a_whole_prompt_is_cut_to_its_first_terms() -> None:
    prompt = " ".join(f"word{number}" for number in range(5000))

    terms = query_terms(prompt)

    assert terms[:2] == ['"word0"', '"word1"']
    assert len(terms) == 128


def test_a_sentence_keeps_every_term_in_order() -> None:
    assert query_terms("upgrade to 3.7.0 of memstore_delete") == [
        '"upgrade"',
        '"to"',
        '"3 7 0"',
        '"of"',
        '"memstore delete"',
    ]
