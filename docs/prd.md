# cc-smith — Product Requirements Document

Status: draft v1 · Owner: Nithish Kumar G · Date: 2026-10-07

Inputs: owner's feature requirements (2026-10-07), `docs/features.md` (consolidated feature list), `docs/ideation.md`, community research in `docs/research/`. Feature IDs in brackets (e.g. [A1]) refer to `docs/features.md` for traceability. The "effective price across stores" feature (formerly D7) is dropped per owner decision.

---

## 1. Overview

cc-smith is a mobile-first product for Indian credit card holders that answers four questions with the user's own numbers:

1. **Which cards should I hold?** — acquire, keep, close.
2. **Which card do I pay with right now?** — for this merchant, this amount, this channel.
3. **What do I need to do this week?** — fees, milestones, expiring rewards, devaluations.
4. **How do I turn my points into the most value?**

Every answer is computed by a deterministic engine over a versioned, source-attributed card knowledge base. The AI model gathers and explains; it never calculates rewards or asserts a card fact from memory.

### 1.1 Problem

From the community research (TechnoFino, r/CreditCardsIndia; ~57k posts and ~75 threads): users cannot decide which card to get or use, lose rewards to caps/exclusions/MCC mis-tags they discover only in statements, miss milestones and fee waivers for lack of a tracker, learn about devaluations from forums rather than banks, and sit on lakhs of unredeemed points. Existing tools are static comparison tables, affiliate-biased, or stale.

### 1.2 Goals

- G1. A user with a spend profile and preferences gets a ranked, explained, rupee-quantified card portfolio.
- G2. A user with multiple cards gets a one-second, cap-aware, milestone-aware answer at payment time.
- G3. No user misses a fee waiver, milestone, or point expiry that the product knew about.
- G4. Every fact shown carries a source and an as-of date; rankings are never paid for: cc-smith takes no affiliate, referral or issuer money.
- G5. The knowledge base covers the Indian market and absorbs new cards and devaluations through an automated pipeline: official-source facts publish after a quote check; everything else is labelled speculation.

### 1.3 Non-goals

- Moving money (UPI TPAP, payment aggregation, bill payment).
- Changing bank behaviour (rejections, customer care, merchant acceptance). The product reduces their cost; it does not promise to fix them.
- Credit score retrieval from bureaus in v1 (user-entered band; bureau integration evaluated later).
- Price comparison across stores (dropped).

### 1.4 Success metrics (first 12 months)

| Metric | Target |
|---|---|
| Knowledge-base coverage | ≥ 95% of cards held by active users are in the master list |
| Fact freshness | Median age of a rule document's last verification ≤ 30 days |
| Recommendation acceptance | ≥ 30% of users who receive a portfolio recommendation apply for or close a card within 60 days |
| Picker usage | ≥ 3 picker queries per active multi-card user per week |
| Notice effectiveness | ≥ 70% of fee-waiver and milestone notices acted on before deadline |
| Trust | ≥ 90% of displayed facts have a source link; user-reported corrections resolved within 7 days |

---

## 2. Users

| Persona | Description | Primary needs |
|---|---|---|
| **Beginner** | First card or ≤ 2 cards; salaried; confused by forum noise | Which card, whether they will get it, how to apply |
| **Optimiser** | 5–15 cards; tracks in spreadsheets; knows caps exist but loses track | Picker, notice board, trackers, reconciliation |
| **Points player** | Premium cards; transfers to Marriott/Accor/airlines | Redemption optimiser, partner tracking, devaluation alerts |
| **Cashback-first** | Wants simple, no-fee, no-games cards | Honest effective rates, LTF reliability, exclusions |
| **Hard profile** | Student, self-employed, no salary account, thin file | Eligibility paths (FD-backed, card-to-card), likelihood |
| **Owner / operator** | Internal; owns the official-source allow-list and receives change alerts | Change alerts, read-only change feed, speculation list, allow-list, rollback |

---

## 3. Principles

- **P1. Deterministic maths.** All reward, fee, milestone, eligibility and redemption numbers come from the engine over structured rules. The LLM extracts documents into the schema and explains engine output; it is never a source of card facts.
- **P2. Provenance or nothing.** A field with no source and as-of date stays empty and is excluded from calculations ("can't assess yet"). [A1, H1]
- **P3. Facts or speculation, no review queue.** A value becomes a fact only from a verbatim quote on an allow-listed official source that owns the field (issuer, or co-brand partner for partner-controlled fields); it then publishes automatically as a new version. Anything else is speculation: shown labelled "reported, not confirmed by the bank" with its refs, never used in the maths. Differing values never overwrite a fact without an official quote. The owner is alerted on every change; nothing waits for a human. [A6; plan DR-12]
- **P4. Replan before recommend.** When rules change, first re-route within the user's existing stack; recommend a new card only for the remaining gap. [F4]
- **P5. Independence.** cc-smith takes no affiliate, referral or issuer money; every rank shows its breakdown. [B7]
- **P6. Privacy by construction.** No card numbers stored; DPDP consent and deletion; no personal data in extraction prompts or third-party search queries. [H3]
- **P7. User preference decides value.** Cashback vs points, lounges vs fees, simplicity vs maximisation — valuations are the user's, not the brochure's.

---

## 4. Glossary

| Term | Meaning |
|---|---|
| Master list | The canonical set of card products (per variant) in the Indian market held in the knowledge base |
| Rule document | The versioned structured record of a card variant's earn rules, caps, exclusions, perks, fees, milestones, eligibility, compatibility, redemption |
| Variant | A distinct terms-set of a card product (e.g. lifetime-free vs paid, Visa vs RuPay, co-brand editions) |
| MCC | Merchant Category Code set by the acquirer; determines earn/exclusion |
| Cap | Maximum accelerated reward per period (statement cycle, calendar month, quarter) |
| Milestone | A spend threshold within a period that unlocks a benefit |
| Spend-and-time lock | A spend requirement in one period that unlocks a perk in the next (e.g. ₹20k this quarter → lounge next quarter) |
| Ledger | The user's transaction record: estimated (budget) entries and actual (captured) entries |
| Picker | The payment method picker: which card/channel to use for a given payment |
| Notice | A time-bound action item for the user derived from their cards and ledger |
| Route | A redemption path for points (portal, voucher, transfer partner, statement credit) |

---

## 5. Functional requirements

### 5.1 Card Knowledge Base (KB)

The KB is the single source of truth for all card facts, the glossary, the engine and the picker. [A1–A8]

**Master list**

- FR-KB-1. The master list holds every credit card product available in the Indian market, one record per variant. Initial population by research across issuer sites and allow-listed community sources; target ≥ 95% coverage of cards held by active users within 6 months.
- FR-KB-2. Each variant's rule document contains: issuer, network(s), UPI capability, fees (joining, annual, add-on, renewal), fee-waiver rules (threshold, period, what counts, charge-then-reverse behaviour, FYF vs LTF status), earn rules (base rate; accelerated categories by MCC/merchant/channel; caps with reset basis; minimum amounts; per-transaction rounding; once-per-cycle rules; refund reversal behaviour), exclusion categories, milestones (threshold, period, benefit, credit lag), welcome benefits (year-one), perks (lounge domestic/international counts, guest, spend criteria and period, network/POS, add-on coverage; forex markup; fuel surcharge waiver; memberships; insurance; concierge; golf; other), redemption (routes, ₹/point per route, fees + GST, caps, minimums, expiry), eligibility (income, age, relationship, geography), compatibility restrictions, issuer policies (max cards per customer, upgrade/downgrade paths), and source references. [A2–A5]
- FR-KB-3. Every field carries `source_url`, `source_type` (issuer MITC, issuer page, community allow-listed, user correction), `as_of` date and `verified_by`. Fields without a source are stored as unknown and excluded from engine maths. [A1, H1]
- FR-KB-4. Rule documents are versioned with `effective_from` / `effective_to`. Announced future changes are stored as pending versions and applied by the engine at their effective date; recommendations consider pending changes. [A1]
- FR-KB-5. Compatibility restrictions are first-class rules, e.g. "holding only a co-branded card with issuer X blocks core-card issuance", "holding any other issuer-Y card makes card Z ineligible", "one card per co-brand partner". Each restriction has a source. The engine applies them in eligibility and recommendation.
- FR-KB-6. Issuer-level documents (master terms, schedule of charges, MITC) are pulled per issuer, stored as snapshots, and used to populate and re-verify rule documents. [A6]

**Sources and intake**

- FR-KB-7. An allow-list of official sources is maintained by the owner, with every edit versioned and alerted: RBI-regulated issuer domains and co-brand partner domains (e.g. airline, e-commerce, telecom partners that publish card terms), each tagged with the fields it owns. Only these sources can create or change facts. Communities (initially TechnoFino and r/CreditCardsIndia), news, AI Mode and every other source produce speculation.
- FR-KB-8. New-card discovery runs on a schedule against official sources, ads and news (Launch Radar). A discovered card with an official page is profiled and published automatically; variants are merged by issuer + name matching. A card without an official page is listed as a **speculative launch**: not scored and no user notification until an official page promotes it. [A6, A7, F6]
- FR-KB-9. Change pipeline: fetch official documents → LLM extraction into the schema with structured output → quote check (the value's verbatim quote must appear in the stored page) and range checks → pass: new version published with effective dates; fail: stored as speculation → owner alert → affected users' trackers, notices and picker precomputations re-run. A weekly automated re-check re-extracts published facts and rolls back any that do not reproduce. [A6; plan DR-12]
- FR-KB-10. Community-sourced claims become speculation with their refs and trigger an immediate re-fetch of the official source. Speculation is promoted to a fact automatically when an official quote confirms it, closed when an official source contradicts it, and expires after 60 days unconfirmed.
- FR-KB-11. User-reported corrections (with optional evidence: statement line, bank email, screenshot) become speculation with the report as the ref and trigger an immediate re-fetch of the official page. The reporter sees the outcome (promoted, contradicted or expired). [A8]
- FR-KB-12. A public changelog per card lists every published change with date, field, old/new values and source. [H1]

**Unlisted cards**

- FR-KB-13. A user may add a card that is not in the master list by issuer + name (with fuzzy matching against existing variants to prevent duplicates). The card is created as a **custom card** on the user's account: due dates, fees and limits are user-entered; rewards are "can't assess yet" in the engine; the picker excludes it from reward ranking but includes it for due-date and milestone tracking the user enters manually.
- FR-KB-14. Each custom card automatically raises a catalogue request (plan DR-4 user-request route). Requests are prioritised by the number of users holding the unlisted card. When the card's official page is found and the card is published into the master list, the custom card is linked to the master variant and the user is notified that full assessment is available.

### 5.2 Reward valuation model (common knowledge)

- FR-VAL-1. Rewards are modelled as either **cashback** (₹ credited; may carry a redemption fee) or **points** (a currency with multiple redemption routes). The KB stores, per card, every route and its ₹-per-point value, fees, GST, caps, minimums and expiry. [A5]
- FR-VAL-2. Transfer partners (hotel programmes, airline miles, other partner currencies) are modelled with transfer ratios and a **partner-currency value** maintained in the KB with a source and as-of date (e.g. value per hotel point based on published award charts / community-verified redemptions). [G2]
- FR-VAL-3. The user's preference profile records a **points stance**: cash-equivalent only; cash-equivalent plus vouchers; or transfer-partner optimiser (with which partners they actually use). The engine values points at the best route the user has said they would use — never at the brochure's maximum. [P7]
- FR-VAL-4. When comparing a cashback card with a points card, the engine translates points to ₹ using the user's stance and current conversion data, and shows both the cash-equivalent view and the transfer-optimised view with the assumptions stated.
- FR-VAL-5. Valuation inputs (transfer ratios, partner values, voucher denominations) are versioned like all KB facts; a change triggers replan and redemption notices. [G2, F4]

### 5.3 Card Glossary

- FR-GL-1. A browsable, searchable list of all master-list cards with filters: issuer, network, fee band, LTF availability, reward type (cashback/points), key perks (lounge, forex, fuel), co-brand partner, UPI-capable.
- FR-GL-2. Cards are tagged for the signed-in user: **held**, **pre-qualified** (eligibility rules pass on the user's profile), **not eligible** (with the failing rule), **blocked by compatibility** (with the blocking card named).
- FR-GL-3. Card detail page (layout modelled on comparison-site card pages, redesigned for provenance): fees (joining, annual, add-on, renewal, waiver rule), welcome benefit, earn rules with caps/exclusions in plain language, milestones with periods, perks (lounge with spend criteria, forex, fuel, memberships, insurance, concierge, roadside assistance and other unique perks), redemption routes with ₹/point, eligibility, compatibility restrictions, issuer policies, changelog, and the user's own effective rate on their spend profile (if available). [B5]
- FR-GL-4. Every displayed value shows source and as-of date on tap. [H1]
- FR-GL-5. From a card page the user can: add to "held", run "should I get this?" [B2], report a correction [A8], and open the application path [C1].

### 5.4 Spend profile and ledger

How spending is tracked: an input ladder where estimates are replaced by actuals as better sources connect. [E1]

- FR-LD-1. **v1 — Budget entry.** During onboarding the user enters monthly spend by category (dining, food delivery, groceries, online shopping, travel, fuel, utilities, rent, insurance, education, EMI, other) with optional top merchants per category. These become **estimated ledger entries** spread across the month.
- FR-LD-2. **Statement upload.** The user uploads statement PDFs/CSVs (password supported). Transactions are parsed into **actual ledger entries** with merchant string, amount, date, card, and — where present — reward lines. The PDF is deleted after parsing. Actuals replace estimates for the covered period.
- FR-LD-3. **Android notification capture.** With explicit consent, a notification listener reads bank transaction alerts and creates actual entries in near real time. iOS: not available; iOS users rely on FR-LD-1/2/4.
- FR-LD-4. **Email capture** (later): user-authorised parsing of transaction alert emails.
- FR-LD-5. **Account Aggregator** (later, if viable for a non-regulated entity).
- FR-LD-6. Each ledger entry stores its provenance (estimated / statement / notification / email) and resolves to a merchant record and an MCC (actual when known from statement or reward evidence; expected otherwise).
- FR-LD-7. The ledger drives: spend profile for recommendations, cap/milestone/waiver trackers, notices, reconciliation and redemption state.
- FR-LD-8. Spend summaries: per card, per category, per month and FY; foreign currency converted to INR. [E7]

### 5.5 Card Recommendation Engine

Tells the user which cards to acquire and which to close, given their credit profile, spending, held cards, preferences, and bank policies. [B1–B7, C1–C5, F2]

- FR-RE-1. Inputs: spend profile (ledger), held cards, credit score band (user-entered; bureau integration later), income band, age, employment type, bank relationships (savings/salary account, FD, loans), preference profile (hard constraints: max fee, LTF-only, max number of cards, issuers to avoid, must-have perks; valuations: cashback vs points stance, lounge usage, international spend, memberships already paid for).
- FR-RE-2. Output: a ranked set of 1–3 card portfolios with, per card, annual ₹ value broken down by line item (category earn after caps/exclusions/rounding, milestones, perks at the user's valuation, minus fees unless waiver is on track), the marginal gain over the user's current best card per category, and the reasons in plain language. [B1, B5]
- FR-RE-3. **Acquire** recommendations consider: eligibility (income, age, geography, relationship), compatibility restrictions, issuer max-cards-per-customer policy, pending devaluations, enquiry hygiene (recent hard enquiries, recent rejections), and the user's hard constraints. Ineligible cards remain visible, marked, with an action plan. [C1, C2]
- FR-RE-4. **Close / keep / convert** recommendations: for each held card, rewards earned over the last 12 months net of fees, what the rest of the stack would earn instead, waiver on track or not, LTF/downgrade conversion options, and credit-profile side effects (utilisation, oldest card). Convert is preferred over close. [B3, F2]
- FR-RE-5. **Likelihood of approval** shown per recommended card as a band (High / Medium / Low) with the contributing factors: credit score band vs issuer norms, income vs minimum, existing relationship, existing cards with the issuer, compatibility rules, recent enquiries, and community-reported approval patterns for that card. Presented as an estimate, never a guarantee.
- FR-RE-6. **Community acquisition intelligence:** for each card, a curated summary (from allow-listed communities, shown as speculation with refs) of how people actually got it — pre-approved routes, card-to-card, FD-backed, relationship requirements, common rejection reasons, typical turnaround — with source links. [C3]
- FR-RE-7. **Named-card assessment:** "Should I get X?" runs the same engine for one card and returns value, eligibility, likelihood and compatibility impact. [B2]
- FR-RE-8. **Hard categories:** for rent, utilities, insurance, fuel, jewellery, wallet loads, tax and education the engine states whether anything earns, the lowest-surcharge option, and whether the spend counts toward milestones/waivers. [B6]
- FR-RE-9. **Hard profiles:** student, self-employed, no salary account → FD-backed, card-to-card and relationship-first paths presented as first-class options. [B4]
- FR-RE-10. **Action plan** for an ineligible card: the failing rule and the steps (open relationship account, FD-backed first, reduce utilisation, wait N months after last enquiry), with re-check when steps are done. [C1]
- FR-RE-11. Enquiry hygiene: hard-enquiry log; warnings before applying; flagging of "pre-approved" channels known to hard-pull and reject. [C2]
- FR-RE-12. LTF proof: at card add, prompt for and store the written LTF/waiver confirmation. [C5]
- FR-RE-13. Independence: cc-smith takes no affiliate, referral or issuer payments, so no payout data exists to reach the ranking. [B7]

### 5.6 Payment Method Picker

Given a payment the user is about to make, choose the card and channel that is best **for this user right now**, with reasoning. [D1–D6, D8]

**Inputs**

- FR-PK-1. Amount; merchant (resolved to a merchant record and expected MCC); channel options available to the user for this payment (card present, online card, RuPay credit on UPI, payment app); optional product/category hint.
- FR-PK-2. **Offline merchant resolution:** (a) scan the merchant's UPI/Bharat QR — payee name and, where present, MCC are read directly; (b) current location → nearby merchants (places lookup) → user selects → category → expected MCC; (c) merchant memory: previously resolved merchants ranked first; (d) manual search by name or category. QR takes precedence over location when both are available. [D2, D3]
- FR-PK-3. **Online merchant resolution:** (a) Android Autofill service — cc-smith registers as an autofill provider; when a checkout form asks for a card number, the picker's recommendation appears in the autofill dropdown. The service never stores or fills real card numbers; the user selects the card in the merchant's own form. (b) share-sheet target — share the product or checkout URL from any app to cc-smith; (c) paste a URL; (d) pick from recent/favourite online merchants; (e) type the merchant name. The domain or app package resolves to the merchant record (for marketplaces, the marketplace MCC applies; product hints are used only for offer eligibility). iOS uses (b)–(e); a Safari extension and a desktop browser extension are later surfaces. [D4]
- FR-PK-4. Merchant → MCC map seeded from known merchants, learned from users' statements and reward evidence, with community MCC reports and "known to mis-tag on issuer X" warnings. [D2, H2]

**Decision**

- FR-PK-5. For each held card × available channel the engine computes the **marginal value** of this payment: earn rate applicable to the MCC/merchant/channel after exclusions, cap state in the current period (from the ledger), minimum amount and rounding, surcharges, live offers (reviewed), plus the **option value** of progress toward milestones, fee waivers and spend-and-time locks (e.g. ₹20k this quarter unlocks lounge next quarter). [D1, E2]
- FR-PK-6. Output: ranked cards with, for each, the ₹ reward now, progress contribution (e.g. "brings card C to ₹4,200 from the fee waiver"), warnings (excluded category, cap exhausted, UPI acceptance risk, DCC/forex), and a one-paragraph reason. The user can switch between "max reward now" and "my plan" (notice-board-weighted) rankings and sees why they differ.
- FR-PK-7. Notice Board items feed the picker: an active notice (waiver gap, milestone deadline, spend-and-time lock) raises the ranking of the relevant card with the notice shown as the reason. [5.7]
- FR-PK-8. Channel rules: RuPay credit on UPI eligibility, per-app rate differences, P2M vs P2P, small-ticket rounding, merchant acceptance reports. [D3]
- FR-PK-9. Forex/DCC: for foreign or INR-billed foreign merchants, show expected markup, the pay-in-local-currency reminder, and the best forex card. [D5]
- FR-PK-10. Surcharges: fuel, rent, tax, government, wallet surcharges shown before paying, including when the charged amount will exceed the OTP amount. [D6]
- FR-PK-11. Performance: answer within ~1 s from precomputed per-user state (cap positions, milestone positions, notice weights). No third-party calls in the hot path; merchant lookups are cached.
- FR-PK-12. After the choice, the user confirms the payment was made (or capture detects it), creating a ledger entry and updating trackers. [E1]
- FR-PK-13. UPI hand-off (Android): from a scanned QR, open the user's UPI app with payee prefilled. [D8]

### 5.7 Notice Board

A per-user list of time-bound action items derived from the KB and the ledger; the same items weight the picker. [E2, E4, E5, F1–F7]

- FR-NB-1. Notice types: fee renewal approaching with waiver spend short (amount, days left, cards to route spend from); milestone deadline approaching (threshold, remaining, days left, benefit); spend-and-time lock (spend by date to unlock next-period perk); cap reset or cap exhausted; expiring points/vouchers; pending benefit overdue (milestone/voucher/offer not credited by expected date); due date and amount (with short-payment interest warning); devaluation or rule change affecting a held card (with replan summary); closure follow-ups; new-launch heads-up when it beats the stack by a threshold; LTF/waiver proof missing.
- FR-NB-2. Each notice has: card, deadline, ₹ at stake, the recommended action, and a link to act (open picker with this card prioritised, open redemption optimiser, open closure checklist, open escalation helper).
- FR-NB-3. Notices are generated from KB rules (periods, thresholds, credit lags) × ledger state, recomputed on every ledger or KB change; push notifications at configurable lead times.
- FR-NB-4. **Replan on change:** when a KB change affects a held card, re-run the routing playbook on the user's ledger, diff old vs new, and post a notice with the ₹ impact and the moves; recommend a new card only if value is still lost. [F4]
- FR-NB-5. Reconciliation notices: when expected rewards differ from statement-posted rewards, post the discrepancy with evidence and offer the escalation helper. [E3, F5]
- FR-NB-6. Keep/convert/close notice ~45 days before renewal, with the decision inputs. [F2]
- FR-NB-7. Closure workflow checklist and reminders until the closure is confirmed on the credit report. [F3]
- FR-NB-8. Escalation helper: per-issuer ladder (customer care → nodal/PNO → RBI Ombudsman), drafts the complaint from ledger evidence, tracks the case. [F5]
- FR-NB-9. Evidence vault: stores LTF/waiver confirmations, offer T&C snapshots, chat screenshots for disputes. [C5, F7]
- FR-NB-10. The KB carries, per card, the structured rules that make these notices possible (periods, lags, locks); the automated change pipeline keeps them current.

### 5.8 Redemption Optimizer

- FR-RD-1. For a card's point balance, rank redemption routes by net ₹ per point after fees, GST, caps, minimums and denominations; show the ₹ outcome for the full balance and for partial redemptions. [G1]
- FR-RD-2. Account for expiry: show points expiring within 30/60/90 days and the best route to clear them.
- FR-RD-3. "Redeem now vs wait": when a partner devaluation or route change is announced (pending KB version), compare value now vs after the effective date.
- FR-RD-4. Partner-programme tracking: transfer ratios, partner additions/removals, partner-currency value changes, each with impact on the user's stored points and an alert. [G2]
- FR-RD-5. Respect the user's points stance (FR-VAL-3): routes the user has said they will not use are shown but de-prioritised.

### 5.9 Trust and community

- FR-TR-1. Provenance everywhere: source and as-of date on every displayed fact; changelog per card; corrections and their resolution visible. [H1]
- FR-TR-2. Community signals: users report RuPay-credit-on-UPI acceptance at a merchant, lounge denials (lounge, card, date), MCC observations; aggregated and shown at the decision point (picker, card page, lounge perk). [H2]
- FR-TR-3. Privacy posture: DPDP-compliant consent per data source; deletion on request within 30 days; no card numbers stored (product + last four only); encryption at rest; no personal data in extraction prompts or third-party search queries; local-first capture on device where possible; a published data map. [H3]
- FR-TR-4. Ranking independence statement on the recommendation screen: no affiliate, referral or issuer money; every rank shows its breakdown. [B7]

### 5.10 Owner console (read-only; no review queue)

- FR-AD-1. Change alerts and feed: every `knowledge.changed` event with card, field, old → new value, tier (fact or speculation), event type (published, speculation added, promoted, contradicted, expired, demoted by re-check, rolled back), every reference (URL, quoted text, fetch time, evidence id, search id), a large-change flag (rate, cap or fee moving more than 50%) and holder count. Immediate alert per change plus a daily digest; channel decided at implementation. Alerts are informational: nothing waits for the owner.
- FR-AD-2. Speculation list: open speculation and speculative launches by card, age, refs and expiry; catalogue requests from custom cards by holder count. The only action is trigger re-fetch; the console cannot write facts or speculation.
- FR-AD-3. Official-source allow-list management: issuer and co-brand partner domains with the fields each owns; every edit versioned and alerted.
- FR-AD-4. Version history and rollback: field-level history, effective dates and changelog per card; automatic rollback when the weekly re-check fails, plus manual rollback to a previous published version.
- FR-AD-5. Fan-out monitoring: after a published change or rollback, visibility into recomputation of trackers/notices for affected users.

---

## 6. Data model (overview)

| Entity | Key fields |
|---|---|
| Issuer | name, regulator reference, policies (max cards per customer, closure process, escalation ladder), source refs |
| CardProduct / CardVariant | issuer, name, variant, network, UPI capable, status (active/discontinued), co-brand partner |
| RuleDocument (versioned) | variant, effective_from/to, fees, waiver rules, earn rules, exclusions, caps, milestones, welcome benefits, perks, redemption routes, eligibility, compatibility restrictions; every field with source/as_of/verified_by |
| PartnerProgramme | name, currency value (sourced), transfer ratios per card, status |
| Merchant | canonical name, domains, place IDs, expected MCC, observed MCCs by issuer, acceptance reports |
| User | auth id, profile (income band, age, employment, city), credit score band, bank relationships, preference profile, consents |
| HeldCard | user, variant or custom card, open date, statement date, due date, fee date, limit, LTF proof |
| LedgerEntry | user, held card, date, amount, merchant, MCC (expected/actual), channel, provenance, reward lines |
| TrackerState | user, held card, period, cap position, milestone position, waiver position, lock position |
| Notice | user, type, card, deadline, ₹ at stake, action, status |
| Speculation | card, field, value, refs (URL, quote, fetch time, evidence id), origin (news/forum/user report/AI Mode/range-check failure), status (open/promoted/contradicted/expired), opened, expires |
| CommunitySignal | type (acceptance/lounge denial/MCC), merchant or lounge, card, date, user (pseudonymous), aggregation |

---

## 7. Non-functional requirements

- NFR-1. **Correctness:** engine uses decimal arithmetic; golden tests per card variant against its MITC; property tests for caps, rounding and period resets.
- NFR-2. **Latency:** picker ≤ 1 s p95 from precomputed state; glossary and recommendations ≤ 3 s p95; chat streaming first token ≤ 2 s.
- NFR-3. **Freshness:** every rule document re-verified at least every 30 days; devaluation news polled daily.
- NFR-4. **Privacy/security:** data residency in India; encryption at rest and in transit; no PAN/CVV storage; per-user data isolation; DPDP consent records; deletion SLA 30 days.
- NFR-5. **Availability:** 99.5% monthly for the API; picker works offline for held cards' static rules with last-synced tracker state.
- NFR-6. **Auditability:** every KB change (publish, speculation, promotion, rollback) and recommendation output is logged with inputs and rule versions used.
- NFR-7. **Platforms:** Flutter app on Android and iOS; Android-only capabilities (notification capture, QR hand-off) degrade gracefully on iOS.

---

## 8. Open questions and answers

Rows 1–9 were accepted as decisions on 2026-10-07; the running log, research items and experiments are in `docs/decisions.md`.

| # | Question (from requirements) | Answer (decided 2026-10-07) |
|---|---|---|
| 1 | How do we handle a user's card that is not in the master list? | Custom card on the user's account with manual due/fee data; rewards "can't assess yet"; auto intake request prioritised by holder count; linked to the master variant when its official page is found and published (FR-KB-13/14). |
| 2 | How do we track spending habits? | Input ladder: budget by category (v1) → statement upload → Android notification capture → email → Account Aggregator if viable. Estimates are replaced by actuals (5.4). |
| 3 | How do we get MCC for offline payments? | QR scan first (payee + MCC when present), then location → nearby merchants → select, then merchant memory and manual search; expected MCC from the merchant map, actual MCC learned from statements (FR-PK-2/4). |
| 4 | Online payments — pasting a link, or better? | Android Autofill service is the primary path (recommendation appears in the card-number field at the moment of choice); share-sheet target, paste URL, recent merchants and name search as fallbacks; iOS share-sheet first; browser extensions later (FR-PK-3). |
| 5 | Max cards per bank | Stored as an issuer policy with source; applied in acquire recommendations (FR-KB-2, FR-RE-3). |
| 6 | Bank relationship effect on eligibility | Relationship captured in profile; eligibility and likelihood use it; action plans can recommend opening a relationship (FR-RE-1/5/10). |
| 7 | Likelihood of approval | Banded estimate from score band, income, relationship, existing issuer cards, compatibility, enquiries and community patterns; always labelled as an estimate (FR-RE-5). |
| 8 | Credit score source | v1 user-entered band plus "don't know"; bureau partner integration evaluated after launch from the findings in `docs/research/eligibility-and-likelihood-inputs.md`. |
| 9 | Live bank offers | Offer records in the KB with end dates. Offers quoted from an issuer's own offer page are facts; aggregator and forum offers are speculation. Offers appear in the picker as hints with source and end date, not in the ₹ ranking, because offer terms are free text (`docs/research/live-offers-sources.md`). |

---

## 9. Release plan

| Release | Scope | Feature IDs |
|---|---|---|
| **v1 — Decide** | Master list (~30 hand-verified cards → growing), glossary with provenance, budget-based spend profile, preference profile, recommendation engine (acquire/keep/close, likelihood band, compatibility, hard categories), named-card assessment, picker (typed merchant, manual channel), basic notice board (fee renewal, milestones, due dates from user-entered data), chat agent, privacy posture | A1–A4, B1–B7, C1, C5, D1 (typed), E1 (budget), F1, F2, H1, H3 |
| **v2 — Track** | Statement upload, Android notification capture, trackers with cycle-correct resets, full notice board (locks, expiring points, pending benefits, replan), reconciliation, QR scan and location-based merchant resolution, Autofill and share-sheet online resolution, UPI hand-off, owner change feed and speculation list, automated change pipeline, news ingestion | A5–A8, C2, D2, D3, D5, D6, D8, E2–E7, F3–F5, F7 |
| **v3 — Optimise** | Redemption optimiser, partner tracking, community signals, community acquisition intelligence, application tracker, upgrade/downgrade paths, browser extension, new-launch heads-up, email capture | C3, C4, D4, F6, G1, G2, H2 |

---

## 10. Traceability — owner requirements → PRD → feature IDs

| Owner requirement | PRD | Feature IDs |
|---|---|---|
| Master list as source of truth; add new cards as released | 5.1 FR-KB-1/2/8 | A1, A6, F6 |
| User holds a card not in the master list | FR-KB-13/14 | — (new) |
| Allow-listed sites; admin approval for new cards (approval superseded by plan DR-12: automatic publish from official sources); issuer or co-brand partner sources | FR-KB-7/8, 5.10 | A6 |
| Compatibility restrictions between cards | FR-KB-5, FR-RE-3 | — (new) |
| Pull MITC / issuer master documents | FR-KB-6/9 | A6 |
| Rewards, perks, milestones, exclusions, accelerated categories, unique perks | FR-KB-2 | A2, A3, A4 |
| Allow-listed communities (TechnoFino, r/CreditCardsIndia) | FR-KB-7/10 | A7, A8 |
| Cashback vs points; transfer partners; conversion rates; user preference | 5.2 | A5, G1, G2 |
| Card glossary with pre-qualified tags, fees, milestones, perks | 5.3 | B5, H1 |
| Recommendation: acquire/close by score, spends, held cards; max cards per bank; relationship; likelihood; community experiences | 5.5 | B1–B7, C1–C3, F2 |
| Tracking spending habits | 5.4 | E1, E7 |
| Picker: caps, exclusions, offline/online merchant → MCC, UPI/card channel, milestone and time-lock tradeoffs, reasoning | 5.6 | D1–D6, D8 |
| Notice board: renewal/waiver gap, milestone deadlines, expiring rewards, spend-and-time locks; feeds picker | 5.7 | E2, E4, E5, F1–F7 |
| Redemption optimiser; partner tracking | 5.8 | G1, G2 |
| Provenance, community signals, privacy | 5.9 | H1, H2, H3 |
| Dropped: effective price across stores | — | D7 (removed) |
