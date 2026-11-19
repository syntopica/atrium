"""A long query is matched on its rarest terms, not its first ones."""

from atrium.retrieve.rarest_terms import rarest_terms


def test_the_least_frequent_terms_are_kept_in_query_order() -> None:
    frequencies = {'"the"': 900, '"vault"': 3, '"meeting"': 400, '"rotation"': 7}

    assert rarest_terms(frequencies, 2) == ['"vault"', '"rotation"']


def test_a_term_no_record_holds_does_not_take_a_place() -> None:
    frequencies = {'"zzyzx"': 0, '"vault"': 3, '"meeting"': 400}

    assert rarest_terms(frequencies, 2) == ['"vault"', '"meeting"']


def test_a_short_query_keeps_every_indexed_term() -> None:
    frequencies = {'"stop"': 50, '"hook"': 20}

    assert rarest_terms(frequencies, 32) == ['"stop"', '"hook"']
