"""A claim that describes a retired thing as current is not proposed for a page."""

from atrium.context.retirement import Retirement
from atrium.curate.claim_retirement import claim_retirement

HOLDED = Retirement(("Holded",), "2026-09-22", "InteliFactu", "brain/business/retired.md")


def test_a_claim_last_seen_before_the_retirement_is_caught() -> None:
    claim = {"text": "Invoices are issued from Holded.", "last_seen": "2026-08-01"}
    assert claim_retirement(claim, [HOLDED]) is HOLDED


def test_a_later_claim_and_an_unrelated_one_stay() -> None:
    later = {"text": "Holded is retired; invoices go through InteliFactu.", "last_seen": "2026-10-01"}
    unrelated = {"text": "Invoices are issued from InteliFactu.", "last_seen": "2026-08-01"}
    assert claim_retirement(later, [HOLDED]) is None
    assert claim_retirement(unrelated, [HOLDED]) is None
