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


def _merge(leads: list[Lead], covered_issuers: set[str] | None = None) -> dict[str, Lead]:
    """Group leads that are one launch under different wordings (suggestion 8); each group
    keeps the most specific name and every source. A generic name ("SBI Credit Cards") is
    dropped for issuers the catalogue already covers; for a bank new to the market
    ("Bandhan Bank enters credit cards") the generic lead is the news, so it stays."""
    covered = covered_issuers or set()
    groups: list[list[Lead]] = []
    for lead in leads:
        if triage.is_generic(lead.card_name, lead.issuer) and triage.issuer_slug(lead.issuer) in covered:
            continue
        home = next((g for g in groups if any(
            m.key == lead.key or triage.same_launch(m.issuer, m.card_name, m.summary, lead.issuer, lead.card_name, lead.summary)
            for m in g)), None)
        if home is None:
            groups.append([lead])
        else:
            home.append(lead)
    out: dict[str, Lead] = {}
    for g in groups:
        best = max(g, key=lambda m: (triage.specificity(m.card_name, m.issuer), len(m.card_name)))
        refs: list[dict] = []
        for m in g:
            refs = _union(refs, m.refs)
        merged = Lead(best.source, best.issuer, best.card_name, refs, best.summary)
        out[merged.key] = merged
    return out


def _ref_id(r: dict) -> tuple:
    return (r.get("url"), r.get("creative_id"))


def _union(a: list[dict], b: list[dict]) -> list[dict]:
    seen = {_ref_id(r) for r in a}
    return a + [r for r in b if _ref_id(r) not in seen]


def catalogue_names(conn: Connection) -> list[tuple[str, str, str]]:
    """(card_id, name, issuer) for the catalogue plus the seed list."""
    out = list(triage.seed_cards())
    out += [(row.id, row.name, row.issuer) for row in store.all_cards(conn)]
    return out


def _known_card(lead: Lead, known: dict[str, str], catalogue: list[tuple[str, str, str]]) -> str | None:
    if lead.key in known:
        return known[lead.key]
    return next((cid for cid, name, issuer in catalogue
                 if triage.same_launch(issuer, name, name, lead.issuer, lead.card_name, lead.card_name)), None)


def _existing_row(c: Connection, lead: Lead):
    """The candidate from an earlier sweep for this launch: same key, or the same launch
    under another wording."""
    row = c.execute(select(launch_candidate).where(launch_candidate.c.dedupe_key == lead.key)).first()
    if row is not None:
        return row
    for r in c.execute(select(launch_candidate)).all():
        if r.issuer and triage.same_launch(r.issuer, r.name, r.summary or "", lead.issuer, lead.card_name, lead.summary):
            return r
    return None


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


def _process(lead: Lead, known: dict[str, str], catalogue: list[tuple[str, str, str]] | None = None) -> Outcome:
    catalogue = catalogue or []
    with engine().begin() as c:
        row = _existing_row(c, lead)
    if row is not None and row.status != "speculative":
        with engine().begin() as c:
            c.execute(update(launch_candidate).where(launch_candidate.c.id == row.id).values(refs=_union(row.refs, lead.refs)))
        return Outcome(lead.key, row.name, row.issuer, row.status, row.card_id, row.summary, "seen")
    known_id = _known_card(lead, known, catalogue) if row is None else None
    if known_id:
        summary = f"Already in the catalogue as {known_id}."
        with engine().begin() as c:
            c.execute(insert(launch_candidate).values(
                dedupe_key=lead.key, name=lead.card_name, issuer=lead.issuer, card_id=known_id, status="known",
                refs=lead.refs, summary=summary))
        return Outcome(lead.key, lead.card_name, lead.issuer, "known", known_id, summary, "new")
    variant = triage.variant_family(lead.issuer, lead.card_name, catalogue)
    prefix = f"New variant of {variant[1]} (the catalogue has {variant[0]} from another issuer). " if variant else ""

    prep = _prepare(lead)
    refs = _union(_union(row.refs if row is not None else [], lead.refs), prep.refs)
    # One transaction per card: the profile, the candidate row and the outbox message
    # commit together, and one bad card cannot roll back the others.
    with engine().begin() as c:
        status, card_id, reason = "speculative", None, prep.reason
        result = None
        if prep.extraction is not None:
            # Savepoint: a card joins the catalogue only if at least one fact publishes;
            # otherwise its empty card row and events are undone.
            sp = c.begin_nested()
            result = profile_card(prep.extraction, origin="launch_radar", conn=c)
            if any(f.outcome in PUBLISHED for f in result.fields):
                sp.commit()
                status, card_id = "profiled", prep.extraction.id
            else:
                sp.rollback()
                reason = f"official page found but no field passed the quote check ({result.summary()})"
        if status == "profiled":
            summary = prefix + _profiled_summary(result)
        else:
            summary = f"{prefix}Reported, not confirmed by the bank: {reason}. {lead.summary}".strip()
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
        # Before reading the catalogue, so an empty card from an older sweep isn't "known".
        prune_empty_cards(c)
        known = known_keys(c)
        catalogue = catalogue_names(c)
    covered = {triage.issuer_slug(issuer) for _, _, issuer in catalogue}
    for lead in _merge([lead for w in workers for lead in w.leads], covered).values():
        report.outcomes.append(_process(lead, known, catalogue))
    with engine().begin() as c:
        detect_variants(c)
        detect_closed(c)
    return report


def prune_empty_cards(conn: Connection) -> list[str]:
    """Remove catalogue cards Launch Radar added that have no published fact (left by
    sweeps before the savepoint above), with their events and speculation."""
    from cc_smith.db import card, card_field, knowledge_event, speculation

    removed = []
    for row in conn.execute(select(card.c.id).where(card.c.origin == "launch_radar")).all():
        published = conn.execute(select(card_field.c.id).where(
            card_field.c.card_id == row.id, card_field.c.status == "published")).first()
        if published is None:
            for t in (card_field, speculation, knowledge_event):
                conn.execute(t.delete().where(t.c.card_id == row.id))
            conn.execute(card.delete().where(card.c.id == row.id))
            removed.append(row.id)
    return removed
