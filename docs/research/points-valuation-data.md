# Points valuation data: turning reward points into rupees

Purpose: the facts cc-smith needs to (1) compare cashback cards with points cards on a common ₹ basis and (2) let the redemption optimiser rank redemption routes. Every number carries its source URL and the date it was read. All reads were on **7 Oct 2026** unless a different date is given. Nothing here is invented; where sources disagree both figures are shown and the row is also listed in §8.

Source tiers used (see §6 for the rule):
- **Tier 1 (ratios, caps, expiry):** issuer pages/PDFs, partner programme pages, and the two local files `docs/research/verified-card-facts.json` (extracted from official PDFs, as of 2026-10-07) and `docs/research/seed-cards.md`.
- **Tier 2 (realised ₹ value, change timelines):** CardAdvisor, CardTrail, CardExpress, Magnify.club, Live From A Lounge (LFAL), Paisabazaar/BankBazaar quoting issuer text.
- **Tier 3 (sentiment only):** r/CreditCardsIndia, TechnoFino. Arctic Shift returned `Timeout. Maybe slow down a bit` on all 6 attempts on 7 Oct 2026 (same failure as recorded in `seed-cards.md` §5), and technofino.in is Cloudflare-blocked, so no fresh Tier-3 figures were captured in this pass. Tier-3 refresh is listed in §8.

Terminology: **floor** = cash-equivalent route anyone can take (statement credit, or Amazon/Flipkart voucher). **Typical** = what a reasonably informed holder realises through the issuer's own travel portal or a common voucher. **Ceiling** = best documented transfer route, needing a premium tier and award availability. Ratios are written **bank points : partner points**.

---

## 1. Issuer programme table

| Programme (card tier) | Cash floor ₹/pt | Typical ₹/pt | Ceiling route → ₹/pt | Caps (redemption / transfer) | Expiry | Devaluations 2024–26 (count) | Sources |
|---|---|---|---|---|---|---|---|
| **HDFC Reward Points — Infinia / Infinia Metal** | ₹0.30 statement credit (aggregators quoting HDFC; official page not machine-readable, see §8) | ₹1.00 SmartBuy flights/hotels/Apple/Tanishq; ₹0.50 vouchers | 1:1 to KrisFlyer / Flying Blue / Finnair Avios → ₹1.00–1.40 (CardExpress range); 2:1 to Accor → ₹1.00 | Flights+hotels+airmiles **1,50,000 RP / calendar month**; statement credit **50,000 RP / month**; max **5 redemptions / month** and **₹2,00,000 / cycle** (1 Feb 2026); **70 %** of travel / Apple / Tanishq bill; Apple 1 product / quarter; Tanishq 50,000 RP / quarter; SmartBuy accelerated **15,000 RP / month**, of which brand vouchers **3,000 RP / month** (1 Jul 2026); earn cap 2,00,000 RP / cycle; transfer cap 1,50,000 RP / month | **3 years** from accrual; nullified after **365 days** of no card use | 15 Jan 2024 (2:1 for Turkish/Accor/Avianca), 1 Sep 2024 (utility/telecom 2,000 RP caps; 3rd-party education 0), 1 Oct 2024 (Apple/Tanishq redemption caps), 1 Jul 2025 (insurance 10,000 RP cap), Jan 2026 (GyFTR 5X→3X, reversed within weeks), 1 Feb 2026 (redemption frequency/₹ caps), Feb 2026 (₹18L retention rule), 1 Jul 2026 (voucher 3,000 cap) → **≈7 effective, 1 reversed** | Official T&C PDF [1]; KFS v2.5 [2]; CardTrail [3]; CardAdvisor [4][5]; AngelOne [6]; seed-cards.md §3.6 |
| **HDFC — Diners Club Black Metal** | ₹0.30 statement (same aggregator basis as Infinia) | ₹1.00 SmartBuy flights/hotels; ₹0.50 vouchers | Same partner table as Infinia (1:1 KrisFlyer etc.) → ₹1.00+ | SmartBuy accelerated **10,000 RP / month** (DCB non-metal 7,500), voucher sub-cap 3,000; transfer cap **75,000 RP / month** | 3 years | Shares Infinia's programme changes (same T&C clauses) | CardAdvisor [5][4]; KFS [2] |
| **HDFC — Regalia Gold** | ₹0.20 statement balance (official page) | ₹0.50 flights/hotels; ₹0.65 "Exclusive Gold Catalogue"; ₹0.35 products/vouchers | "up to 0.5 airmiles" per RP (2:1 to most airlines, 3:1 to BA/Qatar/Air India/Aeroplan/Etihad per CardAdvisor) → ₹0.33–0.50 | SmartBuy accelerated **4,000 RP / month**; earn cap 50,000 RP / cycle; transfer cap **50,000 RP / month** | 2 years (KFS: all cards other than Infinia/DCB family) | 15 May 2026 base earn cut (5 RP/₹200); lounge gate Jul 2026 → **2** | verified-card-facts.json (official page quote) [7]; CardAdvisor [4][5]; KFS [2]; seed-cards.md §3.7 |
| **HDFC — Millennia (CashPoints)** | **₹1.00** statement credit (cap 3,000 CashPoints / month, min 500, ₹50 fee) | ₹1.00 | SmartBuy flights/hotels/catalogue at **₹0.30** (worse than cash; never recommend) | 1,000 CashPoints / month per 5 % and 1 % buckets | 2 years (KFS) | 1 Sep 2024 wallet/EMI/education exclusions; 20 Jul 2026 T&C → **2** | verified-card-facts.json [7]; KFS [2]; seed-cards.md §3.3 |
| **Axis EDGE Miles — Atlas** | ₹1.00 on Travel EDGE ("1 EDGE Mile is equal to INR 1", Atlas T&C) | ₹1.00 | 1:2 to KrisFlyer / Air India / Flying Blue → ₹2.00 (CardAdvisor) up to ₹2.80 at CardExpress's KrisFlyer high; Accor now **2:1** → ₹1.00 | Annual transfer cap **Group A 30,000 / Group B 1,20,000 miles**; fee **₹99** per Travel EDGE redemption, **₹199** per partner transfer | Not stated in sources read (§8) | 20 Apr 2024 (welcome/milestone cuts, ₹2L/month travel earn cap, 1,50,000 transfer ceiling), 2 Apr 2026 (Accor/Marriott/Qatar removed; BA/Finnair/Vietnam/IndiGo added at 2:1), 5 Aug 2026 (Qatar back, weaker), 25 Sep 2026 (Accor/Hilton/M&M/Cathay added, ITC removed, Air India/Flying Blue/Qantas → Group A) → **4** | verified-card-facts.json (Atlas T&C) [7]; CardTrail [8]; CardAdvisor [9][10]; Magnify [11]; LFAL [12] |
| **Axis EDGE Reward Points — Magnus / Reserve** | ₹0.20 statement credit / vouchers | ₹0.20 Travel EDGE (CardAdvisor) **vs** ₹0.30–0.50 (CardTrail) — conflict | **5:1** to Group A (KrisFlyer, Air India, Flying Blue, Accor, Avios…) → ₹0.20 at ₹1/mile, ₹0.40 via Accor at ₹2; **5:2** to Hilton / Miles & More | Annual transfer cap **Group A 1,00,000 / Group B 4,00,000 points**; M&M separate 2,00,000 cap, min 3,000 | **3 years** from transaction (Axis FAQ via BankBazaar; pointsmath) **vs** "2 years inactivity" (CardTrail) — conflict | 20 Apr 2024, 20 Dec 2024, 2 Apr 2026 (5:2→5:1), 25 Sep 2026 → **4** (plus 1 Sep 2023 5:4→5:2) | Magnify [11]; CardTrail [8][13]; CardAdvisor [9]; BankBazaar [14]; Pointsmath [15]; DesiDime [16]; CardInsider [17]; seed-cards.md §3.9 |
| **Axis — Magnus for Burgundy** | ₹0.20 | ₹0.20 | **5:2** to all 20+ partners (Magnify, LFAL) **vs** 5:4 (Pickmycard/Savesage snippet) — conflict → ₹0.40 at ₹1/mile, ₹0.80 via Accor | Group A **2,00,000** / Group B **8,00,000** | 3 years | 2 Apr 2026 (5:4→5:2), 25 Sep 2026 → **2** | Magnify [11]; LFAL [12]; seed-cards.md §3.9 |
| **Axis — Burgundy Private** | ₹0.20 | ₹0.20 | **5:4** to all partners → ₹0.80 at ₹1/mile, ₹1.60 via Accor (CardAdvisor "EDGE RP high ₹1.60") | Group A **3,00,000** / Group B **12,00,000** | 3 years | 20 Apr 2024, 25 Sep 2026 (partner moves) → **2** | Magnify [11]; CardAdvisor [10] |
| **Amex Membership Rewards (India)** | ₹0.25 pay-with-points / shop.amex.in / Amazon voucher | **₹0.50** 18K Gold Collection Taj voucher (18,000 pts → ₹9,000); **₹0.583** 24K Taj (24,000 → ₹14,000); Amazon 18K/24K = ₹0.333 | 1:1 Marriott → ₹0.60 conservative, ₹1.50–2.50 on international aspirational stays (CardTrail); 1:0.8 Virgin Atlantic → ₹0.80; 1:1.5 Hilton → ₹0.53; 2:1 KrisFlyer/BA/Qatar/Asia Miles → ₹0.50 | Min transfer 1,000 MR; no published annual cap found | **Never** while account active | Hilton 2:3 and Virgin 5:4 are **improvements** (18 Aug 2026); no devaluation event found 2024–26 → **0 documented** | Amex Gold Collection page [18]; Magnify [19]; CardTrail [20]; CardAdvisor [21]; Pointsmath [15] |
| **SBI Card Reward Points (Elite, Aurum, SimplyCLICK…)** | **₹0.25** statement credit ("4 Reward Points = Re. 1"), fee ₹99+GST per redemption | ₹0.25 (vouchers 0.25–0.50 per CardTrail) | Air India transfer on Elite/Aurum (ratio not confirmed; CardTrail still names "Club Vistara", which no longer exists) → ₹0.50–1.00 claimed | Statement credit **60,000 RP / card / calendar month** from 1 Apr 2026; Aurum statement credit in multiples of 4,000 | **24 months** from accrual (BankBazaar quoting SBI) **vs** 3 years (CardTrail) — conflict | 1 Apr 2026 (Cashback card cap ₹5k→₹4k, splits, exclusions; statement credit cap; new exclusion categories) → **1 bank-wide event** (plus 2023 Cashback exclusions) | BankBazaar [22]; CardTrail [23]; CardAdvisor [24][10]; seed-cards.md §3.4 |
| **SBI Cashback Card** | ₹1.00 (auto statement credit) | ₹1.00 | n/a | ₹4,000 / cycle (₹2k online + ₹2k offline) from 1 Apr 2026 | n/a | 1 Apr 2026 → 1 | seed-cards.md §3.4; CardAdvisor [10] |
| **ICICI Reward Points — Emeralde Private Metal** | ₹0.40 statement credit | **₹1.00** iShop flights/hotels/vouchers | Air India 1:1 "only on two cards; 6:1 elsewhere" (CardAdvisor) → ₹1.00 | iShop accelerated **18,000 pts / month** (12X hotels, 6X flights/vouchers); Sapphiro 9,000 / month | **3 years** | 15 Nov 2024 (all ICICI cards), 2026 iShop voucher cut (~18 % → ~3 % return) → **2** | LFAL [25]; Tradebrains/Savesage snippets [26]; CardAdvisor [10]; CardInsider [27]; Pickmycard [28] |
| **ICICI — Sapphiro / Emeralde (non-Private) / Coral** | ₹0.25 (Paisabazaar: Emeralde "₹0.25 per redemption") | ₹0.25–0.50 (vouchers) | iShop ₹1.00 for flights/hotels where eligible (cap 9,000 bonus pts on Sapphiro) | as left | 3 years (assumed same programme — verify) | same as above | Paisabazaar [29]; CardTrail [30]; LFAL [25] |
| **HSBC Reward Points — TravelOne / Premier** | ₹0.25 catalogue | ₹0.25–0.50 (travel/vouchers) | **1:1 Accor ALL** → **₹2.00** (highest ceiling in India); 1:1 KrisFlyer/Air India/BA/Qatar/Etihad/Flying Blue/JAL/Thai/Qantas/EVA/Vietnam → ₹1.00; 1:1 Marriott ₹0.60; 1:1 IHG ₹0.45; 1:1 Wyndham; 2:1 Turkish/United/Hainan; 1:3 AirAsia; 5:1 Shangri-La | "no-cap, instant, no transfer fee" (Magnify); none published | Premier: never; Platinum: 3 years; Gold/Classic: 2 years (2024 list); TravelOne not explicitly stated | Live+ revamp 26 Jul 2026 (cashback card, not points) → **0 on the points programme** found | Magnify [31]; CardAdvisor [10][32]; Pointsmath [15]; seed-cards.md §3.14 |
| **IndusInd (Pinnacle, Legend…)** | ₹0.35 catalogue (CardAdvisor); twid "Pay with Rewards" fee **5 % + GST** of amount paid with points from 1 Sep 2025 | ₹0.35 | Air India 1:1 on Tiger/Avios Infinite → ₹0.70–0.75 | — | Never while card active (2024 list) | 1 Sep 2025 twid fee → **1** | IndusInd notice PDF [33]; CardAdvisor [10][34]; CardTrail [30]; Pointsmath [15] |
| **IDFC FIRST** | ₹0.25 vouchers (₹0.22 "realistic" per CardAdvisor) | ₹0.25 | none (no transfer partners found) | Earn capped at credit limit (18 Jun 2026) | **24 months** from 18 Jun 2026 (was "never expire" in 2024 list) | Jan 2026 (FASTag/rail 1X), 18 Jun 2026 (expiry + cap), 2025 utility 1X → **3** ("3rd devaluation in <1 year", TechnoFino thread title) | seed-cards.md §3.13; CardTrail [30]; Pointsmath [15]; CardAdvisor [34] |
| **Kotak (League, Zen, White Reserve…)** | ₹0.25 (Kotak Veer value chart) | ₹0.25 (₹0.22 realistic) | Accor 2:1 (CardAdvisor Accor guide mention) → ₹1.00 — verify per card | — | **2 years** from earn | 1 Jun 2025 reward cuts/fees → **1** | Kotak value chart [35]; FreePressJournal [36]; Pointsmath [15]; CardAdvisor [34] |
| **YES Bank (Marquee, Reserv…)** | ₹0.15 vouchers (devalued) | ₹0.25 travel | — | — | **36 months** excluding month of accrual | voucher devaluation to ₹0.15 (date not captured) → **≥1** | CardAdvisor [37]; CardTrail [30]; Pointsmath [15] |
| **AU SFB (Zenith, Zenith+, LIT)** | ₹0.25 statement credit | ₹0.25 (₹0.22 realistic) | — | LIT RP cap cut (TechnoFino thread) | not captured | 10 Apr 2026 bank-wide transport MCC exclusion + lounge gate; Zenith earn cuts 2025 → **2** | CardAdvisor [38][34][10]; CardInsider [39]; seed-cards.md §3.19 |
| **RBL Bank** | ~₹0.25 | ₹0.25 | — | — | **24 months hard expiry** | not captured | CardAdvisor [34]; Pointsmath [15] |
| **Standard Chartered Ultimate** | **₹1.00** per RP (fixed) | ₹1.00 | — | — | Points earned in a calendar year expire **30 June of the next year** | not captured | SC product PDF / Cardinsider [40]; Pointsmath [15] |
| **Federal Bank (Celesta) / Scapia coins** | Celesta: ₹0.10 statement credit (₹0.25 "official" catalogue value); Scapia: **5 coins = ₹1 → ₹0.20** on Scapia travel | ₹0.20–0.25 | none | — | not captured | not captured | CardAdvisor [41]; Scapia blog / Cardmaven snippets [42] |
| **BOBCARD (Eterna, Scapia BOBCARD)** | **₹0.25** per RP | ₹0.25 | — | — | see BOBCARD RP T&C 2024 PDF (not parsed) | not captured | Pickmywork snippet [43]; BOBCARD RP T&C [44] |
| **OneCard** | **₹0.10** per point | ₹0.10 | — | — | not captured | not captured | OneCard blog / CardInsider [45] |

Cross-issuer index values used by aggregators (for sanity checks only, not for the engine): CardAdvisor `valuations` (verified 1 Jul–1 Oct 2026) gives HDFC ₹0.30 / 0.30–0.50 / 1.00, Amex ₹0.25 / 0.50 / 1.00, ICICI ₹0.40, Axis EDGE Miles ₹0.20 / 1.00 / 2.00–4.00, Axis EDGE RP ₹0.20 / 0.20 / 1.60, SBI ₹0.25, IndusInd ₹0.35 / 0.35 / 0.70, HSBC ₹0.25 / 0.25 / 2.00 [10]. CardTrail's calculator page (13 Mar 2026) gives HDFC 0.50 (Infinia/DCB 0.50–1.00), SBI 0.25, ICICI 0.25–0.50, Axis EDGE RP 0.25–0.50 (Magnus/Atlas 0.50–1.20), Amex 0.30–1.00+, IDFC 0.25, IndusInd 0.50–0.70, Yes 0.25 [30].

---

## 2. Transfer-partner ratio table (bank points : partner points)

### 2a. HDFC (SmartBuy "Miles Transfer"), read 7 Oct 2026 from CardAdvisor's table published 23 Jun 2026 / verified 30 Jun 2026 [4]. Official anchor: Infinia T&C clause 13 "Effective 15th Jan'24, 2 Reward Points will be converted to 1 Loyalty Point for Turkish Miles, Accor and Avianca Life Miles" [1].

| Partner | Infinia / DCB | Regalia Gold | Min / increment | Processing |
|---|---|---|---|---|
| Accor ALL | 2:1 (official [1]) | 2:1 | 1,000 / 1,000 | 1–5 days |
| Singapore KrisFlyer | 1:1 (CardTrail: "100 HDFC = 100 KrisFlyer") | 2:1 | 1,000 | ~7 days |
| Air France-KLM Flying Blue | 1:1 | 2:1 | 1,000 | instant–hours |
| Finnair Plus (Avios) | 1:1 | 2:1 | 1,000 | instant–hours |
| Vietnam Airlines Lotusmiles | 1:1 | 2:1 | 1,000 | — |
| British Airways Executive Club | 2:1 (CardAdvisor recommends routing via Finnair 1:1) | 3:1 | 1,000 | instant–hours |
| Qatar Privilege Club | 2:1 | 3:1 | 1,000 | instant–hours |
| Air India Maharaja Club | 2:1 | 3:1 | 1,000 | 2–4 days |
| Club ITC | 2:1 | 2:1 | 200 / 200 | — |
| Cathay Asia Miles | 2:1 | 3:1 | 1,000 | — |
| United / Turkish Miles&Smiles / Avianca LifeMiles | 2:1 (Turkish & Avianca official [1]) | 2:1 | 1,000 | — |
| Aeroplan / Etihad Guest / Thai | 2:1 | 3:1 | 1,000 | — |
| SpiceJet SpiceClub | 1:1 | 2:1 | 1,000 | — |
| Wyndham Rewards | 1:1 | 2:1 | 1,000 | — |
| IHG One Rewards | 1:1 | 2:1 | 1,000 | — |
| Marriott Bonvoy | 2:1 | 3:1 | 1,000 | 1–5 days |
| Radisson Rewards | 1:1 | 2:1 | 1,000 | — |
| AirAsia Rewards | 1:1 | 2:1 | 1,000 | — |

Monthly transfer caps: Infinia 1,50,000 RP (official, clause 12c, shared with flights/hotels) [1]; DCB 75,000; Regalia Gold 50,000 (CardAdvisor) [4]. No transfer fee stated; transfers irreversible [4]. CardTrail's generic statement "0.5–1 airline mile per HDFC point" [3] agrees with the table.

### 2b. Axis EDGE (post 25 Sep 2026 reshuffle), read 7 Oct 2026 from Magnify.club (23 Sep 2026) [11], cross-checked with LFAL (23 Sep 2026) [12] and CardTrail (3 Apr 2026) [8]. Official page `axis.bank.in/miles-transfer` loads only navigation to the fetcher (263k chars, table not in HTML) — see §8.

| Partner | Magnus for Burgundy | Burgundy Private | Magnus / Reserve | Atlas | Olympus | Horizon |
|---|---|---|---|---|---|---|
| Accor ALL (Group A, returned 25 Sep 2026) | 5:2 | 5:4 | 5:1 | 2:1 | 1:2 | 2:1 |
| Air France-KLM Flying Blue (moved to Group A) | 5:2 | 5:4 | 5:1 | 1:2 | 1:2 | 1:1 |
| Air India Maharaja Club (moved to Group A) | 5:2 | 5:4 | 5:1 | 1:2 | 1:2 | 1:1 |
| Hilton Honors (Group B, new) | 5:2 | 5:4 | 5:2 | 1:2 | 1:4 | 1:1 |
| Lufthansa Miles & More (Group B, new; own 2,00,000/yr cap, min 3,000) | 5:2 | 5:4 | 5:2 | 1:1 | 1:4 | 1:1 |
| Avios (BA / Finnair / Qatar), KrisFlyer, Aeroplan, Turkish, Cathay, JAL, Vietnam, Qantas — Group A | 5:2 | 5:4 | 5:1 | 1:2 core (KrisFlyer) / 2:1 (BA, Finnair, Vietnam, Qatar, Cathay) | 1:2 | 1:1 / 2:1 |
| Group B others: AirAsia, IHG, IndiGo BluChip, Orchid, Postcard Sunshine Club, Radisson, SpiceClub | per Group B card ratio (5:2 / 5:4 / 5:2 / 2:1) — verify each | | | | | |
| Select / Privilege / Rewards cards | 10:1 to all | | | | | |

Annual caps (points out per card, Group A / Group B): Burgundy Private 3,00,000 / 12,00,000; Magnus for Burgundy 2,00,000 / 8,00,000; Olympus 1,50,000 / 6,00,000; Magnus, Reserve, Horizon 1,00,000 / 4,00,000; Atlas 30,000 / 1,20,000 [11]. Atlas T&C (official, via verified-card-facts.json): "annual transfer cap 1,50,000 miles (Group A 30,000 / Group B 1,20,000)"; fees ₹99 per EDGE-portal redemption, ₹199 per partner transfer [7]. Processing 3–7 business days [9]. Removed since 2 Apr 2026: Marriott Bonvoy (not restored as of 25 Sep 2026); Club ITC removed 25 Sep 2026 [9][12].

Conflict flags: CardAdvisor's EDGE guide table still shows Magnus/Reserve 5:2 (~₹0.40) and the Pickmycard/Savesage snippets say Magnus for Burgundy 5:4 to Accor/Cathay/Qatar/M&M; Magnify, LFAL, CardTrail and seed-cards.md all say 5:1 and 5:2 respectively. Treat 5:1 / 5:2 / 5:4 (Magnus / MfB / BP) as current until the official PDF is parsed.

### 2c. Amex India (18 Aug 2026 table, Magnify [19]; CardTrail 20 Mar 2026 [20])

| Partner | Ratio | Notes |
|---|---|---|
| Marriott Bonvoy | 1:1 | 24–48 h; "single best exit" |
| Hilton Honors | 1:1.5 (was 1:0.9 before 18 Aug 2026) | improvement |
| Virgin Atlantic Flying Club | 1:0.8 (was 1:0.5) | improvement |
| Singapore KrisFlyer, BA Executive Club, Qatar Privilege Club, Cathay Asia Miles | 2:1 | 1–3 business days |
| Emirates Skywards, Etihad Guest | 2:1 per CardTrail; **absent** from Magnify's 7-partner list | conflict, §8 |
| Taj / Accor / Air India | not Amex transfer partners (Taj only via Gold Collection vouchers) | [21] |

Minimum 1,000 MR; transfers irreversible; no fee found [20].

### 2d. HSBC TravelOne / Premier (Magnify review, read 7 Oct 2026 [31])

1:1 — Air India, KrisFlyer, BA Executive Club, Qatar Privilege Club, Etihad Guest, Flying Blue, JAL Mileage Bank, Thai Royal Orchid Plus, Qantas, EVA Infinity MileageLands, Vietnam Lotusmiles, Accor ALL, IHG One Rewards, Marriott Bonvoy, Wyndham Rewards. 2:1 — Turkish Miles&Smiles, United MileagePlus, Hainan Fortune Wings. 1:3 — AirAsia Rewards. 5:1 — Shangri-La Circle. Instant, no fee, no cap stated. Official hsbc.bank.in TravelOne URL returned 404 at the path tried — see §8.

### 2e. Others
- ICICI: Air India 1:1 on two cards (not named in the snippet), 6:1 on others [10] — card list unverified.
- SBI Elite / Aurum: Air India transfer exists; ratio not captured [23].
- IndusInd Tiger / Avios Visa Infinite: Air India 1:1 [10]; Avios card earns Avios directly [34].
- Kotak and SBI "transfer to Accor at 2:1" (CardAdvisor Accor guide snippet [32]) — which cards, unverified.

---

## 3. Partner-currency value table (₹ per point/mile; community/aggregator realised values)

| Currency | Low | Typical | High | Sources (read 7 Oct 2026) |
|---|---|---|---|---|
| Marriott Bonvoy | ₹0.40 | ₹0.60 | ₹0.80–0.90; ₹1.50–2.50 on aspirational international stays | CardAdvisor programme page "₹0.40–0.80 depending on property" [46]; CardAdvisor valuations ₹0.60 [10]; CardExpress (TPG-derived at ₹84/USD) ₹0.50–0.90 [47]; CardTrail Amex guide ₹1.50–2.50 optimal [20]; LFAL dynamic-pricing bands (Goa Marriott 30–60k pts) [48] |
| Accor ALL | ₹1.20 | ₹2.00 | ₹2.10+ (euro peg €0.02/pt at €≈₹107) | CardAdvisor valuations [10]; CardAdvisor "how Accor points work" (₹1.8 → ₹2.1+) [32]; CardExpress ₹1.20–2.00 [47] |
| Taj InnerCircle / Tata NeuCoins | ₹0 outside Tata ecosystem | ₹1.00 inside Tata Neu | ₹1.00 | Tata Digital support "1 NeuCoin = ₹1" [49]; CardAdvisor (12-month expiry) [34]. Taj InnerCircle points proper: no ₹ value found (§8) |
| Air India Maharaja Club | ₹0.60 | ₹1.00 | ₹1.00+ on Star Alliance partner awards | CardAdvisor ₹1.00 [10]; CardExpress ₹0.60–1.00 [47]; CardAdvisor guide "realistically well under a rupee" [50]; Air India 2026 award chart (DEL–SIN/BKK/DXB 12,000 pts economy) [51] |
| IndiGo BluChip | ₹0.30 | ₹0.40 | ₹0.50 | CardTrail "roughly ₹0.40", silent cut mid-2025 [52]; CardAdvisor ₹0.42 [10]; TheFlightClub 0.30–0.50 [53] |
| Etihad Guest | ₹0.80 | ₹1.00 | ₹1.20 | CardExpress ₹0.80–1.20 [47]; HSBC 1:1 route [31] |
| Singapore KrisFlyer | ₹0.90 | ₹1.00 | ₹1.40 (CardExpress); "up to ~₹2 on premium Saver" (CardAdvisor) | CardAdvisor [10][54]; CardExpress [47] |
| Qatar Privilege Club (Avios) | ₹0.80 | ₹1.00 | ₹1.80 | CardAdvisor "BA & Qatar Avios ≈₹1.00" [10]; CardExpress BA Avios ₹0.80–1.80 [47] |
| British Airways / Finnair Avios | ₹0.80 | ₹1.00 | ₹1.80 | same as above |
| Aeroplan | — | — | — | **No Indian ₹ valuation found.** LFAL June 2026 only gives purchase cost ₹1.38–2.59/pt [55] (a cost, not a value). §8 |
| United MileagePlus | ₹0.50 | ₹0.90 | ₹1.40 | CardAdvisor "moderate ₹0.50–0.80 (2:1 transfer)" [10]; CardExpress ₹0.90–1.40 [47] — conflict in band |
| Air France-KLM Flying Blue | ₹0.90 | ₹1.00 | ₹1.40 | CardAdvisor [10]; CardExpress [47] |
| Turkish Miles&Smiles | ₹0.80 | ₹1.00 | ₹1.20 | CardExpress [47]; CardAdvisor "strong" tier [10] |
| Hilton Honors | ₹0.35 | ₹0.35 | ₹0.48 (purchase cost at 100 % bonus, LFAL) | CardAdvisor [10]; CardAdvisor Amex guide (₹0.53/MR at 2:3 ⇒ ₹0.35/Hilton pt) [21]; LFAL [55] |
| IHG One Rewards | ₹0.40 | ₹0.45 | ₹0.70 | CardAdvisor ₹0.45 ("Indian estate is Holiday Inn") [10]; CardExpress ₹0.40–0.70 [47]; AwardWallet ≈₹0.66 [56] |
| Wyndham Rewards | ₹0.25 | — | ₹0.65 | CardAdvisor valuations ₹0.25 [10] **vs** CardAdvisor HDFC transfer table ₹0.65 at 1:1 [4] — conflict |
| Club ITC | ₹0.30 | — | ₹1.00 | CardAdvisor valuations ₹0.30 "heavily diluted" [10] **vs** CardAdvisor programmes page ₹1.00 [57] and HDFC transfer table ₹0.50/HDFC pt at 2:1 ⇒ ₹1.00/ITC pt [4] — conflict |
| Cathay Asia Miles | ₹0.50 | — | ₹0.80 | CardAdvisor moderate tier [10] |

Realised-value sanity check against the cash floor: a route is only worth recommending when `ratio × partner ₹ value > floor ₹ value` for that programme (e.g. Magnus 5:1 × ₹1.00 KrisFlyer = ₹0.20 = floor; 5:1 × ₹2.00 Accor = ₹0.40 > floor; Infinia 1:1 × ₹1.00 KrisFlyer = ₹1.00 = SmartBuy travel typical, so transfer only wins if the award is above ₹1/mile).

---

## 4. Expiry rules (points lifetime)

| Programme | Rule | Source |
|---|---|---|
| HDFC Infinia / Infinia Metal / DCB Metal / DCB / H.O.G Diners / BizBlack | 3 years from accumulation; "If the credit card is not used for more than 365 days, reward points accrued will be nullified" | Infinia T&C [1]; KFS v2.5 Mar 2025 [2] |
| HDFC all other cards (Regalia Gold, Millennia CashPoints…) | 2 years from accumulation; EasyEMI CashPoints 1 year | KFS v2.5 [2] |
| Axis EDGE Reward Points | 3 years from the transaction date (BankBazaar quoting Axis FAQ; Pointsmath) — CardTrail says "typically expire after 2 years of account inactivity" (conflict) | [14][15][13] |
| Axis EDGE Miles | not stated in sources read | §8 |
| Amex MR | never expire while account active | [20][15] |
| SBI Card | 24 months from accrual (BankBazaar quoting SBI) vs 3 years (CardTrail) — conflict | [22][23] |
| ICICI | 3 years from receipt (Emeralde Private) | [26] |
| HSBC | Premier never; Platinum 3 years; Gold/Smart Value/Classic 2 years (Feb 2024 list); TravelOne not stated | [15] |
| IndusInd | never, while card active | [15] |
| IDFC FIRST | 24 months, effective 18 Jun 2026 (previously never) | seed-cards.md §3.13; [15] |
| Kotak | 2 years from earn | [15][35] |
| YES Bank | 36 months excluding month of accrual | [15] |
| RBL | hard expiry 24 months | [15] |
| Standard Chartered | expire 30 June of the year after they were earned | [15][40] |
| Tata NeuCoins | 12 months | [34] |
| AU, Federal, BOBCARD, OneCard, Scapia coins | not captured | §8 |

---

## 5. Transfer mechanics summary

| Issuer | Minimum / increment | Caps | Fee | Processing | Reversible |
|---|---|---|---|---|---|
| HDFC | 1,000 / 1,000 (Club ITC 200) | 1,50,000 RP/month Infinia (official, shared with flights/hotels); 75,000 DCB; 50,000 Regalia Gold | none stated | instant–7 days by partner | no |
| Axis | not captured (M&M min 3,000) | annual Group A / B caps per card (§2b) | ₹199 per transfer; ₹99 per Travel EDGE redemption (Atlas T&C) | 3–7 business days | no |
| Amex | 1,000 | none found | none found | airlines 1–3 business days; Marriott 24–48 h | no |
| HSBC | not captured | "no cap" (Magnify) | none | instant | — |
| SBI / ICICI / IndusInd / Kotak | not captured | ICICI iShop monthly bonus caps only | SBI ₹99+GST per redemption; IndusInd twid 5 %+GST | — | — |

Sources: [1][4][7][9][11][19][20][22][31][33].

---

## 6. Sourcing and refresh rule (proposal)

1. **Ratios, caps, fees, expiry = issuer-authoritative only.** Store these from the issuer PDF/page (HDFC T&C/KFS, Axis card T&C and the miles-transfer page rendered in a headless browser, Amex redeem pages, SBI MITC/notices, ICICI T&C, HSBC services guide). Aggregator values may *pre-fill* a row but the row stays `status: "unverified"` until an issuer quote and URL are attached (same policy as `verified-card-facts.json`). Where the issuer page is JS-rendered (SBI, Axis miles-transfer, AU) the scraper must use a headless browser; Wayback snapshots are acceptable fallbacks with the snapshot date recorded.
2. **Realised ₹ value per partner currency = community/aggregator consensus, stored as a range.** Take ≥2 Tier-2 sources per currency (CardAdvisor valuations, CardExpress, CardTrail, Magnify, LFAL) plus Tier-3 sentiment (r/CreditCardsIndia via Arctic Shift, TechnoFino via Wayback) when retrievable. Record `low`, `typical`, `high`, each with its own source URL and read date; never average across sources silently.
3. **Refresh cadence.** Issuer ratios/caps: re-fetch weekly and diff (HDFC's `/pdf/common/Credit-Cards/*feature-change*.pdf` and Axis/ICICI notice pages are the known change channels); any diff creates a dated `change_event` row. Partner valuations: monthly, plus event-driven re-pull when an issuer removes/adds a partner or an airline publishes a new award chart (Air India 2026 chart, Marriott dynamic pricing). Devaluation count: derived from `change_event` rows, not hand-maintained. Everything older than 90 days without a successful re-read is flagged `stale` in the UI.
4. **How to show it to the user.** Show three numbers per programme: *cash floor* (always achievable), *typical* (issuer travel portal or voucher route the user has said they would use), *ceiling* (best transfer route, with the partner and the cap). The comparison engine ranks cards on the **typical** figure by default and lets the user switch to floor or ceiling; the optimiser ranks individual redemptions by `points × route ₹/pt − fees`, subject to the monthly/annual caps. Always print the read date and "value depends on award availability" next to any transfer-based figure, and show both figures when sources conflict (as in §8) instead of picking one.

---

## 7. Proposed JSON shapes

### 7a. `points_programme`
```json
{
  "id": "hdfc_rp_infinia",
  "issuer": "HDFC Bank",
  "programme_name": "HDFC Reward Points",
  "card_tier": "Infinia / Infinia Metal",
  "currency_code": "HDFC_RP",
  "cash_floor_inr_per_pt": { "value": 0.30, "route": "statement_credit", "source_url": "https://www.paisabazaar.com/hdfc-bank/infinia-credit-card/", "source_tier": 2, "read_on": "2026-10-07", "status": "unverified_official" },
  "typical_inr_per_pt": { "value": 1.00, "route": "smartbuy_flights_hotels", "source_url": "https://cardtrail.in/rewards/maximize-hdfc-reward-points-2026/", "source_tier": 2, "read_on": "2026-10-07" },
  "ceiling_inr_per_pt": { "value": 1.40, "route": "transfer", "transfer_partner_id": "krisflyer", "ratio": "1:1", "partner_value_basis": "high", "source_url": "https://cardexpress.in/articles/award-travel-beginners-guide-india", "read_on": "2026-10-07" },
  "redemption_routes": [
    { "route": "smartbuy_flights_hotels", "inr_per_pt": 1.00, "max_share_of_bill": 0.70, "cap": { "points": 150000, "period": "calendar_month", "shared_with": ["airmiles_transfer"] } },
    { "route": "statement_credit", "inr_per_pt": 0.30, "cap": { "points": 50000, "period": "calendar_month" }, "max_redemptions_per_month": 5, "max_inr_per_cycle": 200000 },
    { "route": "vouchers_products", "inr_per_pt": 0.50 },
    { "route": "apple_tanishq", "inr_per_pt": 1.00, "max_share_of_bill": 0.70, "cap_note": "1 Apple product per quarter; Tanishq 50,000 RP per quarter" }
  ],
  "earn_caps": [ { "scope": "all", "points": 200000, "period": "statement_cycle" }, { "scope": "smartbuy_accelerated", "points": 15000, "period": "calendar_month" }, { "scope": "smartbuy_brand_vouchers", "points": 3000, "period": "calendar_month", "effective_from": "2026-07-01" } ],
  "expiry": { "months": 36, "basis": "from_accrual", "inactivity_forfeit_days": 365, "source_url": "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/cards/credit-cards/infinia-credit-card/rewards-points-program-terms-and-conditions.pdf", "read_on": "2026-10-07" },
  "devaluations": [
    { "date": "2024-01-15", "summary": "2:1 for Turkish, Accor, Avianca", "source_url": "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/cards/credit-cards/infinia-credit-card/rewards-points-program-terms-and-conditions.pdf" },
    { "date": "2026-02-01", "summary": "5 redemptions/month; ₹2,00,000/cycle", "source_url": "https://oga-prod.angelone.in/news/stocks/hdfc-bank-credit-card-reward-points-revised-effective-february-1-2026" },
    { "date": "2026-07-01", "summary": "SmartBuy brand-voucher accelerated RP capped at 3,000/month", "source_url": "https://cardadvisor.in/articles/hdfc-smartbuy-voucher-devaluation-july-2026" }
  ],
  "last_verified": "2026-10-07"
}
```

### 7b. `transfer_partner`
```json
{
  "id": "axis_edge_rp_magnus__accor_all",
  "programme_id": "axis_edge_rp_magnus",
  "partner_currency_id": "accor_all",
  "ratio": { "from": 5, "to": 1 },
  "group": "A",
  "annual_cap_points_out": 100000,
  "cap_scope": "group_A_shared",
  "min_transfer_points": null,
  "increment_points": null,
  "fee_inr": 199,
  "processing_days": { "min": 3, "max": 7, "unit": "business_days" },
  "reversible": false,
  "effective_from": "2026-09-25",
  "status": "active",
  "sources": [
    { "url": "https://magnify.club/guides/axis-accor-returns-miles-and-more-september-2026/", "tier": 2, "read_on": "2026-10-07" },
    { "url": "https://livefromalounge.com/axis-bank-travel-edge-rewards-reshuffle-2026/", "tier": 2, "read_on": "2026-10-07" }
  ],
  "official_source": { "url": "https://www.axis.bank.in/miles-transfer", "status": "page_js_rendered_not_parsed", "read_on": "2026-10-07" },
  "conflicts": [ { "claim": "5:2", "url": "https://cardadvisor.in/articles/axis-edge-rewards-guide-2026", "note": "table appears pre-April-2026" } ]
}
```

### 7c. `partner_currency_value`
```json
{
  "id": "marriott_bonvoy",
  "name": "Marriott Bonvoy",
  "type": "hotel",
  "inr_per_point": {
    "low":     { "value": 0.40, "source_url": "https://cardadvisor.in/programs/marriott-bonvoy", "read_on": "2026-10-07" },
    "typical": { "value": 0.60, "source_url": "https://cardadvisor.in/valuations", "read_on": "2026-10-07" },
    "high":    { "value": 0.90, "source_url": "https://cardexpress.in/articles/award-travel-beginners-guide-india", "read_on": "2026-10-07", "note": "₹1.50–2.50 claimed for aspirational international stays by cardtrail.in Amex guide; not used as 'high' because it needs specific availability" }
  },
  "pricing_model": "dynamic",
  "expiry": { "rule": "24 months inactivity", "status": "unverified" },
  "community_sources": [],
  "refresh": { "cadence_days": 30, "last_refreshed": "2026-10-07", "next_due": "2026-11-06" }
}
```

---

## 8. Unverified / conflicting

1. **HDFC Infinia/DCB redemption rates (₹1 / ₹0.50 / ₹0.30).** Official product page HTML did not expose the "Reward Points Redemption" block to the fetcher (two 100k-char reads); figures come from Paisabazaar/BankBazaar/book1a quoting HDFC and from CardTrail/CardAdvisor. Regalia Gold's official block *was* captured (verified-card-facts.json). Action: headless-render `hdfc.bank.in/credit-cards/infinia-credit-card` or use the SmartBuy portal.
2. **Axis ratios for Magnus (5:1 vs 5:2) and Magnus for Burgundy (5:2 vs 5:4).** Magnify/LFAL/CardTrail/seed file vs CardAdvisor guide table and Pickmycard/Savesage snippets. Official `axis.bank.in/miles-transfer` table is JS-rendered. Action: headless render or Wayback.
3. **Axis EDGE RP Travel EDGE rate.** ~₹0.20 (CardAdvisor) vs ₹0.30–0.50 (CardTrail).
4. **Axis EDGE points expiry.** 3 years from transaction (Axis FAQ via BankBazaar, Pointsmath Feb 2024) vs "2 years of inactivity" (CardTrail Mar 2026). EDGE Miles expiry not found at all.
5. **Axis Atlas sourcing status.** CardAdvisor says "closed to new applicants"; seed-cards.md notes the page still shows Apply.
6. **Amex partner list.** CardTrail (Mar 2026) lists Emirates Skywards and Etihad Guest at 2:1; Magnify (Aug 2026) lists only 7 partners without them. Amex Travel Online ₹/pt not found.
7. **SBI expiry.** 24 months (BankBazaar quoting SBI) vs 3 years (CardTrail). SBI Air India transfer ratio not captured; CardTrail still names Club Vistara (programme merged into Maharaja Club in 2024), so that page is partly stale.
8. **ICICI Air India 1:1 "two cards"** unnamed; Sapphiro/Emeralde expiry assumed to match Emeralde Private.
9. **HSBC TravelOne official page** (`/credit-cards/products/travel-one/`) returned 404; partner table is from Magnify only. TravelOne points expiry not stated.
10. **IndusInd, AU, RBL, Federal, BOBCARD, OneCard, Scapia**: ₹/pt from one aggregator each; expiry (AU/Federal/BOBCARD/OneCard/Scapia) not captured; BOBCARD RP T&C PDF [44] not parsed.
11. **Partner values with conflicts:** Wyndham ₹0.25 vs ₹0.65; Club ITC ₹0.30 vs ₹1.00; United ₹0.50–0.80 vs ₹0.90–1.40 (all within CardAdvisor/CardExpress). Aeroplan: no Indian valuation at all. Taj InnerCircle (non-NeuCoin) points: no value found. Qatar Privilege Club valued only via "Avios ≈ ₹1".
12. **Devaluation counts** are compiled from issuer T&C clauses plus aggregator trackers; CardAdvisor's tracker covers only Axis/HDFC/SBI (9 events) and its "Q2 2026: 174 changes, 149 devaluations" aggregate is market-wide, not per issuer. Counts in §1 should be treated as lower bounds.
13. **Tier-3 community values (r/CreditCardsIndia, TechnoFino)** could not be pulled this pass (Arctic Shift timeouts ×6; Cloudflare). All "community-accepted" figures above are aggregator-sourced.
14. **Kotak/SBI → Accor 2:1** mentioned by CardAdvisor without naming cards.

---

## Sources (all read 7 Oct 2026)

1. HDFC Infinia Rewards Points Program T&C (PDF; text extracted with pdftotext): https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/cards/credit-cards/infinia-credit-card/rewards-points-program-terms-and-conditions.pdf
2. HDFC KFS-cum-MITC v2.5 (Mar 2025), section I "Reward Points and Cashpoints": https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/cards/credit-cards/infinia-credit-card/fees-and-charges/infinia-credit-card-fees-and-charges.pdf
3. CardTrail, Maximize HDFC Reward Points 2026 (updated 27 Feb 2026): https://cardtrail.in/rewards/maximize-hdfc-reward-points-2026/
4. CardAdvisor, HDFC reward points transfer guide (23 Jun 2026, verified 30 Jun 2026): https://cardadvisor.in/articles/hdfc-reward-points-transfer-guide
5. CardAdvisor, HDFC SmartBuy voucher devaluation July 2026 (updated 5 Oct 2026): https://cardadvisor.in/articles/hdfc-smartbuy-voucher-devaluation-july-2026
6. AngelOne, HDFC reward points revised effective 1 Feb 2026: https://oga-prod.angelone.in/news/stocks/hdfc-bank-credit-card-reward-points-revised-effective-february-1-2026
7. Local: `/Users/nithishkumar/cc-smith/docs/research/verified-card-facts.json` (as_of 2026-10-07; Regalia Gold page quote, Millennia T&C quote, Atlas T&C quote); `/Users/nithishkumar/cc-smith/docs/research/seed-cards.md`
8. CardTrail, Axis miles transfer partners 2026 (updated 3 Apr 2026): https://cardtrail.in/news/axis-bank-miles-transfer-partners-2026/
9. CardAdvisor, Axis EDGE rewards guide 2026 (updated 1 Oct 2026): https://cardadvisor.in/articles/axis-edge-rewards-guide-2026
10. CardAdvisor, Valuations (verified 1 Jul–1 Oct 2026): https://cardadvisor.in/valuations
11. Magnify.club, Axis brings back Accor… (23 Sep 2026): https://magnify.club/guides/axis-accor-returns-miles-and-more-september-2026/
12. Live From A Lounge, Axis Travel EDGE rewards reshuffle 2026 (23 Sep 2026): https://livefromalounge.com/axis-bank-travel-edge-rewards-reshuffle-2026/
13. CardTrail, Axis EDGE Rewards program guide (updated 17 Mar 2026): https://cardtrail.in/rewards/axis-edge-rewards-program-guide-india/
14. BankBazaar, Axis credit card reward points (quotes Axis FAQ on 3-year expiry): https://www.bankbazaar.com/axis-bank-credit-card-reward-points.html
15. Pointsmath, When do credit card points expire (15 Feb 2024): https://pointsmath.com/when-do-credit-card-points-expire/
16. DesiDime, Axis devaluation 20 Apr 2024: https://www.desidime.com/news/axis-bank-credit-cards-devalued-atlas-magnus-ace-and-many-more
17. CardInsider, Axis revises charges December 2024: https://cardinsider.com/blog/axis-bank-revises-charges-credit-cards-december/
18. Amex India, Gold Collection redemption page: https://www.americanexpress.com/in/rewards/membership-rewards/redeem-points/gold-collection.html
19. Magnify.club, Amex India transfer partners (18 Aug 2026): https://magnify.club/guides/amex-india-transfer-partners/
20. CardTrail, Amex MR India guide (20 Mar 2026): https://cardtrail.in/rewards/amex-membership-rewards-india-guide/
21. CardAdvisor, Amex MR guide 2026 (updated 25 Sep 2026): https://cardadvisor.in/articles/amex-membership-rewards-guide-2026
22. BankBazaar, SBI credit card reward points (quotes "1 Reward Point = Re. 0.25", ₹99+tax fee, 24-month validity): https://www.bankbazaar.com/sbi-credit-card-reward-points.html
23. CardTrail, SBI reward points guide (updated 19 Mar 2026): https://cardtrail.in/rewards/sbi-reward-points-redemption-guide/
24. CardAdvisor, SBI Aurum review 2026: https://cardadvisor.in/articles/sbi-aurum-credit-card-review-2026
25. Live From A Lounge, ICICI iShop launch (₹1 flights/hotels/vouchers, ₹0.40 statement): https://livefromalounge.com/icici-bank-ishop-launched/
26. Tradebrains, ICICI Emeralde Private Metal (3-year validity, 18,000 cap): https://tradebrains.in/money/icici-emeralde-private-metal-is-this-the-best-luxury-travel-credit-card-in-india/ ; Savesage card page: https://savesage.club/credit-card/icici-emeralde-private-metal
27. CardInsider, ICICI devaluation 15 Nov 2024: https://cardinsider.com/blog/icici-bank-credit-cards-set-major-devaluation/
28. Pickmycard, ICICI devaluation 2026: https://www.pickmycard.in/blog/icici-credit-card-devaluation-2026
29. Paisabazaar, ICICI Emeralde (₹0.25): https://www.paisabazaar.com/icici-bank/icici-bank-emeralde-credit-card/
30. CardTrail, reward point value calculator (updated 13 Mar 2026): https://www.cardtrail.in/calculators/reward-point-value-calculator-india/
31. Magnify.club, HSBC TravelOne review (20 partners, ratios): https://magnify.club/guides/hsbc-travelone-credit-card-review/
32. CardAdvisor, How Accor ALL points work in India 2026: https://cardadvisor.in/articles/how-accor-all-points-work-india-2026 ; Accor transfer guide: https://cardadvisor.in/articles/accor-all-points-transfer-guide
33. IndusInd, Changes in Reward Redemption Program (PDF, effective 1 Sep 2025): https://www.indusind.bank.in/content/dam/indusind-corporate/Other/Changes-in-Reward-Redemption-Program.pdf
34. CardAdvisor, Real point value index India 2026: https://cardadvisor.in/articles/real-point-value-index-india-2026 ; What your points are worth in rupees 2026 (updated 25 Sep 2026): https://cardadvisor.in/articles/what-your-credit-card-points-are-worth-in-rupees-2026
35. Kotak Veer Platinum value chart (1 RP = ₹0.25): https://kotak.com/en/personal-banking/cards/credit-cards/veer-platinum-credit-card/value-chart.html
36. Free Press Journal, Kotak reward cuts from 1 Jun 2025: https://www.freepressjournal.in/amp/business/kotak-credit-cards-to-face-reward-cuts-higher-fees-from-june-1-changes-affect-many-cardholders
37. CardAdvisor, YES Marquee: https://cardadvisor.in/cards/yes-marquee
38. CardAdvisor, AU Zenith / Zenith+: https://cardadvisor.in/cards/au-zenith ; https://cardadvisor.in/articles/au-zenith-plus-credit-card-review-2026
39. CardInsider, AU revises reward usage T&C: https://cardinsider.com/blog/au-bank-revises-its-credit-cards-reward-points-usage-terms-conditions/
40. Standard Chartered Ultimate product PDF: https://www.sc.com/global/av/in-ultimate-cc-final.pdf ; CardInsider: https://cardinsider.com/standard-chartered/standard-chartered-ultimate-credit-card/
41. CardAdvisor, Federal Celesta review 2026: https://cardadvisor.in/articles/federal-bank-celesta-credit-card-review-2026
42. Scapia blog (BOBCARD): https://www.scapia.cards/product/blog/the-scapia-bobcard-credit-card-everything-you-need-to-know ; Cardmaven Scapia review: https://cardmaven.in/scapia-credit-card-review/
43. Pickmywork, BOB credit cards 2026 (Eterna ₹0.25): https://www.pickmywork.com/?p=6766
44. BOBCARD reward points T&C 2024 (PDF, not parsed): https://media.bobcard.co.in//media/ioxnz3mm/reward-points-important-terms-conditions-2024.pdf
45. OneCard rewards blog: https://getonecard.app/blog/onecard-credit-card-rewards/ ; CardInsider OneCard: https://cardinsider.com/fintech-cards/onecard-credit-card/
46. CardAdvisor, Marriott Bonvoy programme page: https://cardadvisor.in/programs/marriott-bonvoy
47. CardExpress, Award travel beginner's guide (25 Apr 2026; TPG April 2026 valuations at ₹84/USD): https://cardexpress.in/articles/award-travel-beginners-guide-india
48. Live From A Lounge, Marriott dynamic pricing for Indian hotels (Apr 2022, updated Sep 2023): https://livefromalounge.com/marriott-bonvoy-here-is-how-many-extra-marriott-bonvoy-points-you-should-expect-to-pay-for-the-indian-hotels-under-marriotts-new-dynamic-pricing/
49. Tata Digital support, value of 1 NeuCoin: https://support.tatadigital.com/support/solutions/articles/81000406245-what-is-the-value-of-1-neucoin-
50. CardAdvisor, Air India Maharaja Club guide: https://cardadvisor.in/articles/air-india-maharaja-club-guide
51. Air India, Maharaja Club enhancements (2026 award chart): https://www.airindia.com/in/en/maharaja-club/updates/maharaja-club-enhancements.html
52. CardTrail, IndiGo BluChips worth it? (updated 7 Mar 2026): https://cardtrail.in/travel/indigo-bluchips-worth-it-india/
53. TheFlightClub, How BluChip works (Aug 2026): https://www.theflightclub.it/en/2026/08/how-bluchip-the-indigo-loyalty-program-works/amp/
54. CardAdvisor, KrisFlyer programme page: https://cardadvisor.in/programs/singapore-airlines-krisflyer
55. Live From A Lounge, miles & points buying opportunities (13 Jun 2026): https://livefromalounge.com/miles-and-points-buying-opportunities-june-13-2026/
56. AwardWallet, IHG One Rewards (≈0.69¢/pt): https://awardwallet.com/hotels/ihg-one-rewards/qatar-aiways-partnership/
57. CardAdvisor, Loyalty programmes index: https://cardadvisor.in/programs
58. CardAdvisor, Credit card devaluation tracker 2025–26 (updated 25 Sep 2026): https://cardadvisor.in/articles/credit-card-devaluation-tracker-india-2025-2026 ; CardAdvisor devaluations study 2026: https://cardadvisor.in/articles/credit-card-devaluations-india-study-2026
