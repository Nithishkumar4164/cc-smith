"""Background jobs (DR-7 hackathon stage: plain step functions, a run_state table and
APScheduler). Each job records start, finish, status and a detail blob in run_state."""

import json
import traceback
from collections.abc import Callable
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import insert, select, update

from cc_smith.db import credit_ledger, engine, launch_candidate, now, run_state
from cc_smith.knowledge import store
from cc_smith.ops import outbox
from cc_smith.signals.launch_radar import run_sweep

JOBS = {
    "launch_radar": {"trigger": "cron", "day_of_week": "mon", "hour": 2, "minute": 30},  # 08:00 IST
    "speculation_expiry": {"trigger": "cron", "hour": 21, "minute": 0},  # 02:30 IST
    "outbox_drain": {"trigger": "interval", "minutes": 1},
}


def _set(job: str, **values) -> None:
    with engine().begin() as c:
        if c.execute(select(run_state.c.job).where(run_state.c.job == job)).first():
            c.execute(update(run_state).where(run_state.c.job == job).values(**values))
        else:
            c.execute(insert(run_state).values(job=job, **values))


def tracked(job: str, fn: Callable[[], dict]) -> dict:
    _set(job, last_started=now(), status="running")
    try:
        detail = fn()
    except Exception as e:
        _set(job, last_finished=now(), status="failed", detail={"error": repr(e)[:2000], "trace": traceback.format_exc()[-4000:]})
        raise
    _set(job, last_finished=now(), status="ok", detail=detail)
    return detail


def launch_radar_job(as_of: date | None = None) -> dict:
    report = run_sweep(as_of)
    detail = report.detail()
    detail["delivered"] = outbox.drain()
    return detail


def speculation_expiry_job() -> dict:
    with engine().begin() as c:
        n = store.expire_speculation(c)
    return {"expired": n}


def outbox_drain_job() -> dict:
    return {"delivered": outbox.drain()}


def build_scheduler() -> BackgroundScheduler:
    import cc_smith.notify.alerts  # noqa: F401  registers outbox consumers

    sched = BackgroundScheduler(timezone="UTC")
    fns = {"launch_radar": launch_radar_job, "speculation_expiry": speculation_expiry_job, "outbox_drain": outbox_drain_job}
    for job, spec in JOBS.items():
        spec = dict(spec)
        trigger = spec.pop("trigger")
        sched.add_job(tracked, trigger, args=[job, fns[job]], id=job, coalesce=True, max_instances=1, replace_existing=True, **spec)
    return sched


def run_radar_cli(as_of: str | None = None) -> int:
    """`uv run cc-smith radar [--as-of YYYY-MM-DD]`: one Launch Radar sweep, printed.
    Returns a process exit code."""
    import cc_smith.notify.alerts  # noqa: F401

    when = date.fromisoformat(as_of) if as_of else None
    try:
        detail = tracked("launch_radar", lambda: launch_radar_job(when))
    except Exception as e:  # noqa: BLE001
        print(f"launch radar failed: {e!r}")
        return 1
    print(f"launch radar sweep as of {detail['as_of']}")
    for w in detail["workers"]:
        print(f"  {w['worker']:32s} searches={w['searches']} seen={w['seen']} leads={w['leads']} dropped={w['dropped']}")
        for s in w["skipped"]:
            print(f"    skipped: {s}")
    with engine().begin() as c:
        rows = c.execute(select(launch_candidate).order_by(launch_candidate.c.id)).all()
    acted = {o["key"]: o["action"] for o in detail["outcomes"]}
    for r in rows:
        print(f"  [{r.status:11s}] {r.name} ({r.issuer}) card_id={r.card_id or '-'} {acted.get(r.dedupe_key, 'not seen this sweep')}")
        print(f"      {r.summary}")
    print(f"outbox delivered {detail['delivered']}")
    print(json.dumps({"credits": _credits()}))
    return 0


def _credits() -> dict:
    with engine().begin() as c:
        rows = c.execute(select(credit_ledger.c.flow, credit_ledger.c.cached)).all()
    out: dict[str, dict[str, int]] = {}
    for flow, cached in rows:
        f = out.setdefault(flow, {"live": 0, "cached": 0})
        f["cached" if cached else "live"] += 1
    return out
