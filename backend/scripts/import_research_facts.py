"""Turn the hand-researched official quotes in docs/research/*card-facts*.json into
extraction fixtures in the card schema. Quotes and URLs are copied, never edited;
the mapping below only decides which rule, cap or exclusion each quote supports.

Usage: uv run python scripts/import_research_facts.py
"""

import json
import sys
from pathlib import Path

from cc_smith.knowledge.schema import CardProfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parents[1] / "fixtures" / "extractions"
RUPEE = 100


def load_cards() -> dict[str, dict]:
    cards = {}
    for name in ("verified-card-facts.json", "seed-card-facts-batch2.json"):
        path = ROOT / "docs" / "research" / name
        if path.exists():
            for c in json.loads(path.read_text())["cards"]:
                cards[c["id"]] = c
    return cards


# Some research quotes carry commentary after the verbatim text; keep only the verbatim part.
VERBATIM_PARTS = {
    "hdfc_millennia": lambda q: q.split(" (Also:")[0],
    "hdfc_swiggy_blck": lambda q: q.split(" (cashback")[0],
    "hdfc_swiggy_ornge": lambda q: q.split(" (cashback")[0],
    "icici_amazon_pay": lambda q: q.split("T&C: '")[1].split("'")[0],
    "hdfc_infinia_metal": lambda q: q.split("Varies by redemption: '")[1].rsplit("'", 1)[0],
}

AXIS_FK_PAGE = "https://www.axis.bank.in/cards/credit-card/flipkart-axisbank-credit-card"
# Research files attribute these quotes to the wrong document or join two documents.
POINT_VALUE_SOURCES = {
    "hdfc_regalia_gold": lambda c: [{"url": "https://www.hdfc.bank.in/credit-cards/regalia-gold-credit-card", "quote": c["point_value_quote"]}],
    "axis_flipkart": lambda c: [
        {"url": c["earn"][-1]["url"], "quote": c["point_value_quote"].split(" / ")[0]},
        {"url": AXIS_FK_PAGE, "quote": c["point_value_quote"].split(" / ")[1]},
    ],
}


def verbatim(card_id: str, quote: str) -> str:
    return VERBATIM_PARTS.get(card_id, lambda q: q)(quote)


class Src:
    def __init__(self, card: dict):
        self.c = card

    def earn(self, i: int) -> dict:
        e = self.c["earn"][i]
        return {"url": e["url"], "quote": e["quote"]}

    def earn_cap(self, i: int) -> dict:
        e = self.c["earn"][i]
        return {"url": e.get("cap_url") or e["url"], "quote": e["cap_quote"]}

    def excl(self, i: int) -> dict:
        x = self.c["exclusions"][i]
        # The BLCK T&C PDF has a watermark printed through the last bullet; keep the clean prefix.
        quote = x["quote"].split(" ❖ Purchase of foreign currency")[0]
        return {"url": x["url"], "quote": quote}

    def fees(self) -> dict:
        return {"url": self.c["fees"]["url"], "quote": self.c["fees"]["quote"]}

    def point_value(self) -> list[dict]:
        cid = self.c["id"]
        if cid in POINT_VALUE_SOURCES:
            return POINT_VALUE_SOURCES[cid](self.c)
        url = self.c.get("point_value_url") or self.c["earn"][-1]["url"]
        return [{"url": url, "quote": verbatim(cid, self.c["point_value_quote"])}]

    def network(self) -> list[dict]:
        out = []
        if self.c.get("network_quote"):
            out.append({"url": self.c["network_url"], "quote": self.c["network_quote"]})
        if self.c.get("upi_rupay_quote"):
            out.append({"url": self.c["upi_rupay_url"], "quote": self.c["upi_rupay_quote"]})
        return out

    def milestone(self, i: int) -> dict:
        m = self.c["milestones"][i]
        return {"url": m["url"], "quote": m["quote"]}


def pct(bp: int) -> dict:
    return {"kind": "pct", "bp": bp}


def per(points: int, per_rupees: int) -> dict:
    return {"kind": "per_spend", "points": points, "per_paise": per_rupees * RUPEE}


def fees(s: Src, joining: int, annual: int, waiver: int | None) -> dict:
    return {
        "joining_paise": joining * RUPEE,
        "annual_paise": annual * RUPEE,
        "waiver_spend_paise": waiver * RUPEE if waiver is not None else None,
        "src": [s.fees()],
    }


def regalia_gold(s: Src) -> dict:
    return {
        "fees": fees(s, 2500, 2500, 400_000),
        "currency": {"kind": "points", "name": "HDFC Reward Points", "value_paise": 50, "floor_paise": 20, "src": s.point_value()},
        "earn_rules": [
            {"id": "base", "rate": per(5, 200), "cap_ids": ["cycle"], "src": [s.earn(0)]},
            {"id": "grocery", "match": {"categories": ["grocery"]}, "rate": per(5, 200), "cap_ids": ["grocery", "cycle"], "src": [s.earn(0), s.earn(1)]},
            {"id": "insurance", "match": {"categories": ["insurance"]}, "rate": per(5, 200), "cap_ids": ["insurance", "cycle"], "src": [s.earn(0), s.earn(2)]},
            {"id": "x5_bonus", "match": {"merchants": ["myntra", "nykaa", "reliance_digital", "marks_and_spencer"]}, "rate": per(20, 200), "stacks": True, "cap_ids": ["x5"], "src": [s.earn(3)],
             "note": "5X = 25 RP per ₹200; the bonus over the 5 RP base is 20 RP and only the bonus is capped."},
        ],
        "caps": [
            {"id": "cycle", "amount": 50_000, "unit": "points", "period": "statement_cycle", "src": [s.earn_cap(0)]},
            {"id": "grocery", "amount": 2_000, "unit": "points", "period": "calendar_month", "src": [s.earn(1)]},
            {"id": "insurance", "amount": 2_000, "unit": "points", "period": "calendar_month", "src": [s.earn(2)]},
            {"id": "x5", "amount": 5_000, "unit": "points", "period": "calendar_month", "src": [s.earn(3)]},
        ],
        "exclusions": [
            {"categories": ["fuel"], "src": [s.excl(0)]},
            {"categories": ["wallet"], "src": [s.excl(1)]},
            {"categories": ["rent", "government"], "src": [s.excl(3)]},
        ],
        "min_txn_paise": 150 * RUPEE,
        "min_txn_src": [s.excl(4)],
        "milestones": [
            {"spend_paise": 500_000 * RUPEE, "period": "anniversary_year", "value_paise": 5_000 * RUPEE, "description": "₹5,000 flight voucher at ₹5 lakh", "src": [s.milestone(0)]},
            {"spend_paise": 750_000 * RUPEE, "period": "anniversary_year", "value_paise": 5_000 * RUPEE, "description": "₹5,000 flight voucher at ₹7.5 lakh", "src": [s.milestone(0)]},
            {"spend_paise": 150_000 * RUPEE, "period": "calendar_quarter", "value_paise": 1_500 * RUPEE, "description": "₹1,500 Myntra/Nykaa voucher at ₹1.5 lakh a quarter", "src": [s.milestone(1)]},
        ],
    }


def millennia(s: Src) -> dict:
    return {
        "fees": fees(s, 1000, 1000, 100_000),
        "currency": {"kind": "cashback", "name": "CashPoints", "value_paise": 100, "src": s.point_value()},
        "earn_rules": [
            {"id": "online_10", "match": {"merchants": ["amazon", "bookmyshow", "cultfit", "flipkart", "myntra", "sonyliv", "swiggy", "tatacliq", "uber", "zomato"]}, "rate": pct(500), "cap_ids": ["online_10"], "src": [s.earn(0)]},
            {"id": "other", "rate": pct(100), "cap_ids": ["other"], "src": [s.earn(1)]},
        ],
        "caps": [
            {"id": "online_10", "amount": 1_000 * RUPEE, "unit": "paise", "period": "calendar_month", "src": [s.earn(0)]},
            {"id": "other", "amount": 1_000 * RUPEE, "unit": "paise", "period": "calendar_month", "src": [s.earn(1)]},
        ],
        "exclusions": [
            {"categories": ["fuel", "rent", "government"], "src": [s.excl(0)]},
            {"categories": ["wallet"], "src": [s.excl(1)]},
            {"categories": ["education"], "src": [s.excl(2)]},
            {"categories": ["gift_card"], "rule_ids": ["other"], "src": [s.excl(3)]},
        ],
        "milestones": [
            {"spend_paise": 100_000 * RUPEE, "period": "calendar_quarter", "value_paise": 1_000 * RUPEE, "description": "₹1,000 gift voucher at ₹1 lakh a quarter", "src": [s.milestone(0)]},
        ],
    }


def swiggy(s: Src, swiggy_bp: int, fee: int, waiver: int) -> dict:
    return {
        "identity": {"network": s.c["network"], "src": [{"url": s.c["network_url"], "quote": s.c["network_quote"]}]},
        "fees": fees(s, fee, fee, waiver),
        "currency": {"kind": "cashback", "name": "Cashback", "value_paise": 100, "src": s.point_value()},
        "earn_rules": [
            {"id": "swiggy", "match": {"merchants": ["swiggy"]}, "rate": pct(swiggy_bp), "cap_ids": ["swiggy"], "min_txn_paise": 249 * RUPEE, "src": [s.earn(0), s.excl(2)]},
            {"id": "online", "match": {"categories": ["online", "travel", "entertainment"], "channels": ["online"]}, "rate": pct(500), "cap_ids": ["online"], "src": [s.earn(1)]},
            {"id": "other", "rate": pct(100), "cap_ids": ["other"], "src": [s.earn(2)]},
        ],
        "caps": [
            {"id": "swiggy", "amount": 1_500 * RUPEE, "unit": "paise", "period": "statement_cycle", "src": [s.earn(0)]},
            {"id": "online", "amount": 1_500 * RUPEE, "unit": "paise", "period": "statement_cycle",
             "src": [s.earn_cap(1)] if s.c["earn"][1].get("cap_quote") else [s.earn(1)]},
            {"id": "other", "amount": 1_000 * RUPEE, "unit": "paise", "period": "statement_cycle", "src": [s.earn(2)]},
        ],
        "exclusions": [
            {"categories": ["wallet", "gift_card", "rent", "government", "gaming", "education", "fuel", "jewellery"], "src": [s.excl(0)]},
        ],
    }


def amazon_icici(s: Src) -> dict:
    return {
        "fees": fees(s, 0, 0, None),
        # Credited as Amazon Pay balance at ₹1 a point: rupee value, so it ranks as cashback.
        "currency": {"kind": "cashback", "name": "Amazon Pay balance", "value_paise": 100, "src": s.point_value()},
        "earn_rules": [
            {"id": "amazon_prime", "match": {"merchants": ["amazon"]}, "rate": pct(500), "requires": ["amazon_prime"], "src": [s.earn(0)]},
            {"id": "amazon", "match": {"merchants": ["amazon"]}, "rate": pct(300), "src": [s.earn(1)]},
            {"id": "other", "rate": pct(100), "src": [s.earn(3)]},
        ],
        "exclusions": [
            {"categories": ["education"], "src": [s.excl(0)]},
            {"categories": ["utilities"], "except_merchants": ["amazon"], "src": [s.excl(1)]},
            {"categories": ["fuel", "jewellery", "government"], "src": [s.excl(2)]},
            {"categories": ["rent"], "src": [s.excl(3)]},
        ],
    }


def axis_flipkart(s: Src) -> dict:
    return {
        "fees": fees(s, 0, 500, 350_000),
        "currency": {"kind": "cashback", "name": "Cashback", "value_paise": 100, "src": s.point_value()},
        "earn_rules": [
            {"id": "myntra", "match": {"merchants": ["myntra"]}, "rate": pct(750), "cap_ids": ["myntra"], "src": [s.earn(0)]},
            {"id": "flipkart", "match": {"merchants": ["flipkart"]}, "rate": pct(500), "cap_ids": ["flipkart"], "src": [s.earn(1)]},
            {"id": "cleartrip", "match": {"merchants": ["cleartrip"]}, "rate": pct(500), "cap_ids": ["cleartrip"], "src": [s.earn(2)]},
            {"id": "preferred", "match": {"merchants": ["swiggy"]}, "rate": pct(400), "src": [s.earn(3)],
             "note": "Preferred-merchant list is image-only; Swiggy food delivery is named in the T&C."},
            {"id": "other", "rate": pct(100), "src": [s.earn(4)]},
        ],
        "caps": [
            {"id": k, "amount": 4_000 * RUPEE, "unit": "paise", "period": "statement_quarter", "src": [s.earn(i)]}
            for i, k in enumerate(["myntra", "flipkart", "cleartrip"])
        ],
        "exclusions": [
            {"categories": ["utilities", "education", "rent", "wallet", "government", "insurance", "jewellery", "fuel"], "src": [s.excl(0)]},
            {"categories": ["gift_card"], "src": [s.excl(1)]},
            {"categories": ["tolls"], "src": [s.excl(2)]},
        ],
        "min_txn_paise": 100 * RUPEE,
        "min_txn_src": [s.excl(3)],
    }


def axis_atlas(s: Src) -> dict:
    otas = ["makemytrip", "cleartrip", "goibibo", "easemytrip", "ixigo", "yatra"]
    return {
        "fees": fees(s, 5000, 5000, None),
        "currency": {"kind": "points", "name": "EDGE Miles", "value_paise": 100, "src": s.point_value()},
        "earn_rules": [
            {"id": "travel", "match": {"categories": ["travel"]}, "rate": per(5, 100), "cap_ids": ["travel_spend"], "src": [s.earn(0)],
             "note": "Travel EDGE, airlines and hotels; OTAs and travel agents earn the base rate."},
            {"id": "base", "rate": per(2, 100), "src": [s.earn(1)]},
        ],
        "caps": [
            {"id": "travel_spend", "amount": 200_000 * RUPEE, "unit": "spend_paise", "period": "calendar_month", "src": [s.earn(0)]},
        ],
        "exclusions": [
            {"categories": ["jewellery", "rent", "wallet", "government", "insurance", "fuel", "utilities", "gift_card", "tolls"], "src": [s.excl(0)]},
            {"merchants": otas, "rule_ids": ["travel"], "src": [s.earn(0)]},
        ],
        "milestones": [
            {"spend_paise": a * RUPEE, "period": "anniversary_year", "value_paise": m * RUPEE, "description": d, "src": [s.milestone(0)]}
            for a, m, d in [(300_000, 2_500, "2,500 EDGE Miles at ₹3 lakh"), (750_000, 2_500, "2,500 more at ₹7.5 lakh"), (1_500_000, 5_000, "5,000 more at ₹15 lakh")]
        ],
    }


def identity(s: Src) -> dict:
    return {"network": s.c["network"], "upi_rupay": s.c["upi_rupay"], "src": s.network()}


def tata_neu_infinity(s: Src) -> dict:
    return {
        "identity": identity(s),
        "fees": fees(s, 1499, 1499, 300_000),
        "currency": {"kind": "points", "name": "NeuCoins", "value_paise": 100, "src": s.point_value()},
        "earn_rules": [
            {"id": "tata_neu", "match": {"merchants": ["tata_neu"]}, "rate": pct(500), "src": [s.earn(0)]},
            {"id": "neupass_bonus", "match": {"merchants": ["tata_neu"]}, "rate": pct(500), "stacks": True, "requires": ["neupass"], "src": [s.earn(1)]},
            {"id": "grocery", "match": {"categories": ["grocery"]}, "rate": pct(150), "cap_ids": ["grocery"], "src": [s.earn(2), s.earn(3)]},
            {"id": "utilities", "match": {"categories": ["utilities"]}, "rate": pct(150), "cap_ids": ["utilities"], "src": [s.earn(2), s.earn(4)]},
            {"id": "insurance", "match": {"categories": ["insurance"]}, "rate": pct(150), "cap_ids": ["insurance"], "src": [s.earn(2), s.earn(6)]},
            {"id": "upi", "match": {"channels": ["upi"]}, "rate": pct(50), "cap_ids": ["upi"], "priority": 1, "src": [s.earn(7)]},
            {"id": "other", "rate": pct(150), "src": [s.earn(2)]},
        ],
        "caps": [
            {"id": "grocery", "amount": 2_000 * RUPEE, "unit": "paise", "period": "calendar_month", "src": [s.earn(3)]},
            {"id": "utilities", "amount": 2_000 * RUPEE, "unit": "paise", "period": "calendar_month", "src": [s.earn(4)]},
            {"id": "insurance", "amount": 2_000 * RUPEE, "unit": "paise", "period": "calendar_month", "src": [s.earn(6)]},
            {"id": "upi", "amount": 500 * RUPEE, "unit": "paise", "period": "calendar_month", "src": [s.earn_cap(7)]},
        ],
        "exclusions": [
            {"categories": ["fuel", "wallet", "rent", "government", "gaming"], "src": [s.excl(0)]},
            {"categories": ["education"], "src": [s.excl(2)]},
        ],
    }


def infinia(s: Src) -> dict:
    return {
        "fees": fees(s, 12500, 12500, 1_000_000),
        "currency": {"kind": "points", "name": "HDFC Reward Points", "value_paise": 100, "src": s.point_value()},
        "earn_rules": [
            {"id": "base", "rate": per(5, 150), "cap_ids": ["cycle"], "src": [s.earn(0)]},
            {"id": "grocery", "match": {"categories": ["grocery"]}, "rate": per(5, 150), "cap_ids": ["grocery", "cycle"], "src": [s.earn(0), s.earn(1)]},
            {"id": "insurance", "match": {"categories": ["insurance"]}, "rate": per(5, 150), "cap_ids": ["insurance", "cycle"], "src": [s.earn(0), s.earn(2)]},
            {"id": "utilities", "match": {"categories": ["utilities"]}, "rate": per(5, 150), "cap_ids": ["utilities", "cycle"], "src": [s.earn(0), s.earn(3)]},
        ],
        "caps": [
            {"id": "cycle", "amount": 200_000, "unit": "points", "period": "statement_cycle", "src": [s.earn_cap(0)]},
            {"id": "grocery", "amount": 2_000, "unit": "points", "period": "calendar_month", "src": [s.earn(1)]},
            {"id": "insurance", "amount": 10_000, "unit": "points", "period": "calendar_month", "src": [s.earn(2)]},
            {"id": "utilities", "amount": 2_000, "unit": "points", "period": "calendar_month", "src": [s.earn(3)]},
        ],
        "exclusions": [
            {"categories": ["fuel"], "src": [s.excl(0)]},
            {"categories": ["wallet"], "src": [s.excl(1)]},
            {"categories": ["rent", "government"], "src": [s.excl(2)]},
        ],
    }


def sbi_cashback(s: Src) -> dict:
    return {
        "fees": fees(s, 999, 999, 200_000),
        "currency": {"kind": "cashback", "name": "Cashback", "value_paise": 100, "src": [s.earn(0)]},
        "earn_rules": [
            {"id": "online", "match": {"channels": ["online"]}, "rate": pct(500), "cap_ids": ["online"], "src": [s.earn(0)]},
            {"id": "offline", "match": {"channels": ["offline"]}, "rate": pct(100), "cap_ids": ["offline"], "src": [s.earn(1)]},
        ],
        "caps": [
            {"id": "online", "amount": 2_000 * RUPEE, "unit": "paise", "period": "statement_cycle", "src": [s.earn(0), s.earn_cap(0)]},
            {"id": "offline", "amount": 2_000 * RUPEE, "unit": "paise", "period": "statement_cycle", "src": [s.earn(1)]},
        ],
        "exclusions": [
            {"categories": ["gaming", "tolls", "government"], "src": [s.excl(0)]},
            {"categories": ["utilities", "insurance", "fuel", "rent", "wallet", "education", "jewellery"], "src": [s.excl(1)]},
        ],
    }


def bpcl_octane(s: Src) -> dict:
    return {
        "identity": identity(s),
        "fees": fees(s, 1499, 1499, 200_000),
        "currency": {"kind": "points", "name": "SBI Card Reward Points", "value_paise": 25, "src": s.point_value()},
        "earn_rules": [
            {"id": "bpcl", "match": {"merchants": ["bpcl"]}, "rate": per(25, 100), "cap_ids": ["bpcl"], "src": [s.earn(0)]},
            {"id": "accelerated", "match": {"categories": ["grocery", "dining", "entertainment"]}, "rate": per(10, 100), "cap_ids": ["accelerated"], "src": [s.earn(2)]},
            {"id": "other", "rate": per(1, 100), "src": [s.earn(3)], "note": "Spend unit for 1 RP inferred as ₹100 from the 25X/10X wording."},
        ],
        "caps": [
            {"id": "bpcl", "amount": 2_500, "unit": "points", "period": "statement_cycle", "src": [s.earn(0)]},
            {"id": "accelerated", "amount": 7_500, "unit": "points", "period": "calendar_month", "src": [s.earn_cap(2)]},
        ],
        "exclusions": [
            {"categories": ["fuel"], "except_merchants": ["bpcl"], "src": [s.excl(0)]},
            {"categories": ["wallet"], "src": [s.excl(1)]},
            {"categories": ["rent"], "src": [s.excl(3)]},
        ],
    }


def magnus(s: Src) -> dict:
    return {
        "fees": fees(s, 12500, 12500, 2_500_000),
        "currency": {"kind": "points", "name": "EDGE Reward Points", "value_paise": 40, "src": s.point_value()},
        "earn_rules": [
            {"id": "first_1_5l", "rate": per(12, 200), "cap_ids": ["tier1"], "priority": 1, "src": [s.earn(0)]},
            {"id": "above_1_5l", "rate": per(35, 200), "src": [s.earn(1)],
             "note": "Ceiling of credit limit + ₹1.5 lakh a month is not modelled."},
        ],
        "caps": [
            {"id": "tier1", "amount": 150_000 * RUPEE, "unit": "spend_paise", "period": "calendar_month", "src": [s.earn(0)]},
        ],
        "exclusions": [
            {"categories": ["utilities", "rent", "wallet", "government", "insurance", "jewellery", "fuel"], "src": [s.excl(0)]},
            {"categories": ["gift_card", "tolls"], "src": [s.excl(1)]},
        ],
    }


def airtel_axis(s: Src) -> dict:
    return {
        "fees": fees(s, 500, 500, 200_000),
        "currency": {"kind": "cashback", "name": "Cashback", "value_paise": 100, "src": [s.earn(3)]},
        "earn_rules": [
            {"id": "zomato", "match": {"merchants": ["zomato"]}, "rate": pct(1000), "cap_ids": ["zomato"], "min_txn_paise": 499 * RUPEE, "src": [s.earn(2)]},
            {"id": "blinkit", "match": {"merchants": ["blinkit"]}, "rate": pct(1000), "cap_ids": ["blinkit"], "min_txn_paise": 499 * RUPEE, "src": [s.earn(2)]},
            {"id": "other", "rate": pct(100), "src": [s.earn(3)],
             "note": "Airtel 25% and utilities 10% are capped at multiples of the month's base cashback; not modelled yet, so they earn the base 1%."},
        ],
        "caps": [
            {"id": k, "amount": 200 * RUPEE, "unit": "paise", "period": "calendar_month", "src": [s.earn(2)]} for k in ("zomato", "blinkit")
        ],
        "exclusions": [
            {"categories": ["fuel", "rent", "wallet", "jewellery", "insurance", "education", "government"], "src": [s.excl(0)]},
        ],
    }


def idfc_millennia(s: Src) -> dict:
    return {
        "fees": fees(s, 0, 0, None),
        "currency": {"kind": "points", "name": "IDFC FIRST Reward Points", "value_paise": 25, "src": s.point_value()},
        "earn_rules": [
            {"id": "x10", "match": {"categories": ["dining", "travel"]}, "rate": per(10, 200), "src": [s.earn(0)]},
            {"id": "x1", "match": {"categories": ["utilities", "insurance", "tolls"]}, "rate": per(1, 200), "src": [s.earn(2)]},
            {"id": "x3", "rate": per(3, 200), "src": [s.earn(1)]},
        ],
        "exclusions": [{"categories": ["fuel"], "src": [s.excl(0)]}],
    }


def live_plus(s: Src) -> dict:
    return {
        "identity": identity(s),
        "fees": fees(s, 999, 999, 200_000),
        "currency": {"kind": "cashback", "name": "Cashback", "value_paise": 100, "src": [s.earn(3)]},
        "earn_rules": [
            {"id": "accelerated", "match": {"categories": ["dining", "grocery", "online", "utilities"]}, "rate": pct(1000), "cap_ids": ["accelerated"], "src": [s.earn(0)]},
            {"id": "amazon_flipkart", "match": {"merchants": ["amazon", "flipkart"]}, "rate": pct(150), "src": [s.earn(1)]},
            {"id": "myntra_offer", "match": {"merchants": ["myntra"]}, "rate": pct(1000), "cap_ids": ["accelerated"], "src": [s.earn(2)],
             "note": "Launch offer until 31 Oct 2026; assumed to share the ₹1,200 cap."},
            {"id": "other", "rate": pct(150), "src": [s.earn(3)]},
        ],
        "caps": [
            {"id": "accelerated", "amount": 1_200 * RUPEE, "unit": "paise", "period": "calendar_month", "src": [s.earn(0)]},
        ],
        "exclusions": [
            {"categories": ["fuel", "wallet", "rent", "education", "government", "insurance", "jewellery", "gaming"], "src": [s.excl(1)]},
        ],
    }


def kotak_league(s: Src) -> dict:
    return {
        "fees": fees(s, 499, 499, 50_000),
        "currency": {"kind": "points", "name": "Kotak Reward Points", "value_paise": 10, "src": s.point_value()},
        "earn_rules": [
            {"id": "special", "match": {"categories": ["travel"]}, "rate": per(8, 150), "src": [s.earn(0)]},
            {"id": "utilities", "match": {"categories": ["utilities"]}, "rate": per(4, 150), "cap_ids": ["utilities"], "src": [s.earn(3), s.earn(1)]},
            {"id": "first_2l", "rate": per(4, 150), "cap_ids": ["tier1"], "priority": 1, "src": [s.earn(1)]},
            {"id": "above_2l", "rate": per(8, 150), "src": [s.earn(2)]},
        ],
        "caps": [
            {"id": "utilities", "amount": 35_000 * RUPEE, "unit": "spend_paise", "period": "statement_cycle", "spill": False, "src": [s.earn(3)]},
            {"id": "tier1", "amount": 200_000 * RUPEE, "unit": "spend_paise", "period": "anniversary_year", "src": [s.earn(0)]},
        ],
        "exclusions": [
            {"categories": ["wallet", "gaming", "insurance", "government", "rent", "education", "fuel"], "src": [s.excl(0)]},
            {"merchants": ["irctc"], "src": [s.excl(1)]},
        ],
        "milestones": [
            {"spend_paise": 125_000 * RUPEE, "period": "half_year", "value_paise": 10_000 * 10, "description": "10,000 reward points (or 4 PVR tickets) at ₹1.25 lakh every 6 months", "src": [s.milestone(0)]},
        ],
    }


def kiwi(s: Src) -> dict:
    # YES Bank's MITC lists Klick on the RuPay row; Kiwi, the fintech operator, owns the reward programme.
    return {
        "identity": {"network": "RuPay", "upi_rupay": True, "src": [s.fees()]},
        "fees": fees(s, 0, 0, None),
        "currency": {"kind": "cashback", "name": "Cashback", "value_paise": 100, "src": [s.earn(0)]},
        "earn_rules": [
            {"id": "upi_neon", "match": {"channels": ["upi"]}, "rate": pct(200), "requires": ["kiwi_neon"], "priority": 1, "src": [s.earn(2)]},
            {"id": "upi", "match": {"channels": ["upi"]}, "rate": pct(150), "src": [s.earn(0)]},
            {"id": "online", "match": {"channels": ["online"]}, "rate": pct(50), "src": [s.earn(1)],
             "note": "Kiwi's 0.5% is on online UPI payments; non-UPI card spends earn points at a rate not in the page text."},
        ],
    }


def fees_only(s: Src, joining: int, annual: int, waiver: int | None) -> dict:
    return {"fees": fees(s, joining, annual, waiver)}


MAPPERS = {
    "hdfc_regalia_gold": regalia_gold,
    "hdfc_millennia": millennia,
    "hdfc_swiggy_blck": lambda s: swiggy(s, 1000, 1000, 200_000),
    "hdfc_swiggy_ornge": lambda s: swiggy(s, 500, 500, 150_000),
    "icici_amazon_pay": amazon_icici,
    "axis_flipkart": axis_flipkart,
    "axis_atlas": axis_atlas,
    "hdfc_tata_neu_infinity": tata_neu_infinity,
    "hdfc_infinia_metal": infinia,
    "sbi_cashback": sbi_cashback,
    "sbi_bpcl_octane": bpcl_octane,
    "axis_magnus": magnus,
    "axis_airtel": airtel_axis,
    "idfc_first_millennia": idfc_millennia,
    "hsbc_live_plus": live_plus,
    "kotak_league_platinum": kotak_league,
    # Base earn rate or point value not stated on any official page we could fetch:
    # catalogue entry with fees only, shown as "can't assess yet" (A1).
    "sbi_simplyclick": lambda s: fees_only(s, 499, 499, 100_000),
    "icici_coral": lambda s: fees_only(s, 500, 500, 150_000),
    "au_lit": lambda s: fees_only(s, 0, 0, None),
    "scapia_federal": lambda s: fees_only(s, 0, 0, None),
    "kiwi_yes_klick": kiwi,
}


def main() -> None:
    cards = load_cards()
    OUT.mkdir(parents=True, exist_ok=True)
    for cid, mapper in MAPPERS.items():
        c = cards.get(cid)
        if c is None:
            print(f"skip {cid}: not in research files", file=sys.stderr)
            continue
        body = {"id": cid, "name": c["name"], "issuer": c["issuer"], **mapper(Src(c))}
        profile = CardProfile.model_validate(body)
        (OUT / f"{cid}.json").write_text(profile.model_dump_json(indent=2, exclude_none=True) + "\n")
        print(f"wrote {cid}: {len(profile.earn_rules)} rules, {len(profile.caps)} caps, {len(profile.exclusions)} exclusions")


if __name__ == "__main__":
    main()
