#!/usr/bin/env bash
# Re-records the storybook scenario user's responses from a live backend.
#   tool/record_storybook.sh [http://127.0.0.1:8001] [test/storybook/fixtures]
# Scenario: HDFC Millennia on a shared "HDFC" limit (₹2,00,000, ₹70,000 owed) and
# HSBC Live+ (₹1,50,000 limit, ₹20,000 owed, first year free until 2026-11-15);
# Swiggy/online-heavy spends; an ₹11,000 BigBasket payment logged on Live+.
set -euo pipefail
B=${1:-http://127.0.0.1:8001}
OUT=${2:-test/storybook/fixtures}
mkdir -p "$OUT"
J='Content-Type: application/json'
UID_=$(curl -sf -XPOST "$B/users" | python3 -c 'import json,sys;print(json.load(sys.stdin)["user_id"])')
H="X-User-Id: $UID_"
echo "$UID_" > "$OUT/user_id.txt"
put() { curl -sf -X"$1" "$B$2" -H "$H" -H "$J" ${3:+-d "$3"}; }

put PUT /me/profile '{"flags":[],"reward_preference":"any"}' > /dev/null
put PUT /me/pools '[{"id":"hdfc","name":"HDFC shared","limit_paise":20000000}]' > /dev/null
put PUT /me/holdings '[
  {"card_id":"hdfc_millennia","pool_id":"hdfc","balance_paise":7000000,"statement_day":5},
  {"card_id":"hsbc_live_plus","credit_limit_paise":15000000,"balance_paise":2000000,"fee_status":"fyf","fyf_until":"2026-11-15"}]' > /dev/null
put PUT /me/spends '{"dining":900000,"swiggy":600000,"zomato":200000,"online":1500000,"amazon":600000,"flipkart":400000,
  "grocery":1000000,"travel":800000,"fuel":300000,"utilities":400000,"other":1000000}' > "$OUT/me.json"
put POST /pay/confirm '{"card_id":"hsbc_live_plus","merchant":"BigBasket","amount_paise":1100000,"idempotency_key":"storybook-bigbasket"}' > /dev/null

curl -sf "$B/meta" > "$OUT/meta.json"
curl -sf "$B/cards" > "$OUT/cards.json"
curl -sf "$B/cards/hdfc_millennia" > "$OUT/card_detail.json"
curl -sf "$B/ops/changes?limit=40" > "$OUT/changes.json"
curl -sf "$B/launches" -H "$H" > "$OUT/launches.json"
put GET /me > "$OUT/me.json"
put GET /me/credit > "$OUT/credit.json"
put GET /me/notices > "$OUT/notices.json"
put POST /finder '{"max_new":3}' > "$OUT/finder.json"
put POST /pay '{"merchant":"Swiggy","amount_paise":120000}' > "$OUT/pay_swiggy.json"
put POST /pay '{"merchant":"myntra.com","amount_paise":800000}' > "$OUT/pay_offer.json"
put POST /pay '{"merchant":"BPCL","amount_paise":200000}' > "$OUT/pay_fuel.json"
put POST /pay '{"merchant":"MakeMyTrip","amount_paise":14000000}' > "$OUT/pay_big.json"
put GET /me/transactions > "$OUT/transactions.json"
echo "recorded user $UID_ into $OUT"
