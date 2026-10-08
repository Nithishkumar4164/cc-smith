"""Transactional outbox. Producers insert in the same transaction as their write;
`drain` delivers to in-process consumers, idempotent on (topic, key) per consumer."""

from collections.abc import Callable

from sqlalchemy import Connection, insert, select, update

from cc_smith.db import engine, outbox

TOPICS = {"card.version_published", "launch.published", "txn.recorded", "knowledge.changed", "user.erased"}
MAX_ATTEMPTS = 5

_consumers: dict[str, list[Callable[[Connection, dict], None]]] = {}


def publish(conn: Connection, topic: str, key: str, payload: dict) -> None:
    assert topic in TOPICS, topic
    conn.execute(insert(outbox).values(topic=topic, key=key, payload=payload))


def consumer(topic: str):
    def wrap(fn: Callable[[Connection, dict], None]):
        _consumers.setdefault(topic, []).append(fn)
        return fn
    return wrap


def drain(limit: int = 500) -> int:
    done = 0
    with engine().begin() as conn:
        rows = conn.execute(select(outbox).where(outbox.c.status == "pending").order_by(outbox.c.id).limit(limit)).all()
    for row in rows:
        try:
            with engine().begin() as conn:
                for fn in _consumers.get(row.topic, []):
                    fn(conn, {**row.payload, "_outbox_id": row.id})
                conn.execute(update(outbox).where(outbox.c.id == row.id).values(status="done", attempts=row.attempts + 1))
            done += 1
        except Exception as e:  # noqa: BLE001 - one bad message must not stop the queue
            with engine().begin() as conn:
                attempts = row.attempts + 1
                conn.execute(update(outbox).where(outbox.c.id == row.id).values(
                    attempts=attempts, last_error=repr(e)[:2000], status="dead" if attempts >= MAX_ATTEMPTS else "pending"))
    return done
