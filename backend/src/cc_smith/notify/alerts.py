"""Owner change alerts (DR-12). Every knowledge.changed event becomes an alert with its
refs; delivery for the hackathon is the owner_alert table plus a log file."""

import json

from sqlalchemy import Connection, func, insert, select

from cc_smith.config import settings
from cc_smith.db import holding, knowledge_event, owner_alert
from cc_smith.ops.outbox import consumer


@consumer("knowledge.changed")
def on_knowledge_changed(conn: Connection, msg: dict) -> None:
    ev = conn.execute(select(knowledge_event).where(knowledge_event.c.id == msg["event_id"])).first()
    if ev is None or conn.execute(select(owner_alert.c.id).where(owner_alert.c.event_id == ev.id)).first():
        return
    holders = conn.execute(select(func.count()).select_from(holding).where(holding.c.card_id == ev.card_id)).scalar_one()
    payload = {
        "card_id": ev.card_id,
        "field": ev.field,
        "event_type": ev.event_type,
        "tier": ev.tier,
        "old": ev.old,
        "new": ev.new,
        "refs": [{k: r.get(k) for k in ("url", "quote", "evidence_id", "fetched_at", "match", "search_id", "official", "reason") if k in r} for r in (ev.refs or [])],
        "large_change": ev.large_change,
        "holders": holders,
        "at": ev.created_at.isoformat(),
    }
    conn.execute(insert(owner_alert).values(event_id=ev.id, payload=payload))
    settings.alerts_log.parent.mkdir(parents=True, exist_ok=True)
    with settings.alerts_log.open("a") as f:
        f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
