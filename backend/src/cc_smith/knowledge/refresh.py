"""Card refresh (scheduled): re-check catalogue cards on the bank's own site through
SerpApi, a few cards a night, so published facts follow the bank's current pages.

Same path as a new launch (DR-4, DR-12): SerpApi Google Search limited to the issuer's
allow-listed domain → fetch → extract → quote and range checks → fact or speculation.
A value that is unchanged only bumps its as-of date; a changed value that passes the
checks is published and shows in Market › What changed."""

from dataclasses import asdict, dataclass, field

from sqlalchemy import select

from cc_smith.config import settings
from cc_smith.db import card, engine
from cc_smith.knowledge import allowlist
from cc_smith.knowledge.discover import discover
from cc_smith.knowledge.extract import ExtractionError, extract_terms
from cc_smith.knowledge.fetcher import FetchError, fetch
from cc_smith.knowledge.pipeline import profile_card
from cc_smith.ops import serp

FLOW = "card_profile"
# 70 searches a month (DR-5) at up to 2 searches a card: 3 cards a night re-checks the
# 22-card catalogue about once a week, and the 30-day search cache keeps repeats free.
CARDS_PER_RUN = 3
MAX_PAGES = 4


@dataclass
class CardRefresh:
    card_id: str
    status: str  # refreshed | skipped
    reason: str = ""
    summary: dict[str, int] = field(default_factory=dict)
    urls: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def due(card_ids: list[str], last: dict[str, str], n: int = CARDS_PER_RUN) -> list[str]:
    """Never-checked cards first, then the longest ago; ties by id so runs are repeatable."""
    return sorted(card_ids, key=lambda cid: (last.get(cid, ""), cid))[:n]


def catalogue_ids() -> list[str]:
    with engine().begin() as c:
        return [r.id for r in c.execute(select(card.c.id).where(card.c.status == "active"))]


def refresh_card(card_id: str) -> CardRefresh:
    with engine().begin() as c:
        row = c.execute(select(card).where(card.c.id == card_id)).first()
    if row is None:
        return CardRefresh(card_id, "skipped", "not in the catalogue")
    if allowlist.issuer_key(row.issuer) is None:
        return CardRefresh(card_id, "skipped", f"{row.issuer} is not on the official-domain allow-list")
    try:
        urls = discover(row.name, row.issuer, flow=FLOW)
        have = {u.url for u in urls}
        urls += [u for u in discover(row.name, row.issuer, flow=FLOW, page=False, pdf=True) if u.url not in have]
    except serp.ReplayMissing:
        return CardRefresh(card_id, "skipped", "no recorded search to replay; runs on the next live refresh")
    except serp.SerpError as e:
        return CardRefresh(card_id, "skipped", f"search did not run ({e})")
    if not urls:
        return CardRefresh(card_id, "skipped", "no official page found on the issuer's domain")
    live = settings.mode == "live"
    evidence = []
    for u in urls[:MAX_PAGES]:
        try:
            evidence.append(fetch(u.url, refresh=live))
        except FetchError:
            continue
    found = [u.url for u in urls[:MAX_PAGES]]
    if not evidence:
        return CardRefresh(card_id, "skipped", "official page found but could not be fetched", urls=found)
    try:
        extraction = extract_terms(card_id, row.name, row.issuer, [(ev.url, ev.text) for ev in evidence])
    except ExtractionError as e:
        return CardRefresh(card_id, "skipped", f"extraction failed: {e}"[:300], urls=found)
    # Quotes are checked against the pages just fetched (live) or the recorded ones (replay).
    result = profile_card(extraction, origin="refresh", refresh=live)
    return CardRefresh(card_id, "refreshed", summary=result.summary(), urls=found)
