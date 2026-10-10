from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from cc_smith.api.main import app
from cc_smith.db import (
    card,
    card_field,
    credit_ledger,
    engine,
    launch_candidate,
    outbox,
    run_state,
)
from cc_smith.knowledge.discover import core_name, queries
from cc_smith.signals import launch_radar, triage
from cc_smith.signals.scheduler import run_radar_cli
from cc_smith.signals.sources import Lead


def _candidates() -> dict[str, object]:
    with engine().begin() as c:
        return {r.name: r for r in c.execute(select(launch_candidate))}


# ---------- triage and dedupe ----------
def test_rules_drop_apple_pay_noise_and_name_new_cards():
    assert not triage.rules("Apple Pay launches in India with Axis Bank as first partner").is_launch
    assert not triage.rules("HDFC Bank new MD-CEO takes charge").is_launch
    v = triage.rules("Google Pay Flex SBI Card Launched")
    assert (v.is_launch, v.issuer, v.card_name) == (True, "SBI Card", "Google Pay Flex SBI Card")
    v = triage.rules("Scapia and Axis Bank launch co-branded travel credit card")
    assert (v.issuer, v.card_name) == ("Axis Bank", "Scapia Axis Bank Credit Card")


def test_dedupe_key_merges_headlines_and_matches_seeds():
    a = triage.rules("Bandhan Bank enters credit card business, launches four cards with Mastercard")
    b = triage.rules("Bandhan Bank forays into credit cards with four Mastercard variants")
    assert triage.dedupe_key(a.issuer, a.card_name) == triage.dedupe_key(b.issuer, b.card_name) == "bandhan_bank:*"
    # Scapia on Axis is not the Scapia Federal card: different issuer, same family.
    assert triage.dedupe_key("Axis Bank", "Scapia Axis Bank Credit Card") not in {
        triage.dedupe_key(i, n) for _, n, i in triage.seed_cards()}
    assert triage.variant_family("Axis Bank", "Scapia Axis Bank Credit Card", list(triage.seed_cards())) == ("scapia_federal", "Scapia")
    # Parenthetical variants in seed names do not change the key.
    assert triage.dedupe_key("HDFC Bank", "HDFC Bank INFINIA Credit Card (Metal Edition)") == "hdfc_bank:infinia"
    assert triage.dedupe_key("Federal Bank (fintech partner: Scapia)", "Scapia Federal Bank Credit Card") == "federal_bank:scapia"
    assert triage.card_id_for("Axis Bank", "Axis Bank ACE Credit Card") == "axis_ace"


def test_discovery_queries_use_the_official_domain():
    assert core_name("Google Pay Flex SBI Card", "SBI Card") == "Google Pay Flex"
    assert queries("Google Pay Flex SBI Card", "SBI Card") == ['site:sbicard.com "Google Pay Flex"']
    assert queries("Bandhan Bank credit cards", "Bandhan Bank") == []  # not on the allow-list


# ---------- the sweep (replay) ----------
@pytest.fixture
def swept(db):
    report = launch_radar.run_sweep()
    return report


def test_sweep_outcomes_speculative_profiled_known(swept):
    assert swept.as_of == date(2026, 10, 7)
    rows = _candidates()
    assert {n: r.status for n, r in rows.items()} == {
        "Bandhan Bank credit cards": "speculative",  # issuer not on the allow-list
        "Google Pay Flex SBI Card": "speculative",  # R20: no sbicard.com page found
        "Flipkart SBI Credit Card": "speculative",  # SBI's own ad, no official page discovered
        "Scapia Axis Bank Credit Card": "speculative",  # its own card on Axis (suggestion 9), no Axis page recorded
        "Axis Bank ACE Credit Card": "profiled",
    }
    gpay = rows["Google Pay Flex SBI Card"]
    assert gpay.card_id is None and gpay.refs[0]["kind"] == "news" and gpay.refs[0]["official"] is False
    assert "not confirmed by the bank" in gpay.summary
    scapia_axis = rows["Scapia Axis Bank Credit Card"]
    assert scapia_axis.card_id is None
    assert scapia_axis.summary.startswith("New variant of Scapia (the catalogue has scapia_federal from another issuer).")
    flipkart = rows["Flipkart SBI Credit Card"]
    assert flipkart.refs[0]["advertiser"] == "SBI CARDS AND PAYMENT SERVICES LIMITED"
    assert "1st Year Free" in flipkart.refs[0]["quote"]
    # Two Bandhan headlines collapse into one candidate with both refs.
    assert len(rows["Bandhan Bank credit cards"].refs) == 2


def test_profiled_launch_adds_scored_card_with_facts_and_outbox(swept):
    with engine().begin() as c:
        row = c.execute(select(card).where(card.c.id == "axis_ace")).first()
        fields = {f.field for f in c.execute(select(card_field).where(card_field.c.card_id == "axis_ace", card_field.c.status == "published"))}
        msgs = c.execute(select(outbox).where(outbox.c.topic == "launch.published")).all()
    assert (row.origin, row.status) == ("launch_radar", "active")
    assert {"fees", "currency", "earn_rules", "caps", "exclusions"} <= fields
    assert [m.payload["card_id"] for m in msgs] == ["axis_ace"]
    ace = _candidates()["Axis Bank ACE Credit Card"]
    assert any(r.get("kind") == "official_page" and r["url"].startswith("https://www.axis.bank.in/") for r in ace.refs)


def test_ads_worker_keeps_only_the_issuers_own_advertiser(swept):
    ads = next(w for w in swept.workers if w.worker == "google_ads_transparency_center")
    assert {lead.issuer for lead in ads.leads} == {"SBI Card", "Axis Bank"}
    assert all(r["advertiser"] in ("SBI CARDS AND PAYMENT SERVICES LIMITED", "AXIS BANK LIMITED") for lead in ads.leads for r in lead.refs)
    assert any("MANISHA GUPTA" in d for d in ads.dropped)


def test_every_search_is_ledgered_and_replay_spends_no_credits(swept):
    with engine().begin() as c:
        rows = c.execute(select(credit_ledger)).all()
    assert rows and all(r.flow == "launch_radar" and r.cached for r in rows)


def test_second_sweep_is_idempotent(swept):
    launch_radar.run_sweep()
    with engine().begin() as c:
        assert len(c.execute(select(launch_candidate)).all()) == 5
        assert len(c.execute(select(outbox).where(outbox.c.topic == "launch.published")).all()) == 1


def test_speculative_launch_is_promoted_when_the_official_page_appears(db):
    lead = Lead("ads", "Axis Bank", "Axis Bank ACE Credit Card", [{"url": "https://adstransparency.google.com/x", "kind": "ad"}], "ad")
    with engine().begin() as c:
        c.execute(launch_candidate.insert().values(dedupe_key=lead.key, name=lead.card_name, issuer="Axis Bank", status="speculative",
                                                   refs=lead.refs, summary="earlier sweep"))
    out = launch_radar._process(lead, {})
    assert (out.status, out.action, out.card_id) == ("profiled", "promoted", "axis_ace")


def test_get_launches_lists_candidates_and_scores_the_profiled_one(swept):
    client = TestClient(app)
    rows = client.get("/launches").json()
    assert {r["status"] for r in rows} == {"speculative", "profiled"}
    uid = client.post("/users").json()["user_id"]
    hdr = {"X-User-Id": uid}
    assert client.put("/me/spends", json={"swiggy": 4_000 * 100, "online": 10_000 * 100}, headers=hdr).status_code == 200
    scored = {r["name"]: r for r in client.get("/launches", headers=hdr).json()}
    assert scored["Axis Bank ACE Credit Card"]["gain_paise"] > 0
    assert scored["Google Pay Flex SBI Card"]["gain_paise"] is None  # speculative: listed, not scored


def test_cli_records_run_state(db, capsys):
    assert run_radar_cli() == 0
    out = capsys.readouterr().out
    assert "[profiled   ] Axis Bank ACE Credit Card" in out
    with engine().begin() as c:
        rs = c.execute(select(run_state).where(run_state.c.job == "launch_radar")).first()
    assert rs.status == "ok" and rs.detail["as_of"] == "2026-10-07"



# Headlines from the first live sweep (10 Oct 2026), suggestion 8.
LIVE_HEADLINES = [
    ("IndusInd Bank", "Overdraft And Cash Credit Linked Corporate Credit Card",
     "IndusInd Bank Launches Overdraft And Cash Credit Linked Corporate Credit Card For Businesses"),
    ("IndusInd Bank", "OD CC IndusInd Bank Credit Card", "IndusInd Bank launches OD and CC linked corporate credit card for businesses"),
    ("IndusInd Bank", "IndusInd Bank OD CC Corporate Credit Card", "IndusInd Bank OD CC Corporate Credit Card Launch 2026"),
    ("SBI Card", "Launches FD-Backed Credit Card", "SBI Card Launches FD-Backed Credit Card on YONO App"),
    ("SBI Card", "Advantage SBI Card", "FD-backed SBI credit card: Advantage SBI Card launched; who can benefit from it?"),
    ("SBI Card", "FD-backed YONO SBI Card Credit Card", "SBI Card launches FD-backed secured card on SBI YONO"),
    ("SBI Card", "SBI Credit Cards", "New SBI Card ad: 10X Reward Points on everyday spends"),
    ("SBI Card", "SimplySAVE Credit Card", "New SBI Card ad: 10X Reward Points on everyday spends"),
    ("YES Bank", "Ultimate Travel Credit Card", "Niyo, YES BANK and Visa Partner to Launch the Ultimate Travel Credit Card"),
]


def _live_leads():
    from cc_smith.signals.sources import Lead

    return [Lead("news", i, n, [{"url": f"https://example.org/{k}", "kind": "news"}], h) for k, (i, n, h) in enumerate(LIVE_HEADLINES)]


def test_same_launch_under_different_headlines_collapses_to_one_lead():
    from cc_smith.signals.launch_radar import _merge

    merged = _merge(_live_leads(), covered_issuers={"sbi_card", "axis_bank", "hdfc_bank", "yes_bank"})
    by_issuer = {}
    for lead in merged.values():
        by_issuer.setdefault(lead.issuer, []).append(lead)
    assert len(by_issuer["IndusInd Bank"]) == 1 and len(by_issuer["IndusInd Bank"][0].refs) == 3
    sbi = {lead.card_name for lead in by_issuer["SBI Card"]}
    assert len(sbi) == 2  # the FD-backed card (three headlines) and SimplySAVE stay separate
    assert "SimplySAVE Credit Card" in sbi
    assert "SBI Credit Cards" not in sbi  # generic name from a bank the catalogue covers
    fd = next(lead for lead in by_issuer["SBI Card"] if lead.card_name != "SimplySAVE Credit Card")
    assert len(fd.refs) == 3
    assert len(by_issuer["YES Bank"]) == 1


def test_generic_lead_from_a_bank_new_to_the_market_is_kept():
    from cc_smith.signals.launch_radar import _merge
    from cc_smith.signals.sources import Lead

    leads = [Lead("news", "Bandhan Bank", "Bandhan Bank credit cards", [{"url": "https://a"}], "Bandhan Bank enters credit cards"),
             Lead("news", "Bandhan Bank", "Bandhan Bank credit cards", [{"url": "https://b"}], "Bandhan forays into credit cards")]
    merged = _merge(leads, covered_issuers={"sbi_card"})
    assert len(merged) == 1 and len(next(iter(merged.values())).refs) == 2


def test_ads_for_accounts_and_debit_cards_are_not_launches():
    assert triage.is_noise("Axis Bank Digital Savings Account")
    assert triage.is_noise("e-debit card")
    assert not triage.is_noise("SimplySAVE Credit Card")


def test_empty_launch_cards_are_pruned_and_profiled_ones_kept(db, cards):
    from cc_smith.knowledge import store
    from cc_smith.knowledge.pipeline import profile_card
    from cc_smith.signals.launch_radar import prune_empty_cards

    profile_card(cards["hdfc_millennia"], origin="launch_radar")
    with db.begin() as c:
        store.ensure_card(c, "sbi_flex_google_pay", "Google Pay Flex SBI Card", "SBI Card", origin="launch_radar")
        assert prune_empty_cards(c) == ["sbi_flex_google_pay"]
        assert {r.id for r in store.all_cards(c)} == {"hdfc_millennia"}
