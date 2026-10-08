"""Launch Radar source workers (DR-1: one worker per source family, each with its own
search cap). A worker turns SerpApi results into Leads; it never writes knowledge."""

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from cc_smith.config import settings
from cc_smith.knowledge import allowlist
from cc_smith.ops import serp
from cc_smith.signals import triage

FLOW = "launch_radar"
# gl=in does not localise a generic English query (live run R10), so the query names
# India; `so` is rejected together with `q` (R9), so results are filtered by date in code.
NEWS_QUERIES = ("launches new credit card India when:30d",)
NEWS_MAX_AGE = timedelta(days=30)
# Top four issuers by cards outstanding (seed-cards.md §1); 4 searches a week fits the
# 45-search monthly envelope with news and discovery.
ADS_ISSUERS = ("sbi_card", "hdfc_bank", "icici_bank", "axis_bank")
INDIA_REGION = "2356"  # verified in live run R18 (region_name "India")
ADS_WINDOW = timedelta(days=30)
NEW_CREATIVE_DAYS = 14
MAX_AD_READS = 2  # ad-details searches per issuer per sweep
# Legal advertiser names; Ads Transparency returns affiliates bidding on the issuer's
# domain too (R18: 13 of 40 SBI ads), so only these advertisers' ids are kept.
OWN_ADVERTISERS = {
    "sbi_card": "SBI CARDS AND PAYMENT SERVICES LIMITED",
    "hdfc_bank": "HDFC BANK LIMITED",
    "icici_bank": "ICICI BANK LIMITED",
    "axis_bank": "AXIS BANK LIMITED",
    "kotak_mahindra_bank": "KOTAK MAHINDRA BANK LIMITED",
}


@dataclass
class Lead:
    source: str  # news | ads
    issuer: str
    card_name: str
    refs: list[dict]
    summary: str

    @property
    def key(self) -> str:
        return triage.dedupe_key(self.issuer, self.card_name)


@dataclass
class WorkerReport:
    worker: str
    searches: int = 0
    seen: int = 0
    leads: list[Lead] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _why(e: Exception) -> str:
    # A missing replay fixture is expected for sources not recorded yet; say so briefly.
    return "not recorded for replay" if isinstance(e, serp.ReplayMissing) else str(e)


def _news_date(item: dict) -> datetime | None:
    if item.get("iso_date"):
        return datetime.fromisoformat(item["iso_date"])
    try:  # google_news `date`: "10/01/2026, 07:00 AM, +0000 UTC"
        return datetime.strptime(item.get("date") or "", "%m/%d/%Y, %I:%M %p, %z UTC")
    except ValueError:
        return None


def news_worker(as_of: date) -> WorkerReport:
    rep = WorkerReport("google_news")
    cutoff = datetime.combine(as_of, datetime.min.time(), UTC) - NEWS_MAX_AGE
    candidates: list[tuple[dict, str]] = []
    for q in NEWS_QUERIES:
        try:
            res = serp.search(FLOW, "google_news", {"q": q, "gl": "in", "hl": "en"})
        except serp.SerpError as e:
            rep.skipped.append(f"{q}: {_why(e)}")
            continue
        rep.searches += 1
        for item in res.data.get("news_results", []):
            rep.seen += 1
            when = _news_date(item)
            if when is not None and when < cutoff:
                rep.dropped.append(f"stale: {item.get('title')}")
                continue
            candidates.append((item, res.search_id))
    verdicts = [triage.rules(it.get("title", ""), it.get("snippet", "")) for it, _ in candidates]
    if settings.mode == "live" and settings.anthropic_api_key:
        verdicts = _llm_refine(candidates, verdicts)
    for (item, sid), v in zip(candidates, verdicts, strict=True):
        if not v.is_launch:
            rep.dropped.append(f"{'; '.join(v.reasons)}: {item.get('title')}")
            continue
        src = item.get("source") or {}
        ref = {"url": item.get("link"), "title": item.get("title"), "source": src.get("name") if isinstance(src, dict) else src,
               "date": item.get("iso_date") or item.get("date"), "search_id": sid, "official": False, "kind": "news"}
        rep.leads.append(Lead("news", v.issuer, v.card_name, [ref], item.get("title", "")))
    return rep


def _llm_refine(candidates, verdicts):
    """Haiku names the card for headlines the rules let through; rule output stays the
    fallback when the call fails, so a model outage never empties the sweep."""
    from cc_smith.signals import llm

    idx = [i for i, v in enumerate(verdicts) if v.is_launch]
    if not idx:
        return verdicts
    heads = [{"index": i, "title": candidates[i][0].get("title"), "date": candidates[i][0].get("date")} for i in idx]
    try:
        out = llm.triage_headlines(heads)
    except Exception as e:  # noqa: BLE001
        for i in idx:
            verdicts[i].reasons.append(f"llm triage failed: {e!r}"[:200])
        return verdicts
    for h in out.items:
        if h.index not in idx:
            continue
        v = verdicts[h.index]
        if not h.is_new_credit_card:
            v.is_launch, v.reasons = False, ["llm: not a new credit card"]
        elif h.card_name:
            v.card_name = h.card_name
            v.issuer = triage.find_issuer(h.issuer or "") or v.issuer
            v.reasons.append("llm")
    return verdicts


def _ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _domain(key: str) -> str | None:
    canonical = (allowlist.load()["issuers"].get(key) or {}).get("canonical")
    return canonical.removeprefix("www.") if canonical else None


def _read_creative(ad: dict) -> tuple[dict, str | None]:
    """Text ads come back as rendered images (R19), so the creative is read with vision.
    Replay serves the recorded reading from fixtures/ads_read/<creative_id>.json."""
    cid = ad["ad_creative_id"]
    res = serp.search(FLOW, "google_ads_transparency_center_ad_details",
                      {"advertiser_id": ad["advertiser_id"], "creative_id": cid, "region": INDIA_REGION})
    if settings.mode == "replay":
        path = settings.fixtures_dir / "ads_read" / f"{cid}.json"
        if not path.exists():
            raise serp.ReplayMissing(f"no recorded ad reading for {cid} (fixtures/ads_read)")
        return json.loads(path.read_text()), res.search_id
    from cc_smith.signals import llm

    images = [c["image"] for c in res.data.get("ad_creatives", []) if c.get("image")]
    if not images:
        raise llm.LLMError(f"{cid}: ad details returned no image")
    reading = llm.read_ad(images).model_dump()
    path = settings.fixtures_dir / "ads_read" / f"{cid}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reading, indent=2, ensure_ascii=False) + "\n")
    return reading, res.search_id


def ads_worker(as_of: date, issuers: tuple[str, ...] = ADS_ISSUERS) -> WorkerReport:
    rep = WorkerReport("google_ads_transparency_center")
    end = as_of
    new_after = datetime.combine(as_of, datetime.min.time(), UTC) - timedelta(days=NEW_CREATIVE_DAYS)
    for key in issuers:
        domain = _domain(key)
        legal = (allowlist.load()["issuers"].get(key) or {}).get("name", key)
        issuer_name = triage.find_issuer(legal) or legal
        if domain is None:
            rep.skipped.append(f"{key}: no canonical domain")
            continue
        params = {"text": domain, "region": INDIA_REGION, "start_date": _ymd(end - ADS_WINDOW), "end_date": _ymd(end)}
        try:
            res = serp.search(FLOW, "google_ads_transparency_center", params)
        except serp.SerpError as e:
            rep.skipped.append(f"{key}: {_why(e)}")
            continue
        rep.searches += 1
        ads = res.data.get("ad_creatives", [])
        rep.seen += len(ads)
        own_name = OWN_ADVERTISERS.get(key)
        own_ids = {a["advertiser_id"] for a in ads if own_name and a.get("advertiser", "").upper() == own_name}
        affiliates = sorted({a.get("advertiser", "?") for a in ads if a.get("advertiser_id") not in own_ids})
        if affiliates:
            rep.dropped.append(f"{key}: {len([a for a in ads if a.get('advertiser_id') not in own_ids])} ads from other advertisers ({', '.join(affiliates)})")
        fresh = sorted(
            (a for a in ads if a.get("advertiser_id") in own_ids and datetime.fromtimestamp(a.get("first_shown", 0), UTC) >= new_after),
            key=lambda a: -a.get("first_shown", 0),
        )
        for ad in fresh[:MAX_AD_READS]:
            try:
                reading, sid = _read_creative(ad)
            except Exception as e:  # noqa: BLE001 - one unreadable creative must not stop the sweep
                rep.skipped.append(f"{key} {ad['ad_creative_id']}: {_why(e)}"[:300])
                continue
            rep.searches += 1
            ref = {
                "url": ad.get("details_link"), "advertiser": ad.get("advertiser"), "advertiser_id": ad["advertiser_id"],
                "creative_id": ad["ad_creative_id"], "format": ad.get("format"),
                "first_shown": datetime.fromtimestamp(ad["first_shown"], UTC).isoformat(),
                "quote": reading.get("text"), "search_id": sid, "official": False, "kind": "ad",
            }
            for card in reading.get("cards", []):
                summary = f"New {issuer_name} ad" + (f": {reading['offer']}" if reading.get("offer") else "")
                rep.leads.append(Lead("ads", issuer_name, card, [ref], summary))
    return rep
