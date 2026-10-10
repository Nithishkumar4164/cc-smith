"""knowledge module: the only writer of card, card_field, speculation and knowledge_event."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection, and_, func, insert, select, update

from cc_smith.db import card, card_field, knowledge_event, now, speculation
from cc_smith.knowledge.schema import FIELDS, CardProfile
from cc_smith.ops import outbox

SPECULATION_TTL = timedelta(days=60)


def ensure_card(conn: Connection, card_id: str, name: str, issuer: str, status: str = "active", origin: str = "seed") -> bool:
    if conn.execute(select(card.c.id).where(card.c.id == card_id)).first():
        return False
    conn.execute(insert(card).values(id=card_id, name=name, issuer=issuer, status=status, origin=origin))
    _event(conn, card_id, None, "card_added", None, None, {"status": status}, [], False)
    return True


def set_status(conn: Connection, card_id: str, status: str) -> None:
    conn.execute(update(card).where(card.c.id == card_id).values(status=status))


def current(conn: Connection, card_id: str, field: str):
    return conn.execute(
        select(card_field).where(and_(card_field.c.card_id == card_id, card_field.c.field == field, card_field.c.status == "published"))
    ).first()


def _event(conn, card_id, field, event_type, tier, old, new, refs, large) -> int:
    eid = conn.execute(insert(knowledge_event).values(
        card_id=card_id, field=field, event_type=event_type, tier=tier, old=old, new=new, refs=refs, large_change=large,
    )).inserted_primary_key[0]
    if event_type != "as_of_bumped":
        outbox.publish(conn, "knowledge.changed", f"event:{eid}", {"event_id": eid, "card_id": card_id})
    return eid


def publish_fact(conn: Connection, card_id: str, field: str, value, refs: list[dict], large: bool, effective_from: datetime | None = None) -> str:
    """Returns 'unchanged' (as_of bumped), 'published' or 'first'."""
    ts = now()
    cur = current(conn, card_id, field)
    if cur is not None and cur.value == value:
        conn.execute(update(card_field).where(card_field.c.id == cur.id).values(as_of=ts, refs=refs))
        _event(conn, card_id, field, "as_of_bumped", "fact", None, None, refs, False)
        return "unchanged"
    version = 1
    if cur is not None:
        conn.execute(update(card_field).where(card_field.c.id == cur.id).values(status="superseded"))
        version = cur.version + 1
    conn.execute(insert(card_field).values(
        card_id=card_id, field=field, version=version, value=value, refs=refs, status="published",
        as_of=ts, effective_from=effective_from or ts,
    ))
    _event(conn, card_id, field, "published", "fact", cur.value if cur else None, value, refs, large)
    outbox.publish(conn, "card.version_published", f"{card_id}:{field}:{version}", {"card_id": card_id, "field": field, "version": version})
    # A fact from an official quote settles any open speculation on the same field.
    for s in conn.execute(select(speculation).where(and_(
        speculation.c.card_id == card_id, speculation.c.field == field, speculation.c.status == "open",
    ))).all():
        status = "promoted" if s.value == value else "contradicted"
        conn.execute(update(speculation).where(speculation.c.id == s.id).values(status=status))
        _event(conn, card_id, field, status, "speculation", s.value, value, refs, False)
    return "first" if cur is None else "published"


def add_speculation(conn: Connection, card_id: str, field: str, value, refs: list[dict], origin: str, reason: str) -> int:
    existing = conn.execute(select(speculation.c.id, speculation.c.value).where(and_(
        speculation.c.card_id == card_id, speculation.c.field == field, speculation.c.status == "open",
    ))).all()
    for s in existing:
        if s.value == value:
            return s.id
    sid = conn.execute(insert(speculation).values(
        card_id=card_id, field=field, value=value, refs=refs, origin=origin, reason=reason,
        expires_at=now() + SPECULATION_TTL,
    )).inserted_primary_key[0]
    _event(conn, card_id, field, "speculation_added", "speculation", None, value, refs, False)
    return sid


def expire_speculation(conn: Connection, at: datetime | None = None) -> int:
    at = at or now()
    rows = conn.execute(select(speculation).where(and_(speculation.c.status == "open", speculation.c.expires_at <= at))).all()
    for s in rows:
        conn.execute(update(speculation).where(speculation.c.id == s.id).values(status="expired"))
        _event(conn, s.card_id, s.field, "expired", "speculation", s.value, None, s.refs, False)
    return len(rows)


def rollback(conn: Connection, card_id: str, field: str, reason: str = "manual") -> bool:
    cur = current(conn, card_id, field)
    if cur is None:
        return False
    prev = conn.execute(select(card_field).where(and_(
        card_field.c.card_id == card_id, card_field.c.field == field, card_field.c.version < cur.version,
        card_field.c.status == "superseded",
    )).order_by(card_field.c.version.desc())).first()
    conn.execute(update(card_field).where(card_field.c.id == cur.id).values(status="rolled_back"))
    if prev is not None:
        conn.execute(update(card_field).where(card_field.c.id == prev.id).values(status="published"))
    _event(conn, card_id, field, "rolled_back", "fact", cur.value, prev.value if prev else None, [{"reason": reason}], False)
    outbox.publish(conn, "card.version_published", f"{card_id}:{field}:rollback:{cur.version}", {"card_id": card_id, "field": field})
    return True


def profile(conn: Connection, card_id: str) -> tuple[CardProfile, dict[str, dict]] | None:
    """The published profile plus per-field provenance {field: {as_of, refs, version}}."""
    row = conn.execute(select(card).where(card.c.id == card_id)).first()
    if row is None:
        return None
    body: dict = {"id": row.id, "name": row.name, "issuer": row.issuer}
    meta: dict[str, dict] = {}
    for f in conn.execute(select(card_field).where(and_(card_field.c.card_id == card_id, card_field.c.status == "published"))).all():
        meta[f.field] = {"as_of": f.as_of.replace(tzinfo=UTC).isoformat() if f.as_of.tzinfo is None else f.as_of.isoformat(), "refs": f.refs, "version": f.version}
        if f.field == "min_txn":
            body["min_txn_paise"] = f.value["min_txn_paise"]
            body["min_txn_src"] = f.value["min_txn_src"]
        else:
            body[f.field] = f.value
    # Rules whose caps were not published cannot be evaluated safely.
    cap_ids = {c["id"] for c in body.get("caps", [])}
    if any(cid not in cap_ids for r in body.get("earn_rules", []) for cid in r.get("cap_ids", [])):
        body.pop("earn_rules", None)
        meta.setdefault("earn_rules", {})["blocked"] = "caps not confirmed"
    # Exclusions that exist but failed the checks would let the card "earn" on fuel or rent;
    # until they are confirmed the card is not scored (Scapia: issuer copy behind a bot wall).
    if "exclusions" not in body and conn.execute(select(speculation.c.id).where(and_(
        speculation.c.card_id == card_id, speculation.c.field == "exclusions", speculation.c.status == "open",
    ))).first():
        body.pop("earn_rules", None)
        meta.setdefault("earn_rules", {})["blocked"] = "exclusions not confirmed"
    return CardProfile.model_validate(body), meta


def all_cards(conn: Connection):
    return conn.execute(select(card).order_by(card.c.issuer, card.c.name)).all()


def open_speculation(conn: Connection, card_id: str | None = None):
    q = select(speculation).where(speculation.c.status == "open")
    if card_id:
        q = q.where(speculation.c.card_id == card_id)
    return conn.execute(q.order_by(speculation.c.opened_at.desc())).all()


def events(conn: Connection, card_id: str | None = None, limit: int = 200):
    q = select(knowledge_event).where(knowledge_event.c.event_type != "as_of_bumped")
    if card_id:
        q = q.where(knowledge_event.c.card_id == card_id)
    return conn.execute(q.order_by(knowledge_event.c.id.desc()).limit(limit)).all()


def field_names() -> tuple[str, ...]:
    return FIELDS


def count_published(conn: Connection) -> int:
    return conn.execute(select(func.count()).select_from(card_field).where(card_field.c.status == "published")).scalar_one()
