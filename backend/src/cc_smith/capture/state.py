"""Per-user, per-source capture state: last sync time, cursor (Gmail historyId) and
small derived details (last statement date per card). Counts come from capture_event."""

from sqlalchemy import Connection, func, insert, select, update

from cc_smith.db import capture_event, capture_state, now

UNSET = object()


def get_state(conn: Connection, uid: str, source: str) -> dict:
    row = conn.execute(select(capture_state).where((capture_state.c.user_id == uid) & (capture_state.c.source == source))).first()
    return dict(row._mapping) if row else {}


def set_state(conn: Connection, uid: str, source: str, cursor=UNSET, detail=UNSET, synced: bool = True) -> None:
    values: dict = {}
    if synced:
        values["last_sync_at"] = now()
    if cursor is not UNSET:
        values["cursor"] = cursor
    if detail is not UNSET:
        values["detail"] = detail
    where = (capture_state.c.user_id == uid) & (capture_state.c.source == source)
    if conn.execute(select(capture_state.c.user_id).where(where)).first():
        if values:
            conn.execute(update(capture_state).where(where).values(**values))
    else:
        conn.execute(insert(capture_state).values(user_id=uid, source=source, **values))


def counts(conn: Connection, uid: str) -> dict[str, dict[str, int]]:
    rows = conn.execute(select(capture_event.c.source, capture_event.c.outcome, func.count()).where(capture_event.c.user_id == uid)
                        .group_by(capture_event.c.source, capture_event.c.outcome)).all()
    out: dict[str, dict[str, int]] = {}
    for source, outcome, n in rows:
        out.setdefault(source, {})[outcome] = n
    return out
