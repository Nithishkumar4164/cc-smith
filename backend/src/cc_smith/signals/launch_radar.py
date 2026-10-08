"""Launch Radar (architecture §4, DR-4 catalogue growth, DR-12).

Weekly sweep: source workers (news, ads) → triage → dedupe against the catalogue, the
seed list and earlier candidates → for each new card, discovery on the issuer's own
domain. A card whose official page is found is fetched, extracted and run through
profile_card (facts only from verbatim official quotes) and announced on
`launch.published`. Otherwise it is a speculative launch: listed with its refs, never
scored, and retried on the next sweep."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy import Connection, insert, select, update

from cc_smith.config import settings
from cc_smith.db import engine, launch_candidate
from cc_smith.knowledge import allowlist, store
from cc_smith.knowledge.discover import DiscoveredUrl, discover
from cc_smith.knowledge.extract import ExtractionError, extract_terms
from cc_smith.knowledge.fetcher import FetchError, fetch
from cc_smith.knowledge.pipeline import ProfileResult, profile_card
from cc_smith.knowledge.schema import CardProfile
from cc_smith.ops import outbox, serp
from cc_smith.signals import sources, triage
from cc_smith.signals.sources import Lead, WorkerReport

FLOW = sources.FLOW
# Replay is a fake clock pinned to the day the SerpApi fixtures were recorded, so the
# date-bounded Ads Transparency params hash to the recorded fixture.
REPLAY_AS_OF = date(2026, 10, 7)
MAX_PAGES = 4  # official URLs fetched per new card
PUBLISHED = {"first", "published", "unchanged"}


@dataclass
class Outcome:
    key: str
    name: str
    issuer: str
    status: str  # speculative | profiled | known
    card_id: str | None
    summary: str
    action: str  # new | promoted | seen


@dataclass
class SweepReport:
    as_of: date
    workers: list[WorkerReport]
    outcomes: list[Outcome] = field(default_factory=list)

    def detail(self) -> dict:
        return {
            "as_of": self.as_of.isoformat(),
            "workers": [{"worker": w.worker, "searches": w.searches, "seen": w.seen, "leads": len(w.leads),
                         "dropped": len(w.dropped), "skipped": w.skipped} for w in self.workers],
            "outcomes": [{"key": o.key, "status": o.status, "action": o.action, "card_id": o.card_id} for o in self.outcomes],
        }


def _merge(leads: list[Lead]) -> dict[str, Lead]:
    out: dict[str, Lead] = {}
    for lead in leads:
        if lead.key in out:
            out[lead.key].refs = _union(out[lead.key].refs, lead.refs)
        else:
            out[lead.key] = Lead(lead.source, lead.issuer, lead.card_name, list(lead.refs), lead.summary)
    return out


def _ref_id(r: dict) -> tuple:
    return (r.get("url"), r.get("creative_id"))


def _union(a: list[dict], b: list[dict]) -> list[dict]:
    seen = {_ref_id(r) for r in a}
    return a + [r for r in b if _ref_id(r) not in seen]


def known_keys(conn: Connection) -> dict[str, str]:
    """dedupe key → card id, for the catalogue plus the seed list."""
    out = {triage.dedupe_key(issuer, name): cid for cid, name, issuer in triage.seed_cards()}
    for row in store.all_cards(conn):
        out[triage.dedupe_key(row.issuer, row.name)] = row.id
    return out


@dataclass
class _Prepared:
    extraction: CardProfile | None
    refs: list[dict]
    reason: str


def _official_refs(urls: list[DiscoveredUrl]) -> list[dict]:
    return [{"url": u.url, "title": u.title, "search_id": u.search_id, "official": True, "kind": "official_page"} for u in urls]


def _prepare(lead: Lead) -> _Prepared:
    """Discovery → fetch → extract, outside any DB transaction (network and model calls
    must not hold a SQLite write lock). Failures leave the card speculative with the reason."""
    if allowlist.issuer_key(lead.issuer) is None:
        return _Prepared(None, [], f"{lead.issuer} is not on the official-domain allow-list, so no page can be official yet")
    try:
        urls = discover(lead.card_name, lead.issuer, flow=FLOW)
    except serp.ReplayMissing:
        return _Prepared(None, [], "official-page discovery has no recorded search to replay; it runs on the next live sweep")
    except serp.SerpError as e:
        return _Prepared(None, [], f"discovery did not run ({e})")
    if not urls:
        return _Prepared(None, [], "no official page found on the issuer's domain")
    # The terms PDF costs a second search, spent only once the card's page exists.
    try:
        have = {u.url for u in urls}
        urls += [u for u in discover(lead.card_name, lead.issuer, flow=FLOW, page=False, pdf=True) if u.url not in have]
    except serp.SerpError:
        pass
    refs = _official_refs(urls)
    evidence = []
    for u in urls[:MAX_PAGES]:
        try:
            evidence.append(fetch(u.url))
        except FetchError:
            continue
    if not evidence:
        return _Prepared(None, refs, "official page found but could not be fetched")
    card_id = triage.card_id_for(lead.issuer, lead.card_name)
    try:
        extraction = extract_terms(card_id, lead.card_name, lead.issuer, [(ev.url, ev.text) for ev in evidence])
    except ExtractionError as e:
        return _Prepared(None, refs, f"extraction failed: {e}")
    return _Prepared(extraction, refs, "")


def _profiled_summary(result: ProfileResult) -> str:
    published = sum(1 for f in result.fields if f.outcome in PUBLISHED)
    spec = sum(1 for f in result.fields if f.outcome == "speculation")
    tail = f", {spec} held as speculation" if spec else ""
    return f"Profiled from the bank's own pages: {published} fields published as facts{tail}."


def _process(lead: Lead, known: dict[str, str]) -> Outcome:
    with engine().begin() as c:
        row = c.execute(select(launch_candidate).where(launch_candidate.c.dedupe_key == lead.key)).first()
    if row is not None and row.status != "speculative":
        with engine().begin() as c:
            c.execute(update(launch_candidate).where(launch_candidate.c.id == row.id).values(refs=_union(row.refs, lead.refs)))
        return Outcome(lead.key, row.name, row.issuer, row.status, row.card_id, row.summary, "seen")
    if row is None and lead.key in known:
        summary = f"Already in the catalogue as {known[lead.key]}."
        with engine().begin() as c:
            c.execute(insert(launch_candidate).values(
                dedupe_key=lead.key, name=lead.card_name, issuer=lead.issuer, card_id=known[lead.key], status="known",
                refs=lead.refs, summary=summary))
        return Outcome(lead.key, lead.card_name, lead.issuer, "known", known[lead.key], summary, "new")

    prep = _prepare(lead)
    refs = _union(_union(row.refs if row is not None else [], lead.refs), prep.refs)
    # One transaction per card: the profile, the candidate row and the outbox message
    # commit together, and one bad card cannot roll back the others.
    with engine().begin() as c:
        status, card_id, reason = "speculative", None, prep.reason
        result = None
        if prep.extraction is not None:
            result = profile_card(prep.extraction, origin="launch_radar", conn=c)
            card_id = prep.extraction.id
            if any(f.outcome in PUBLISHED for f in result.fields):
                status = "profiled"
            else:
                reason = f"official page found but no field passed the quote check ({result.summary()})"
        if status == "profiled":
            summary = _profiled_summary(result)
        else:
            summary = f"Reported, not confirmed by the bank: {reason}. {lead.summary}".strip()
        values = {"name": lead.card_name, "issuer": lead.issuer, "card_id": card_id, "status": status, "refs": refs, "summary": summary}
        if row is None:
            cid = c.execute(insert(launch_candidate).values(dedupe_key=lead.key, **values)).inserted_primary_key[0]
            action = "new"
        else:
            cid = row.id
            c.execute(update(launch_candidate).where(launch_candidate.c.id == cid).values(**values))
            action = "promoted" if status == "profiled" else "seen"
        if status == "profiled":
            outbox.publish(c, "launch.published", f"launch:{cid}", {"candidate_id": cid, "card_id": card_id})
    return Outcome(lead.key, lead.card_name, lead.issuer, status, card_id, summary, action)


def detect_variants(conn: Connection) -> list[str]:
    """TODO(DR-4 'Variant or relaunch'): diff each issuer's sitemap for new card pages
    that name an existing card (e.g. Swiggy BLCK/ORNGE) and profile them separately,
    marking the old card closed_to_new. Not in the hackathon sweep."""
    return []


def detect_closed(conn: Connection) -> list[str]:
    """TODO(DR-4 removals): a card page that 404s or leaves the sitemap on two runs
    becomes 'closed to new applicants' speculation until an official notice confirms."""
    return []


def run_sweep(as_of: date | None = None, ads_issuers: tuple[str, ...] = sources.ADS_ISSUERS) -> SweepReport:
    as_of = as_of or (REPLAY_AS_OF if settings.mode == "replay" else datetime.now(UTC).date())
    workers = [sources.news_worker(as_of), sources.ads_worker(as_of, ads_issuers)]
    report = SweepReport(as_of, workers)
    with engine().begin() as c:
        known = known_keys(c)
    for lead in _merge([lead for w in workers for lead in w.leads]).values():
        report.outcomes.append(_process(lead, known))
    with engine().begin() as c:
        detect_variants(c)
        detect_closed(c)
    return report
