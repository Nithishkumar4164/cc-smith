from hypothesis import given
from hypothesis import strategies as st

from cc_smith.rewards.engine import Purchase, reward

R = 100  # paise per rupee


def test_regalia_base_rate_and_block_rounding(cards):
    rg = cards["hdfc_regalia_gold"]
    r = reward(rg, Purchase(1_000 * R, "dining"))
    assert r.lines[0].units == 25  # 5 RP per ₹200
    assert r.value_paise == 25 * 50
    # ₹399 is one ₹200 block.
    assert reward(rg, Purchase(399 * R, "dining")).lines[0].units == 5


def test_regalia_below_minimum_and_excluded(cards):
    rg = cards["hdfc_regalia_gold"]
    assert "below_min_txn" in reward(rg, Purchase(149 * R, "dining")).reason_codes
    assert reward(rg, Purchase(5_000 * R, "fuel")).value_paise == 0
    assert "excluded:fuel" in reward(rg, Purchase(5_000 * R, "fuel")).reason_codes


def test_regalia_5x_bonus_stacks_and_caps_only_the_bonus(cards):
    rg = cards["hdfc_regalia_gold"]
    r = reward(rg, Purchase(2_000 * R, "online", "myntra", "online"))
    assert {l.rule_id: l.units for l in r.lines} == {"base": 50, "x5_bonus": 200}
    r = reward(rg, Purchase(2_000 * R, "online", "myntra", "online"), {"x5": 4_900})
    assert {l.rule_id: l.units for l in r.lines} == {"base": 50, "x5_bonus": 100}


def test_regalia_grocery_monthly_cap(cards):
    rg = cards["hdfc_regalia_gold"]
    r = reward(rg, Purchase(100_000 * R, "grocery"))
    assert r.lines[0].units == 2_000
    assert "capped:grocery" in r.reason_codes


def test_millennia_5pct_merchants_and_monthly_cap(cards):
    m = cards["hdfc_millennia"]
    assert reward(m, Purchase(2_000 * R, "online", "amazon", "online")).value_paise == 100 * R
    capped = reward(m, Purchase(2_000 * R, "online", "amazon", "online"), {"online_10": 950 * R})
    assert capped.value_paise == 50 * R
    assert reward(m, Purchase(2_000 * R, "dining")).value_paise == 20 * R


def test_swiggy_blck_min_txn_falls_back_to_base(cards):
    b = cards["hdfc_swiggy_blck"]
    assert reward(b, Purchase(500 * R, "dining", "swiggy", "online")).value_paise == 50 * R
    small = reward(b, Purchase(200 * R, "dining", "swiggy", "online"))
    assert [l.rule_id for l in small.lines] == ["other"]
    assert small.value_paise == 2 * R


def test_swiggy_online_rule_needs_online_channel(cards):
    b = cards["hdfc_swiggy_blck"]
    assert reward(b, Purchase(1_000 * R, "online", "amazon", "online")).value_paise == 50 * R
    assert reward(b, Purchase(1_000 * R, "online", "croma", "offline")).value_paise == 10 * R


def test_amazon_icici_prime_flag(cards):
    a = cards["icici_amazon_pay"]
    p = Purchase(1_000 * R, "online", "amazon", "online")
    assert reward(a, p).value_paise == 30 * R
    assert reward(a, Purchase(1_000 * R, "online", "amazon", "online", frozenset({"amazon_prime"}))).value_paise == 50 * R


def test_amazon_icici_utilities_excluded_except_on_amazon(cards):
    a = cards["icici_amazon_pay"]
    assert reward(a, Purchase(1_000 * R, "utilities", "bescom")).value_paise == 0
    assert reward(a, Purchase(1_000 * R, "utilities", "amazon", "online")).value_paise == 30 * R


def test_atlas_travel_spend_cap_spills_to_base(cards):
    at = cards["axis_atlas"]
    r = reward(at, Purchase(50_000 * R, "travel", "indigo", "online"), {"travel_spend": 190_000 * R})
    assert {l.rule_id: l.units for l in r.lines} == {"travel": 500, "base": 800}


def test_atlas_ota_earns_base_only(cards):
    at = cards["axis_atlas"]
    r = reward(at, Purchase(10_000 * R, "travel", "makemytrip", "online"))
    assert [l.rule_id for l in r.lines] == ["base"]
    assert r.value_paise == 200 * R


def test_upi_needs_rupay(cards):
    assert "no_upi" in reward(cards["hdfc_millennia"], Purchase(500 * R, "dining", channel="upi")).reason_codes


@given(st.integers(min_value=0, max_value=10_000_000 * R), st.sampled_from(["dining", "grocery", "online", "travel", "fuel", "other"]))
def test_reward_never_negative_and_cap_use_bounded(cards, amount, category):
    for card in cards.values():
        r = reward(card, Purchase(amount, category))
        assert r.value_paise >= 0
        for cid, used in r.cap_use.items():
            if cid.startswith("earned:"):  # base-rule counter for base-multiple caps, not a cap
                continue
            cap = card.cap(cid)
            if cap.unit != "base_multiple":
                assert used <= cap.amount


def test_airtel_bill_cap_is_twice_the_months_base_cashback(cards):
    """Axis: 25% on Airtel bills 'capped at twice the base cashback earned during the
    statement month'; the base is 1% on other spends."""
    at = cards["axis_airtel"]
    bill = Purchase(999 * R, "utilities", "airtel", "online")
    assert reward(at, bill).value_paise == 0  # nothing earned at 1% yet, so the cap is ₹0
    other = reward(at, Purchase(2_000 * R, "other"))
    assert other.value_paise == 20 * R and other.cap_use == {"earned:other": 20 * R}
    capped = reward(at, bill, other.cap_use)
    assert capped.value_paise == 40 * R  # 2 x ₹20, not 25% of ₹999
    assert "capped:airtel" in capped.reason_codes
    plenty = reward(at, bill, {"earned:other": 200 * R})
    assert plenty.value_paise == 24975  # 25% of ₹999 fits under 2 x ₹200


def test_airtel_utilities_cap_is_once_the_base(cards):
    at = cards["axis_airtel"]
    r = reward(at, Purchase(2_000 * R, "utilities", "airtel_thanks_bills", "online"), {"earned:other": 50 * R})
    assert r.value_paise == 50 * R
