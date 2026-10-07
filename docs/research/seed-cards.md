# Seed cards: the 20 most popular Indian credit cards (as of 6 Oct 2026)

Purpose: the first set of cards that cc-smith profiles by hand (features.md "Phase 1 — about 30 hand-verified cards"). It records each card's popularity evidence and the **official sources** to profile it from. The machine-readable allow-list is in `official-domains.yaml`, in this folder.

Fees below are copied from the issuer's own page or KFS/MITC as fetched on 6 Oct 2026. They are **not** profile data. Re-extract them through the A6 pipeline before use. "—" means not found on an official page. Nothing here was taken from aggregator sites.

---

## 0. Read this first: domain migration

RBI made Indian banks move to `.bank.in` (deadline 31 Oct 2025). Verified on 6 Oct 2026 with `curl`, every bank's old domain now **301-redirects** to its new one:

| Old | Now (canonical) |
|---|---|
| hdfcbank.com | **hdfc.bank.in** |
| icicibank.com | **icici.bank.in** |
| axisbank.com | **axis.bank.in** (also `campaign.axis.bank.in` for PDFs) |
| kotak.com | **kotak.bank.in** (kotak.com still serves pages; `images.kotak.com` hosts some PDFs) |
| idfcfirstbank.com | **idfcfirst.bank.in** |
| aubank.in | **au.bank.in** (behind Cloudflare: blocks curl and WebFetch with 403) |
| hsbc.co.in | **hsbc.bank.in** |
| yesbank.in | **yes.bank.in** |
| federalbank.co.in | **federal.bank.in** |
| indusind.com | **indusind.bank.in** |
| rblbank.com | **rbl.bank.in** |

SBI Card is an NBFC, not a bank, so it stays on **sbicard.com**. Community posts and older PDFs still link to the old domains. The allow-list must accept both and normalise to the new one.

---

## 1. How the 20 were picked

**Evidence used, strongest first:**
1. **Cards outstanding by issuer** (RBI monthly bank-wise card statistics, as reported in the press): June 2026 — HDFC 26.7M (22.0%), SBI Card 22.6M (18.6%), ICICI 19.5M (16.1%), Axis 16.2M (13.3%). The top four hold about 70% of 121.6M cards. Spend share: HDFC 27.2%, ICICI 19.9%, SBI Card 17.7%, Axis 9.3%. Primary source to re-pull: https://www.rbi.org.in/Scripts/ATMView.aspx (verified 200). Press summaries: https://www.angelone.in/news/economy/india-s-credit-card-market-hits-119-million-psu-banks-report-stronger-spending-growth , https://www.kotakneo.com/news/personal-finance/india-credit-card-additions-june-2026-hdfc-bank-sbi-cards-icici/ , https://www.grabon.in/indulge/finance/credit-card-statistics/ (weak).
2. **Issuer-announced card-level issuance** (the only card-level numbers in public): Amazon Pay ICICI was the fastest co-brand to 1M and then 2M cards (2021). Flipkart Axis passed 2M cards in force (2022). Tata Neu HDFC passed 2M (Mar 2025) and was >13% of India's net new cards in Q3 FY25.
3. **Community salience** from this repo's sweeps (`reddit-creditcardsindia-pain-points.md`, `technofino-pain-points.md`): which cards appear in the year's most-upvoted threads and devaluation threads.
4. **2026 news volume** on devaluations and launches (aggregators, used only as weak evidence of attention).

**What could not be measured:**
- **Per-card Reddit mention counts.** I tried title-match counts over the Arctic Shift archive API. It returned "Timeout. Maybe slow down a bit" on nearly every request on 6 Oct 2026, and the run yielded only one partial number (Infinia ≥276 titles, Apr–Oct 2026). PullPush returns 429 to agents.
- **TechnoFino forum thread counts** (Cloudflare 403).
- **Google Trends** (no access).

The rank is therefore a judgement over the evidence above, not a measured order. Re-rank when mention counts can be pulled; the counter script is described in §5.

**Coverage rules applied:**
- Issuers: HDFC ×5, SBI Card ×3, Axis ×4, ICICI ×2, IDFC FIRST, Kotak, AU, HSBC, plus two fintech co-brands (Scapia on Federal/BOBCARD/Axis, Kiwi on YES Bank).
- Every archetype is covered: cashback, shopping co-brands, food co-brand, telecom/utility, travel/premium, lifetime-free/entry, fuel, and RuPay-on-UPI.

---

## 2. The 20

Legend:
- **UPI** = a RuPay variant exists that links to UPI apps. "✔ conf." means confirmed on the issuer page, "✔ rep." means reported only, "✘" means none known, "?" means unverified.
- **Fee** = joining / renewal fee, excluding GST, followed by the renewal waiver condition.

| # | Card (exact name) | Issuer | Network(s) | UPI | Archetype | Fee (official) | Recent status |
|---|---|---|---|---|---|---|---|
| 1 | Amazon Pay ICICI Bank Credit Card | ICICI Bank | Visa (rep.) | ✘ | Shopping co-brand, lifetime free | Nil / Nil | Jan 2026 fees on wallet/gaming/transport; exclusions widened Oct 2025; forex markup cut to 1.99% |
| 2 | Tata Neu Infinity HDFC Bank Credit Card (+ Tata Neu Plus) | HDFC Bank | RuPay, Visa | ✔ conf. (NeuCoins on UPI PDF) | Shopping co-brand + UPI | Infinity ₹1,499 / ₹1,499, waived at ₹3L. Plus ₹499 / ₹499, waived at ₹1L | 2026: lounge gated behind quarterly spend; UPI rounding complaints |
| 3 | HDFC Bank Millennia Credit Card | HDFC Bank | Visa/Mastercard (rep.) | ? | Cashback, entry | ₹1,000 / ₹1,000, waived at ₹1L | New T&C dated 20 Jul 2026 (`millennia-tnc-20th-jul26.pdf`) |
| 4 | Cashback SBI Card | SBI Card | Visa (rep.) | ✘ | Online cashback | ₹999 / ₹999, waived at ₹2L (KFS) | **Devalued 1 Apr 2026**: cap ₹4,000/cycle split ₹2k online + ₹2k offline; gaming/toll/govt excluded |
| 5 | Flipkart Axis Bank Credit Card | Axis Bank | Visa/Mastercard (rep.) | ✘ | Shopping co-brand | Joining Nil (limited offer) / ₹500, waived at ₹3.5L | Lounge removed Jun 2025; Myntra 7.5%; T&C changed 28 Aug 2026 (toll excluded, DCC 3.5%). New sibling: Flipkart Axis Bank **Super Elite** |
| 6 | HDFC Bank INFINIA Credit Card (Metal Edition) | HDFC Bank | Visa/Mastercard (rep.) | ✘ | Super-premium rewards | ₹12,500 / ₹12,500, waived at ₹10L (page) | Feb 2026: **retention needs ₹18L spend or ₹50L relationship value**, reviewed Apr 2027. Jan 2026 SmartBuy cut rolled back; redemption frequency capped |
| 7 | HDFC Bank Regalia Gold Credit Card | HDFC Bank | Visa/Mastercard (rep.) | ✘ | Premium travel/lifestyle | ₹2,500 / ₹2,500, waived at ₹4L | **Devalued 15 May 2026** (base earn); lounge gated by ₹60k/quarter from Jul 2026 |
| 8 | Axis Bank Atlas Credit Card | Axis Bank | Visa (rep.) | ✘ | Travel miles | ₹5,000 / ₹5,000 | **Devalued 2 Apr 2026**: Accor/Marriott/Qatar removed as transfer partners. Aggregators say new sourcing stopped (**unverified**; page still live with Apply) |
| 9 | Axis Bank Magnus Credit Card (+ Magnus for Burgundy) | Axis Bank | Visa/Mastercard (rep.) | ✘ | Super-premium | Magnus ₹12,500, waived at ₹25L. Burgundy ₹30,000, waived at ₹30L | **Devalued 2 Apr 2026** (transfer ratio 5:2→5:1; Burgundy 5:4→5:2). LTF for new Burgundy Salary accounts from 1 Jul 2026 |
| 10 | Swiggy BLCK HDFC Bank Credit Card / Swiggy ORNGE HDFC Bank Credit Card | HDFC Bank | Mastercard (BLCK conf.) | ? | Food-delivery co-brand | BLCK ₹1,000 / ₹1,000 (joining waived on ₹75k in 90 days), waived at ₹2L. ORNGE ₹500 / ₹500, waived at ₹1.5L | **Relaunched** 12 Mar 2026 as two variants. Old Swiggy HDFC stopped new sourcing 10 Feb 2026 and existing holders continue. T&C dated 22 Sep 2026 |
| 11 | Airtel Axis Bank Credit Card | Axis Bank | Mastercard (rep.) | ✘ | Telecom/utility cashback | ₹500 / ₹500, waived at ₹2L | **Devalued 12 Apr 2026**: lounge removed; Airtel/utility cap now dynamic (tied to 1% spends); 10% partners now Blinkit/Zomato/District. T&C update 28 Aug 2026 |
| 12 | SimplyCLICK SBI Card | SBI Card | Visa/Mastercard (rep.) | ? | Entry online-shopping | ₹499 / ₹499, waived at ₹1L (sbicard.com; KFS table ambiguous) | 2026 SBI-wide rule changes |
| 13 | IDFC FIRST Millennia Credit Card | IDFC FIRST Bank | Visa + **FIRST Digital RuPay add-on** (conf.) | ✔ conf. | Lifetime-free entry | Nil / Nil (page) | 2026 devaluations: FASTag/rail 1X (Jan); 24-month point expiry and earn capped at the credit limit (18 Jun) |
| 14 | HSBC Live+ Credit Card | HSBC India | Visa (Visa Infinite, conf.) | ✘ (HSBC RuPay Cashback is a separate card) | Dining/grocery cashback | ₹999 / ₹999, waived above ₹2L | **Revamped 26 Jul 2026**: 10% bucket wider, cap ₹1,200/month; lounge 4→2 domestic + 1 international; forex 1.99% |
| 15 | Scapia Federal Bank Credit Card (also Scapia BOBCARD; **Scapia Axis Bank** launched 3 Sep 2026) | Federal Bank / BOBCARD / Axis Bank (fintech: Scapia) | Visa (Federal), Mastercard (Axis), RuPay companion | ✔ conf. (RuPay card for UPI) | Travel, lifetime free, zero forex | Zero joining/annual (scapia.cards) | Multi-issuer since 2026; Federal credit-limit cuts reported earlier |
| 16 | ICICI Bank Coral Credit Card (incl. Coral RuPay) | ICICI Bank | Visa, Mastercard, RuPay (RuPay conf.) | ✔ conf. (ICICI RuPay page) | Entry rewards + UPI | ₹500 / ₹500, waived above ₹1.5L | — |
| 17 | BPCL SBI Card OCTANE | SBI Card | Visa (rep.) | ? | Fuel | ₹1,499 / ₹1,499, waived at ₹2L (KFS) | — |
| 18 | Kiwi RuPay Credit Card (YES BANK) | YES Bank (fintech: Kiwi) | RuPay | ✔ (UPI-only product) | RuPay-on-UPI, lifetime free | Lifetime free (gokiwi.in; issuer page **unverified**) | Neon paid tier ₹999/yr (fintech claim) |
| 19 | AU Bank LIT Credit Card | AU Small Finance Bank | ? (verify) | ? | Customisable, lifetime free | Lifetime free (au.bank.in, per search snippet; page blocks bots) | 10 Apr 2026: no points on transport MCCs bank-wide; lounge spend gate ₹50k/quarter |
| 20 | Kotak League Platinum Credit Card | Kotak Mahindra Bank | ? (verify) | ✘ (Kotak UPI RuPay is a separate card) | Entry rewards (Myntra Kotak holders migrated here, Jul 2025) | ₹499 or Nil (two variants) / ₹499 or Nil, waived at ₹50k | — |

### Bench: next in line, or swap-ins
- **Axis Bank ACE** (₹499; cashback; heavily discussed, devalued).
- **HDFC Diners Club Black Metal**.
- **ICICI Sapphiro / Emeralde Private Metal**.
- **Tata Neu Infinity SBI Card**.
- **PhonePe SBI Card PURPLE / SELECT BLACK** (RuPay; "10% only on first txn per category" complaint).
- **IndianOil HDFC Bank** (₹500) and **IndianOil Axis** (fuel).
- **Kotak Cashback+** (₹750; RuPay variant earns 0.5% on UPI; Prime variant launched 8 May 2026).
- **ixigo AU** (lifetime free, zero forex).
- **IDFC FIRST Wealth / Select** (lifetime free).
- **HSBC TravelOne**.
- **IndusInd** cards.
- **Flipkart SBI Card**.

All are needed to reach the ~30 in features.md Phase 1.

---

## 3. Per-card notes and official sources

All URLs were HTTP-checked on 6 Oct 2026 unless marked **(unverified)**. Product page = the issuer's canonical page. "Docs" = MITC, KFS, T&C and fee PDFs found linked from that page.

### 1. Amazon Pay ICICI Bank Credit Card — ICICI Bank
- **Popularity:**
  - Fastest co-brand to 1M cards: https://www.icici.bank.in/about-us/news-room/2020/news-amazon-pay-icici-bank-credit-card-is-fastest-to-cross-1-million-milestone
  - Fastest to 2M: https://www.icici.bank.in/about-us/news-room/2021/news-amazon-pay-icici-bank-credit-card-onboards-over-two-million-customers
  - Reddit: "6th rejection for Amazon Pay ICICI" (226↑) https://www.reddit.com/r/CreditCardsIndia/comments/1q7ge7s ; erroneous-rejection compensation (1124↑).
- **Product page:** https://www.icici.bank.in/personal-banking/cards/credit-card/amazon-pay-credit-card (200). Lists "No Joining Fee / No Annual Fee / Forex 1.99%".
- **Docs:**
  - MITC: https://www.icici.bank.in/content/dam/icicibank/india/managed-assets/revamp-page-images/docs/pdf/mitc-cc-gk-t.pdf (200, PDF)
  - Card T&C: https://www.icici.bank.in/content/dam/icicibank/india/managed-assets/revamp-page-images/docs/pdf/tc-for-amazon-pay-credit-card.pdf (200, PDF)
- **Notes:** The best "first card" candidate, but approval is hard (rejection threads). Cashback depends on Amazon Prime status. Exclusions list is long.

### 2. Tata Neu Infinity HDFC Bank Credit Card (and Tata Neu Plus) — HDFC Bank
- **Popularity:**
  - >2M issued; >13% of net new cards in Q3 FY25: https://www.business-standard.com/industry/banking/tata-neu-hdfc-bank-cobranded-card-surpasses-2-million-issuances-125032701117_1.html , https://yourstory.com/2025/03/tata-neu-hdfc-bank-credit-card-crosses-2m-issuances
  - Reddit "1.5% on UPI that quietly becomes 0%" (252↑) https://www.reddit.com/r/CreditCardsIndia/comments/1pcfiy1
- **Product pages:**
  - Infinity: https://www.hdfc.bank.in/credit-cards/tata-neu-infinity-hdfc-bank-credit-card (200)
  - Infinity fees: https://www.hdfc.bank.in/credit-cards/tata-neu-infinity-hdfc-bank-credit-card/fees-and-charges (200)
  - Plus: https://www.hdfc.bank.in/credit-cards/tata-neu-plus-hdfc-bank-credit-card (200)
- **Docs** (base `https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/cards/credit-cards/`):
  - Infinity T&C `tata-neu-infinity-credit-card/pdf/tata_neu_infinity_card_tnc.pdf` (200)
  - UPI NeuCoins `tata-neu-infinity-credit-card/pdf/additional-upi-neucoins-infinity.pdf`
  - Plus T&C `tata-neu-plus-hdfc-bank-credit-card/pdfs/tata_neu_plus_card_tnc.pdf`
  - Common HDFC MITC `personal-mitc/mitc-in-english.pdf` (200)
- **Notes:** The joining fee is levied on day 120. SBI Card issues parallel Tata Neu Infinity/Plus SBI cards on the same NeuCoin ecosystem (bench). UPI rounding per transaction matters (A2).

### 3. HDFC Bank Millennia Credit Card — HDFC Bank
- **Popularity:** HDFC is the largest issuer (22% of cards). Millennia is its mass cashback card and appears in most recommendation threads (qualitative).
- **Product page:** https://www.hdfc.bank.in/credit-cards/millennia-credit-card (200)
  - Fees page: https://www.hdfc.bank.in/credit-cards/millennia-credit-card/fees-and-charges
- **Docs:**
  - KFS-cum-MITC: https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/cards/credit-cards/millennia-credit-card/fees-and-charges/pdf/part-i-key-fact-statement-cum-most-important-terms-and-conditions-for-credit-cards.pdf (200)
  - Current T&C: …/millennia-credit-card/pdf/millennia-tnc-20th-jul26.pdf (200)
  - Older T&C: …/millennia-tnc-25th%20apr%2725.pdf — keep it for diffing
  - Milestone program: …/millennia-credit-card/pdf/quarterly-spends-milestone-program.pdf
- **Notes:** The Jul-2026 T&C file implies a rule change. Diff the two T&Cs before profiling. Whether a RuPay variant exists is unverified.

### 4. Cashback SBI Card — SBI Card
- **Popularity:**
  - "RIP SBI Cashback credit card" (1031↑) https://www.reddit.com/r/CreditCardsIndia/comments/1rgxk7y
  - MCC mis-tag thread (580↑) https://www.reddit.com/r/CreditCardsIndia/comments/1u4wg9u
  - Devaluation coverage: https://cardtrail.in/news/sbi-card-april-2026-rule-changes/
- **Product page:** https://www.sbicard.com/en/personal/credit-cards/cashback-sbi-card.html (200; content is JS-rendered, so fees are not in the HTML).
- **Docs:**
  - KFS (all cards, fee table): https://www.sbicard.com/sbi-card-en/assets/docs/pdf/kfs/key-fact-statement.pdf (200)
  - MITC: https://www.sbicard.com/sbi-card-en/assets/docs/pdf/most-important-terms-and-conditions/mitc-english.pdf (200)
  - MITC index: https://www.sbicard.com/en/most-important-terms-and-conditions.page
  - Notices: https://www.sbicard.com/en/customer-notices.page (200)
  - Card-specific T&C PDF: not found **(gap)**
- **Notes:** The scraper needs a headless browser for sbicard.com product pages. The page's data JSON (`/templatedata/product/card/data/en/personal/cashback-sbi-card.json`) returns 404 when fetched directly.

### 5. Flipkart Axis Bank Credit Card — Axis Bank
- **Popularity:**
  - 2M cards in force: https://www.axis.bank.in/about-us/press-releases/flipkart-axis-bank-credit-card-surpasses-2-million-users (search result; the axisbank.com twin redirects)
  - TechnoFino co-brand-conflict rejections thread.
- **Product page:** https://www.axis.bank.in/cards/credit-card/flipkart-axisbank-credit-card (200)
  - Super Elite variant: https://www.axis.bank.in/cards/credit-card/flipkart-axis-bank-super-elite-credit-card
- **Docs** (base `https://www.axis.bank.in/docs/default-source/default-document-library/`):
  - T&C `terms-and-conditions-flipkart-axis-bank-credit-card.pdf` (200)
  - Cashback T&C `cashback-tncs---final.pdf`
  - Preferred merchants `flipkart-axis-bank-credit-card-preferred-merchants.pdf`
  - Axis MITC `mitc-credit-cards.pdf` (200)
  - Schedule of charges `credit-card/sosc-credit-cards.pdf` (200)
- **Notes:** The page says "T&C updated w.e.f. 28 Aug '26". Use the post-change version.

### 6. HDFC Bank INFINIA Credit Card (Metal Edition) — HDFC Bank
- **Popularity:**
  - Most-discussed premium card. Reddit ₹18L threads (666↑, 585↑): https://www.reddit.com/r/CreditCardsIndia/comments/1rebss6 , https://www.reddit.com/r/CreditCardsIndia/comments/1sl97iv
  - Retention rule: https://www.businesstoday.in/amp/personal-finance/banking/story/hdfc-tightens-infinia-norms-infinia-cardholders-must-spend-rs-18-lakh-or-hold-rs-50-lakh-to-retain-benefits-518234-2026-02-26
- **Product page:** https://www.hdfc.bank.in/credit-cards/infinia-credit-card (200)
  - Fees page: https://www.hdfc.bank.in/credit-cards/infinia-credit-card/fees-and-charges
- **Docs:**
  - Fees PDF: …/infinia-credit-card/fees-and-charges/infinia-credit-card-fees-and-charges.pdf (200)
  - Reward program T&C: …/infinia-credit-card/rewards-points-program-terms-and-conditions.pdf (200)
  - Lounge program: …/infinia-credit-card/airport-lounge-access-program-30sep2025.pdf
  - Common MITC (above)
- **Notes:** By invite only. The fees page also shows a ₹10,000 variant (Infinia non-metal/legacy), so verify which variant each fee row belongs to. Model the ₹10L fee waiver and the ₹18L retention criterion as **separate** fields.

### 7. HDFC Bank Regalia Gold Credit Card — HDFC Bank
- **Popularity:**
  - "Infinia and regalia guys" thread https://www.reddit.com/r/CreditCardsIndia/comments/1qlfodr
  - May 2026 devaluation coverage: https://tradebrains.in/money/list-of-major-credit-cards-in-india-devalued-in-2026-airtel-axis-regalia-more/
- **Product page:** https://www.hdfc.bank.in/credit-cards/regalia-gold-credit-card (200)
  - Fees page: https://www.hdfc.bank.in/credit-cards/regalia-gold-credit-card/fees-and-charges
- **Docs:**
  - **Feature-change notice:** https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/common/Credit-Cards/Regalia-Gold-Product-feature-change.pdf
  - T&C: …/regalia-gold-credit-card/terms-and-conditions.pdf (200)
  - Reward T&C: …/regalia-gold-credit-card/pdfs/regalia-gold-credit-card-reward-points-t-and-cs.pdf
  - Lounge: …/regalia-gold-credit-card/pdfs/lounge-t-and-cs-and-list-Regalia-Gold.pdf
  - Fee PDF: …/regalia-gold-credit-card/fees-and-charges/rgc2.pdf
- **Notes:** The `/pdf/common/Credit-Cards/*feature-change*.pdf` path is HDFC's change-notice pattern. Watch it (A7).

### 8. Axis Bank Atlas Credit Card — Axis Bank
- **Popularity:**
  - TechnoFino milestone/miles-not-credited threads (e.g. https://technofino.in/community/threads/axis-atlas-milestone-benefit.16600/)
  - April 2026 devaluation coverage: https://cardtrail.in/news/axis-atlas-discontinued-2026/ (claims sourcing stopped; **unverified**)
- **Product page:** https://www.axis.bank.in/cards/credit-card/axis-bank-atlas-credit-card (200). Sub-pages: `/rewards-benefits`, `/tiered-benefits`, `/privileges`.
- **Docs:**
  - …/credit-cards/terms-and-conditions-atlas-credit-card.pdf (200)
  - …/credit-cards/terms-and-conditions-of-features-of-axis-bank-atlas-credit-card.pdf
  - Axis MITC
- **Notes:** Page shows fee ₹5,000 + GST and "DCC revised w.e.f. 21 Aug 2026 — 3.5%". Transfer partners and ratios belong in A5, with an effective date of 2 Apr 2026.

### 9. Axis Bank Magnus Credit Card (+ Magnus for Burgundy) — Axis Bank
- **Popularity:**
  - Magnus MCC thread (111↑) https://www.reddit.com/r/CreditCardsIndia/comments/1v1cvkg
  - TechnoFino rent-milestone thread (10 pages)
  - Burgundy LTF news: https://cardinsider.com/blog/axis-bank-waives-joining-annual-fees-magnus-horizon-credit-cards-select-burgundy-customers/
- **Product page:** https://www.axis.bank.in/cards/credit-card/axis-bank-magnus-credit-card (200)
- **Docs:**
  - Magnus MITC: https://www.axis.bank.in/docs/default-source/magnus-card/mitc-credit-cards.pdf (200)
  - Magnus T&C: …/credit-cards/magnus-credit-card-terms-and-conditions.pdf (200)
  - Burgundy T&C: …/credit-cards/magnus-for-burgundy-terms-and-conditions.pdf
  - Burgundy-salary LTF: https://campaign.axis.bank.in/generic/terms-and-conditions-for-magnus-credit-card-ltf-for-burgundy-salary-customers.pdf
- **Notes:** Two variants with different fees, waivers and transfer ratios, so make two profiles.

### 10. Swiggy BLCK / Swiggy ORNGE HDFC Bank Credit Card — HDFC Bank
- **Popularity:**
  - "HDFC Swiggy discontinued" (725↑) https://www.reddit.com/r/CreditCardsIndia/comments/1r1xlj0
  - Refund-cap thread (493↑) https://www.reddit.com/r/CreditCardsIndia/comments/1qybdiq
  - Relaunch: https://cardinsider.com/blog/hdfc-bank-launches-swiggy-ornge-swiggy-blck-credit-cards/ , https://www.swiggy.com/swiggy-hdfc-bank-credit-card
- **Product pages:**
  - BLCK: https://www.hdfc.bank.in/credit-cards/swiggy-blck-hdfc-bank-credit-card (200)
  - ORNGE: https://www.hdfc.bank.in/credit-cards/swiggy-ornge-hdfc-bank-credit-card (200)
  - Legacy: https://www.hdfc.bank.in/credit-cards/swiggy-hdfc-bank-credit-card (still in sitemap)
- **Docs:**
  - BLCK T&C 22-09-2026: …/swiggy-blck-hdfc-bank-credit-card/pdf/tncs-swiggy-blck-hdfc-bank-credit-card-22092026.pdf (200)
  - Combined T&C: …/swiggy-blck-hdfc-bank-credit-card/pdf/combined-tncs-ornge-and-blck.pdf (200)
  - ORNGE T&C: …/swiggy-ornge-hdfc-bank-credit-card/pdf/tncs-swiggy-ornge-hdfc-bank-credit-card-22092026.pdf
  - Card member agreement: …/pdf/card-member-agreement-swiggy.pdf
- **Notes:** Three profiles: legacy (existing holders only), BLCK, ORNGE. Aggregator reports say the legacy card needs ≥₹249 per Swiggy transaction from 17 Apr 2026; this is unverified.

### 11. Airtel Axis Bank Credit Card — Axis Bank
- **Popularity:**
  - Devaluation threads (800↑, 781 comments) https://www.reddit.com/r/CreditCardsIndia/comments/1rpplp7 ; (613↑) https://www.reddit.com/r/CreditCardsIndia/comments/1rpsctn
  - https://cardtrail.in/news/airtel-axis-credit-card-devaluation-2026/
- **Product page:** https://www.axis.bank.in/cards/credit-card/airtel-axis-bank-credit-card (200)
- **Docs:**
  - …/credit-cards/axis-bank-airtel-terms-and-conditions.pdf (200)
  - …/credit-cards/terms-and-conditions-for-cashback-for-airtel-axis-bank-credit-card.pdf
  - …/terms-and-conditions-for-airtel-cbcc-cvp.pdf
  - Axis MITC
- **Notes:** The dynamic cap (accelerated cashback limited by 1%-category spend) is a good test case for the engine's cap model.

### 12. SimplyCLICK SBI Card — SBI Card
- **Popularity:** The standard entry/online card in beginner threads (qualitative). SBI Card is the #2 issuer.
- **Product page:** https://www.sbicard.com/en/personal/credit-cards/simplyclick-sbi-card.html (200; JS-rendered)
- **Docs:**
  - T&C/MITC booklet: https://www.sbicard.com/sbi-card-en/assets/docs/pdf/simply-click-tnc-MITC-booklet.pdf (200; check its date)
  - SBI KFS and MITC (above)

### 13. IDFC FIRST Millennia Credit Card — IDFC FIRST Bank
- **Popularity:**
  - IDFC devaluation thread ("3rd devaluation in less than a year") https://technofino.in/community/threads/idfc-reward-reduced-to-1x-for-utility.15453/
  - Recommended in lifetime-free/first-card threads.
- **Product page:** https://www.idfcfirst.bank.in/credit-card/millennia (200). The page states "Lifetime-free", "Joining and Annual Fees NIL" and offers a "FIRST Digital RuPay" add-on linked to UPI.
- **Docs:**
  - MITC: https://www.idfcfirst.bank.in/content/dam/idfcfirstbank/pdf/credit-card/MITC-Document-Customer.pdf (200)
  - Travel & shop T&C: …/pdf/credit-card/first-millennia-tnc-travel-and-shop.pdf
  - Privileges: https://www.idfcfirst.bank.in/content/dam/IDFCFirstBank/credit-cards/FIRSTMillenniaCreditCard/FIRST-Millennia-Privileges.pdf
  - May 2026 change notice (Wealth; same pattern): https://www.idfcfirst.bank.in/content/dam/idfcfirstbank/pdf/credit-card/FIRST-Wealth-Credit-Card-Communication-May-26.pdf (200)
- **Notes:** IDFC page fee snippets mix promos for other cards (₹199, ₹499), so extract only from the card's own fee block. Siblings that share the MITC: Select (`/credit-card/select`), Wealth (`/credit-card/wealth`), and Power/Power+ (`/credit-card/hpcl-power-fuel-credit-card`, fuel, ₹199/₹499).

### 14. HSBC Live+ Credit Card — HSBC India
- **Popularity:**
  - "Influencers hyped HSBC cards… reality is very different" (132↑) https://www.reddit.com/r/CreditCardsIndia/comments/1sew2dp
  - https://livefromalounge.com/hsbc-is-becoming-one-of-indias-most-relevant-credit-card-issuers-again/
- **Product page:** https://www.hsbc.bank.in/credit-cards/products/live-plus/ (200)
- **Docs** (base `https://www.hsbc.bank.in/content/dam/hsbc/in/documents/`):
  - KFS `credit-card-key-fact-statement.pdf` (200)
  - MITC `platinum_mostimp_tnc.pdf` (200; filename says "platinum", so confirm it covers Live+)
  - Services guide `credit-cards/live-plus-credit-card-services-guide.pdf`
  - Cashback T&C `credit-cards/visa-cashback/terms-and-condition.pdf`
- **Notes:** The Jul 2026 changes cut both ways (wider 10% bucket, less lounge). Good test of "pending change" handling.

### 15. Scapia credit card (Federal Bank / BOBCARD / Axis Bank) — fintech co-brand
- **Popularity:**
  - Frequent in zero-forex and lifetime-free travel recommendations.
  - Axis launch: https://www.businesstoday.in/personal-finance/news/story/axis-bank-scapia-credit-card-goes-live-check-lounge-access-upi-rewards-forex-benefits-and-fees-553384-2026-09-05
  - Add-on launch: https://www.scapia.cards/newsroom/scapia-and-federal-bank-launch-a-first-of-its-kind-add-on-credit-card-empowering-users-to-share-credit-and-travel-privileges-with-complete-independence
- **Product pages:**
  - Scapia (partner, not issuer): https://www.scapia.cards/ (200)
  - Axis: https://www.axis.bank.in/cards/credit-card/scapia-axis-bank-credit-card (200; title "Scapia Axis Bank Credit Card - Zero Fee Travel Credit Card")
- **Docs** (all linked from scapia.cards):
  - Federal MITC https://www.federal.bank.in/documents/d/guest/mitc_v11-30_04_26 (200)
  - Federal KFS https://www.federal.bank.in/documents/d/guest/kfs_v11-30_04_26 (200)
  - BOBCARD MITC https://media.bobcard.co.in//media/wldj0y5t/bobcard-scapia-mitc-1.pdf
  - BOBCARD KFS https://media.bobcard.co.in//media/gj3mfwnu/bobcard-scapia-kfs-1.pdf
  - BOBCARD T&C https://media.bobcard.co.in//media/atehw542/bobcard-scapia-tc.pdf
  - Axis: MITC/SOSC as above
  - Cardholder agreements on `res.cloudinary.com/scapiacards/...` (CDN, **treat as partner-hosted**)
- **Notes:** One product with three issuers, so profile one card per issuer. The scapia.cards rewards copy is a partner claim; prefer the issuer MITC. The BOBCARD links are **unverified** (not HTTP-checked).

### 16. ICICI Bank Coral Credit Card (incl. Coral RuPay) — ICICI Bank
- **Popularity:** ICICI is the #3 issuer and led new issuance in Apr 2026 (https://oga-prod.angelone.in/news/market-updates/icici-bank-leads-new-credit-card-issuance-in-april-2026-amid-heavy-competition). Coral is ICICI's default entry card and its RuPay-on-UPI flagship.
- **Product pages:**
  - Coral: https://www.icici.bank.in/personal-banking/cards/credit-card/coral-credit-card (200)
  - RuPay hub: https://www.icici.bank.in/personal-banking/cards/credit-card/rupay-credit-card (200; lists Coral, HPCL Super Saver, Rubyx, Sapphiro RuPay fees)
- **Docs:**
  - MITC: https://www.icici.bank.in/content/dam/icicibank/india/managed-assets/revamp-page-images/docs/pdf/mitc_cc.pdf (200)
  - T&C: …/revamp-page-images/docs/pdf/tnc_english.pdf
- **Notes:** The Coral page shows forex markup of 3.5%.

### 17. BPCL SBI Card OCTANE — SBI Card
- **Popularity:** SBI's flagship fuel card. Fuel is a core archetype (TechnoFino "fuel excluded on UPI" threads). It was picked over IndianOil HDFC/Axis to balance issuers.
- **Product page:** https://www.sbicard.com/en/personal/credit-cards/bpcl-sbi-card-octane.html (200; JS-rendered). Base variant: …/bpcl-sbi-card.html
- **Docs:** SBI KFS (OCTANE ₹1,499, waived at ₹2L) and MITC (above). Card-specific T&C not found **(gap)**.

### 18. Kiwi RuPay Credit Card (YES BANK) — YES Bank, via Kiwi
- **Popularity:**
  - The RuPay-on-UPI question is very common (~6,700 posts). Kiwi is one of the most-cited UPI-first cards (qualitative).
  - Kiwi's own blog shows heavy SEO presence, so treat that as **weak** evidence.
- **Product pages:**
  - Fintech: https://gokiwi.in/ (200)
  - Issuer RuPay page: https://www.yes.bank.in/personal-banking/yes-individual/cards/credit-cards/rupay-credit-card (200; JS-rendered; **Kiwi linkage unverified**)
- **Docs:** YES Bank MITC (v18, 05-10-2026): https://www.yes.bank.in/sites/web/content/published/api/v1.1/assets/CONTAA57595B2EF245259C4C623B1F7D33B3/native/ybl_mitc_pdf.pdf (200)
- **Notes:** The Kiwi program reportedly also runs on AU SFB (unverified). Cashback is credited by the fintech, so record who pays it.

### 19. AU Bank LIT Credit Card — AU Small Finance Bank
- **Popularity:**
  - Customisable lifetime-free card. Cap-cut thread: https://technofino.in/community/threads/au-lit-reward-points-limit.31188/
  - AU 2026 bank-wide changes: https://cardadvisor.in/changes/2026-W15 (weak)
- **Product page:** https://www.au.bank.in/personal-banking/credit-cards/lit-credit-card (**403 to bots**; the URL comes from search on au.bank.in). Use a real browser.
- **Docs:**
  - MITC with schedule of charges: https://www.au.bank.in/content/dam/aubank/in/en/pdf/credit-card/MITC(with-Schedule-of-Charges).pdf (200)
  - KFS/SOC: https://www.au.bank.in/content/dam/aubank/in/en/pdf/credit-card/Schedule-of-Charges-CC.pdf (200)
  - Product guide: https://www.au.bank.in/campaign/lit-product-guide.pdf **(unverified)**
- **Notes:** Network and RuPay status are unverified. Alternate: **ixigo AU** (https://www.au.bank.in/personal-banking/credit-cards/ixigo-au-credit-card; lifetime free; zero forex per AU).

### 20. Kotak League Platinum Credit Card — Kotak Mahindra Bank
- **Popularity:**
  - Myntra Kotak holders were auto-migrated to it (Jul 2025): https://cardinsider.com/blog/kotak-myntra-credit-card-discontinued-from-july-2025/
  - Kotak closure-compensation post (6,253↑, the year's top post) shows Kotak's salience: https://www.reddit.com/r/CreditCardsIndia/comments/1ssihqu
  - TechnoFino "LTF League Platinum charged fee" thread.
- **Product page:** https://www.kotak.bank.in/en/personal-banking/cards/credit-cards/league-platinum-card.html (200)
- **Docs:**
  - MITC and KFS index: https://www.kotak.bank.in/en/personal-banking/cards/credit-cards/mitc-and-ca.html (200)
  - Generic KFS: https://www.kotak.bank.in/content/dam/Kotak/Customer-Service/others/kfs.pdf (200)
  - MCC list: …/content/dam/Kotak/gsfcfiles/credit-cards/list-of-mccs-with-respect-to-revised-fees-and-rewards_june_01_2025.pdf
- **Notes:** "₹499/Nil" means paid and lifetime-free variants exist. Store an LTF flag per user, not per card. Alternate: **Kotak Cashback+** (https://www.kotak.bank.in/en/personal-banking/cards/credit-cards/kotak-cashback-plus-credit-card.html; ₹750 waived at ₹2L; RuPay variant earns 0.5% on UPI; KFS `/content/dam/Kotak/files/key-fact-statement/Key-fact-statement-kfs-cashback-credit-card.pdf`).

---

## 4. Caveats
- **The rank is judgement, not measurement.** Reddit and TechnoFino counts could not be pulled (see §1). Only issuer-level share and three issuer-announced card milestones are hard numbers, and those milestones are 2021–2025.
- **Networks marked "rep."** come from general knowledge or aggregators. Confirm them from the application page or MITC before setting `network` in profiles.
- **Several 2026 changes are sourced only from aggregators**: Atlas sourcing stop, Swiggy ₹249 minimum, HDFC Tata Neu lounge gate, IDFC changes, AU changes. Each needs the issuer notice before entering a profile.
- **JS-rendered or bot-blocked pages** (sbicard.com product pages, yes.bank.in, au.bank.in) need a headless browser in the A6 scraper. The PDFs on those domains download fine.
- **Partner-hosted documents** (scapia.cards, res.cloudinary.com/scapiacards, gokiwi.in, swiggy.com) are partner claims, not issuer documents. They are allowed as secondary sources only (see YAML `partner_sources`).

## 5. Re-running the popularity count
Arctic Shift title search worked only in one-month windows, e.g. `https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=CreditCardsIndia&title=<term>&after=2026-09-01&before=2026-10-01&limit=100&fields=created_utc` (paginate with `before=<last created_utc>`). It must be called with curl, because Python urllib gets 403 on User-Agent. On 6 Oct 2026 it returned mostly "Timeout" errors. Retry off-peak with ≥3 s spacing, and count variants (`infinia`, `regalia`, `tata neu`, `amazon pay`, `flipkart axis`, `sbi cashback`, `airtel axis`, `swiggy`, `magnus`, `atlas`, `millennia`, `scapia`, `kiwi`, `live+`, `coral`, `octane`, `league`, `au lit`, `simplyclick`).
