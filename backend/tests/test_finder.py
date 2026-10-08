import pytest

from cc_smith.rewards.finder import GST_BP, find_portfolios, refine, simulate
from cc_smith.users.service import spend_lines

R = 100

SPENDS = {"amazon": 6_000 * R, "swiggy": 5_000 * R, "grocery": 10_000 * R, "utilities": 4_000 * R, "other": 10_000 * R}


def _fee(card) -> int:
    return card.fees.annual_paise * (10_000 + GST_BP) // 10_000


def test_refined_routing_keeps_the_held_cards_milestone_value(cards):
    """Chunk-by-chunk routing can move spend off Millennia and drop it below its ₹1 lakh a
    quarter voucher milestone; refine() must never let a new card cost more than its fee."""
    mil, live = cards["hdfc_millennia"], cards["hsbc_live_plus"]
    lines = spend_lines(SPENDS)
    held = simulate([mil], lines)
    assert held.cards[mil.id].milestone_paise == 4 * 1_000 * R
    refined, _ = refine([mil, live], lines, {mil.id})
    assert refined.net_paise >= held.net_paise - _fee(live)


@pytest.mark.parametrize("new_id", ["hsbc_live_plus", "hdfc_swiggy_blck", "axis_atlas", "hdfc_regalia_gold", "sbi_cashback"])
def test_adding_a_card_never_costs_more_than_its_fee(cards, new_id):
    mil, new = cards["hdfc_millennia"], cards[new_id]
    lines = spend_lines(SPENDS)
    base, _ = refine([mil], lines)
    with_new, _ = refine([mil, new], lines, {mil.id})
    assert with_new.net_paise - base.net_paise >= -_fee(new)


def test_finder_portfolios_are_distinct_and_positive(cards):
    lines = spend_lines(SPENDS)
    base, portfolios = find_portfolios([cards["hdfc_millennia"]], list(cards.values()), lines)
    assert portfolios and all(p.gain_paise > 0 for p in portfolios)
    sets = [frozenset(p.new_cards) for p in portfolios]
    assert len(set(sets)) == len(sets)
    for p in portfolios:
        assert p.simulation.net_paise - base.net_paise == p.gain_paise
