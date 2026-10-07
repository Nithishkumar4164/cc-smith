# cc-smith — Consolidated feature list

Built from three inputs:

1. `docs/ideation.md` — the base ideation (knowledge base + engine + agent + ledger, preference-driven rankings, companion app, action centre, replan).
2. The cc-smith Flow Map artifact — four flows (recommend, pay-time pick, eligibility action plan, cap tracker, keep/convert/close at renewal, new-launch heads-up) and the card-profile sourcing rules.
3. Community pain-point sweep (Oct 2026) — TechnoFino forum (~36 threads read in full, ~40 more from search snippets) and r/CreditCardsIndia (all ~56.9k posts from Oct 2025–Oct 2026 via an archive API; comment trees on 55 high-signal posts). Frequency labels below come from that sweep.

Priority: **P0** = must exist for the product to be worth opening; **P1** = first year; **P2** = later. Roadmap step refers to `docs/ideation.md` → Roadmap.

---

## Pain points → features (the map)

| # | Pain point (merged across both communities) | Frequency | Features |
|---|---|---|---|
| 1 | "Which card should I get / keep / close / use for this?" — thousands of profile-dump posts; beginners, self-employed and students worst served | Very common | B1 B2 B3 B4 B5 D1 |
| 2 | Rewards, cashback and milestones not credited; MCC mis-tagging, caps, exclusions, rounding and refund reversals discovered only in the statement | Very common | A2 D2 E3 E4 |
| 3 | Devaluations and silent T&C changes; users learn the impact from the forum, not the bank | Very common | A6 A7 F6 G2 |
| 4 | Losing track of milestone, waiver, welcome-benefit and lounge-spend thresholds across many cards; Excel is the state of the art | Very common | E2 E5 |
| 5 | CIBIL opacity: hard enquiries from "pre-approved" offers and marketplaces, unexplained drops, misreporting | Very common | C2 C3 E6 |
| 6 | Rejections without reason, repeated re-applications, VKYC / pincode failures, salary-account gatekeeping | Very common | C1 C3 C4 |
| 7 | Fees charged despite waiver met or despite "lifetime free"; mis-selling that can't be proven | Very common | A4 C5 F2 F7 |
| 8 | Closure friction: cards not closed for months, paise residuals, fees and CIBIL hits after closure | Very common | F3 |
| 9 | Redemption paralysis: lakhs of points with no clear best use; per-redemption fees; portal confusion; partner removals | Very common | A5 G1 G2 |
| 10 | Multi-card overload: wrong card at checkout, scattered due dates and statements, missed payments and interest shocks | Very common | D1 E1 F1 |
| 11 | RuPay-on-UPI: small-ticket rounding to zero, inconsistent per-card rules, merchants switching off acceptance | Very common | A2 D3 H2 |
| 12 | Lounge access as a black box: spend criteria with odd quarters, lounge/POS-specific eligibility, denied at the desk, Priority Pass confusion | Very common | A3 E2 H2 |
| 13 | Customer care can't answer; only PNO / RBI Ombudsman works; every bank has a different escalation path | Very common | F5 |
| 14 | Offers not applied (co-brand exclusions, targeted eligibility), vouchers arriving 80–90 days late or never, "offer processing fees" | Common | D4 E4 |
| 15 | Forex markup vs DCC confusion; markup on INR-billed foreign merchants; surcharges above the OTP amount | Common | D5 D6 |
| 16 | Influencer / affiliate-biased and stale information; even bank channels contradict each other; LLMs hallucinate rates | Common | A1 A6 H1 |

---

## A. Card knowledge base (foundation)

| ID | Feature | Pri | Step |
|---|---|---|---|
| A1 | **Versioned card profiles, one per variant.** Every field carries a source URL and an as-of date. No source → the field stays empty and is excluded from the maths ("can't assess yet", never a guess). Pending changes (announced devaluations) are applied before scoring. | P0 | 1 |
| A2 | **Earn rules at the resolution banks actually apply.** MCC-level earn rates and exclusions; caps with their reset basis (statement cycle vs calendar month vs quarter with non-calendar dates); minimum transaction amounts; per-transaction rounding (so a 1.5% card that floors to ₹0 under ₹67 is scored honestly); per-channel rules (UPI, own-app-only rates, wallet loads, payment apps); "once per cycle" offer rules; refund-reversal behaviour. | P0 | 1 |
| A3 | **Perks as typed line items.** Lounge: count, domestic/international, guest, spend criteria and its period, which lounge network / POS it works on, add-on card coverage. Forex markup. Fuel surcharge waiver. Memberships. Insurance. Welcome benefits (year-one only). | P0 | 1 |
| A4 | **Fee and waiver rules in full.** Fee, waiver threshold, what counts toward it (refunds, excluded categories, statement vs posted spend), whether the bank charges-then-reverses, first-year-free vs lifetime-free variants, add-on card fees, surcharges (rent, utilities, fuel, government, wallet). | P0 | 1 |
| A5 | **Redemption catalogue per card.** Routes (portal, vouchers, transfer partners, statement credit), ₹ per point by route, redemption fees and GST, per-month redemption caps, minimum thresholds, point expiry rules. | P1 | 3 |
| A6 | **Change pipeline.** Scrape issuer pages and MITC/T&C documents; LLM extracts into the schema; quote check against the stored page; a value with an official quote publishes automatically as a new version, anything else is speculation and never overwrites a fact; weekly re-check rolls back facts that don't reproduce; owner alerted on every change (plan DR-12, no human review). Once published, every holder's trackers and playbook re-run. Public changelog per card. | P1 | 2 |
| A7 | **News and devaluation ingestion.** Issuer notices, community devaluation threads, partner-programme changes (airline/hotel ratios). Each item is tied to card IDs and an effective date so impact can be computed per user. | P1 | 3 |
| A8 | **User-reported corrections** with evidence (statement line, bank email) become speculation and trigger an immediate re-fetch of the official page; the reporter sees the outcome. | P1 | 2 |

## B. Recommend

| ID | Feature | Pri | Step |
|---|---|---|---|
| B1 | **Preference-driven portfolio recommendation.** Spend profile + preference profile (hard constraints + valuations) → ranked 1–3 card portfolios with per-line-item ₹ breakdown; marginal gain measured against the user's existing best card per category; duplicates of a held card score low. | P0 | 1 |
| B2 | **"Should I get X?"** — named-card assessment against the user's own numbers, including pending devaluations. | P0 | 1 |
| B3 | **Portfolio review: keep / close / replace** across all held cards, with the ₹ each card earned net of fee and what the rest of the stack would earn instead. | P1 | 2 |
| B4 | **Beginner and hard-profile paths.** First card, student, self-employed, no salary account: FD-backed, card-to-card and relationship-based routes shown as first-class options rather than rejections. | P1 | 2 |
| B5 | **Reality check on headline rates.** For every recommended card, show effective rate after caps, exclusions, minimums and rounding on the user's actual spend pattern — the number the brochure doesn't print. | P0 | 1 |
| B6 | **Hard categories answered honestly.** Rent, utilities, insurance, fuel, jewellery, wallet loads, tax, education: if nothing earns, say so and show the lowest-surcharge option and whether it counts toward milestones. | P0 | 1 |
| B7 | **Ranking independence.** No affiliate, referral or issuer money is taken (owner, 2026-10-06/07); breakdown shown for every rank. | P0 | 1 |

## C. Acquire

| ID | Feature | Pri | Step |
|---|---|---|---|
| C1 | **Eligibility check + action plan.** Income, age, relationship, score signals; a failed rule becomes steps: pre-approved route, card-to-card, FD-backed then upgrade in 6–12 months, open the relationship account, bring utilisation under 30%, wait N months after the last enquiry. Re-check when steps are done. | P1 | 2 |
| C2 | **Enquiry hygiene.** Hard-enquiry log; warn before applying (spacing, utilisation, recent rejections); flag "pre-approved" channels and marketplaces known to hard-pull and then reject. | P1 | 2 |
| C3 | **Application tracker and rejection intelligence.** Track applications, VKYC, pincode serviceability; crowd-sourced rejection reasons by bank and card (co-brand conflicts, "internal policy", enquiry count); suggested re-apply timing. | P2 | 5 |
| C4 | **Upgrade / downgrade paths** within a bank, with points carry-over rules and the income thresholds reps actually apply. | P2 | 5 |
| C5 | **LTF proof vault.** At onboarding, prompt for and store the written LTF / fee-waiver confirmation (email, screenshot); nudge to get it in writing before activation. Used in F7 disputes. | P1 | 2 |

## D. Use (pay-time)

| ID | Feature | Pri | Step |
|---|---|---|---|
| D1 | **Which card now.** Merchant + amount + channel → the card with the highest marginal value, in about a second from precomputed data: cap state, milestone and waiver proximity, live offers, channel rules. Shows the margin over the next best. Entry points: type it, scan the merchant QR, share a checkout URL. | P0 | 1 (typed) / 3 (scan) |
| D2 | **Merchant → MCC map.** Seeded from known merchants; learned from users' own statements; crowd-sourced per acquirer; user corrections; "this merchant is known to mis-tag on bank X" warnings before paying. | P1 | 3 |
| D3 | **UPI-specific logic.** Minimum amounts, rounding, own-app-only rates, which UPI app to pay from, P2M vs P2P, and merchant acceptance reports for RuPay credit. | P1 | 3 |
| D4 | **Online checkout assist.** Browser extension recognises the domain; applies co-brand exclusions to sale offers; nets out "offer processing" and convenience fees so the discount shown is the real one. | P2 | 5 |
| D5 | **Forex and DCC guidance.** Which card for international and INR-billed foreign merchants; always-pay-in-local-currency reminder; expected markup shown before paying. | P1 | 3 |
| D6 | **Surcharge awareness.** Fuel, rent, tax, government and wallet surcharges shown up front, including when the charged amount will exceed the OTP amount. | P1 | 3 |
| D7 | ~~Effective price across stores~~ — **dropped** (owner decision, 2026-10-07). | — | — |
| D8 | **UPI hand-off.** From the scan, open the UPI app with payee prefilled (Android). | P1 | 3 |

## E. Track (ledger)

| ID | Feature | Pri | Step |
|---|---|---|---|
| E1 | **Transaction ledger.** Input ladder: manual category entry → statement upload (PDF/CSV) → notification capture (Android) → email → Account Aggregator if viable. Estimated entries are replaced by real ones. | P0 (manual) / P1 (statement) / P1 (notification) | 1 / 2 / 3 |
| E2 | **Threshold trackers.** Caps, milestones, fee-waiver spend, welcome-benefit spend, lounge spend criteria — with cycle-correct resets (statement date, odd quarters) and "₹X to go, N days left" nudges. | P1 | 3 |
| E3 | **Expected-vs-actual rewards reconciliation.** The engine computes what every transaction *should* earn; the statement says what it did. Flags missing points, wrong-MCC postings, cap mis-application, refund reversals that recomputed wrongly, vouchers past their expected credit date. Produces evidence for F5. | P1 | 3 |
| E4 | **Pending benefits ledger.** Vouchers, offers and milestone credits with expected credit dates (e.g. 60–90 days) and alerts when overdue. | P1 | 3 |
| E5 | **Points balances and expiry.** Per card, with expiry alerts and redemption nudges before points lapse. | P1 | 3 |
| E6 | **Credit hygiene view.** Utilisation per card and total, issuer reporting dates, enquiry log, oldest-card age — the inputs that drive score, shown plainly. | P1 | 3 |
| E7 | **Spend summaries.** Per card, per category, per FY; forex converted to INR. | P1 | 2 |

## F. Manage (action centre)

| ID | Feature | Pri | Step |
|---|---|---|---|
| F1 | **Due dates and payments.** All cards' due dates and amounts; pay-by alerts; warning that a short payment is charged interest on the full statement; autodebit setup guidance per issuer; caution on third-party bill-pay apps and a reminder to verify at the bank side. | P1 | 2 |
| F2 | **Keep / convert / close at renewal.** ~45 days before the fee date: rewards earned vs fee, what the rest of the stack would earn instead, waiver on track or not, LTF/downgrade conversion available, credit-score side effects (utilisation jump, oldest card). Convert-to-LTF preferred over close. Retention-call script. | P1 | 3 |
| F3 | **Closure workflow.** Checklist: zero balance including paise, pending cashback reversals, NOC in writing, account-level not card-level closure, verify on the credit report after 45 days; follow-up reminders until confirmed. | P1 | 3 |
| F4 | **Replan on change.** Devaluation or rule change → re-run the playbook on the user's ledger → diff → recap of what to move where and the ₹ impact → new card suggested only if value is still lost. | P1 | 3 |
| F5 | **Escalation helper.** Per-bank ladder (customer care → nodal/PNO → RBI Ombudsman via CMS) with contacts and timelines; drafts the complaint from ledger evidence (transactions, MCCs, expected vs actual, screenshots from C5); tracks the case. | P1 | 3 |
| F6 | **New-launch heads-up** only when a new card beats the user's stack by more than a threshold. | P2 | 4 |
| F7 | **Promise and evidence vault.** Written confirmations, chat screenshots, offer T&C snapshots at the time of the offer — the proof users lack in mis-selling disputes. | P1 | 2 |

## G. Redeem

| ID | Feature | Pri | Step |
|---|---|---|---|
| G1 | **Redemption optimiser.** For a given balance: rank routes by net ₹ per point after fees, GST, caps and minimums; account for expiry; "redeem now vs wait" when a partner devaluation is announced. | P1 | 3 |
| G2 | **Partner-programme tracking.** Transfer ratios and partner removals with impact on stored points; alerts. | P2 | 4 |

## H. Trust and community

| ID | Feature | Pri | Step |
|---|---|---|---|
| H1 | **Provenance everywhere.** Source and as-of date on every fact shown; changelog per card; corrections visible. | P0 | 1 |
| H2 | **Community signals.** Acceptance reports (RuPay credit on UPI at a merchant), lounge denial reports (lounge, card, date), MCC reports — aggregated and shown at the decision point. | P2 | 4 |
| H3 | **Privacy posture.** DPDP consent and deletion, no card numbers stored, local-first capture where possible, published data map. | P0 | 1 |

---

## What this does not fix

Bank behaviour: rejections without reason, customer-care quality, merchants disabling RuPay credit on UPI, devaluations themselves. The product reduces their cost — earlier warning, evidence in hand, the right escalation path — but should not promise to change them.

## v1 scope (roadmap step 1)

A1–A4, B1, B2, B5, B6, B7, D1 (typed), E1 (manual), H1, H3 — about 30 hand-verified cards.
