"""cc-smith command line: seed the catalogue from extraction fixtures, run jobs, serve."""

import argparse
import json

from cc_smith.config import settings


def seed(refresh: bool) -> None:
    import cc_smith.notify.alerts  # noqa: F401
    from cc_smith.knowledge.pipeline import (
        load_extraction,
        profile_card,
    )
    from cc_smith.ops.outbox import drain

    for path in sorted((settings.fixtures_dir / "extractions").glob("*.json")):
        r = profile_card(load_extraction(path), refresh=refresh)
        spec = [f"{f.field}: {'; '.join(f.reasons)[:160]}" for f in r.fields if f.outcome == "speculation"]
        print(f"{r.card_id:28s} {json.dumps(r.summary())}")
        for s in spec:
            print(f"    speculation {s}")
    from cc_smith.db import engine
    from cc_smith.knowledge import offers

    for path in sorted((settings.fixtures_dir / "offers").glob("*.json")):
        with engine().begin() as c:
            print(f"offers {path.name}: {offers.load(c, path, refresh=refresh)}")
    print(f"outbox delivered {drain()}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="cc-smith")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seed", help="profile every card in fixtures/extractions")
    s.add_argument("--refresh", action="store_true", help="re-fetch official pages (needs network)")
    r = sub.add_parser("radar", help="one Launch Radar sweep")
    r.add_argument("--as-of", help="YYYY-MM-DD; replay fixtures were recorded on 2026-10-07")
    v = sub.add_parser("serve")
    v.add_argument("--host", default="127.0.0.1")
    v.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    if args.cmd == "seed":
        seed(args.refresh)
    elif args.cmd == "radar":
        from cc_smith.signals.scheduler import run_radar_cli

        raise SystemExit(run_radar_cli(args.as_of))
    elif args.cmd == "serve":
        import uvicorn

        uvicorn.run("cc_smith.api.main:app", host=args.host, port=args.port)
