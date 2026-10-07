# Issuer-level card-holding policies (India)

Research date: 2026-10-07. Scope: rules that decide whether a user can *get* or *hold* a card with an issuer: per-issuer card caps, mutual-exclusion / compatibility rules, relationship-gated cards, cooling-off and re-apply rules, and product-change paths.

How to read this file

- **Confidence** is one of `policy` (issuer document or issuer page, allow-listed in `official-domains.yaml`), `community-consistent` (several independent forum reports agreeing, no issuer text), `anecdotal` (one or two reports, or a single aggregator claim). Only `policy` rows may be used as hard constraints in the advisor; everything else is "warn, don't block" (DR-4 / DR-12 in `official-domains.yaml`).
- **Sources**: issuer PDFs were downloaded and text-extracted with `pdftotext`; TechnoFino threads were read from Wayback Machine snapshots (direct fetch is Cloudflare-403); snapshot dates are given per row. The Arctic Shift Reddit API returned `{"error":"Timeout. Maybe slow down a bit"}` (HTTP 422) on every call during this run, so Reddit evidence is limited to search-result snippets and is marked anecdotal.
- Nothing below is invented. Where an issuer page was fetched and was silent on a point, the row says so.

Issuer pages fetched directly in this run (status): HDFC Infinia product page (200, "By Invite Only" visible), HDFC Swiggy and Tata Neu Infinity product pages (200, eligibility block not in server HTML), Federal Bank Scapia page (200), Standard Chartered Priority Visa Infinite page (200), Kotak White Reserve page (200, no eligibility section), RBL "Policy for credit card issuance and conduct" PDF (200), SBI Card "Policy for the issuance and conduct of credit cards" PDF (200), SBI Card "Card upgrade process" T&C PDF (200), SBI Card "Preferred Partners" T&C PDF (200; only cashback-offer terms, nothing on card holding), Yes Bank Marquee page (timed out twice), IndusInd "Credit Cards Issuance and Conduct Policy FY24-25" PDF (DNS failure on indie.indusind.com, 301 chain to a 500 page on indusind.bank.in), Axis Burgundy Private T&C v1 PDF (301 to sitemap: document gone), Axis Burgundy Private product page (404 at the guessed slug), IDFC FIRST FAQ page (404 at the guessed slug), Amex India FAQ hub (200, nothing on multiple cards).

---

## (a) Per-issuer summary

| Issuer | Max cards per person (policy / practice) | Relationship needed | Secured (FD) card option | Re-apply cooling-off | Notes and sources |
|---|---|---|---|---|---|
| HDFC Bank | **No published cap.** Practice (2024-25): one card per customer is the default; co-brands (Tata Neu, Swiggy, Marriott, IRCTC, IndianOil, Shoppers Stop) are issued to existing core-card holders on a **shared** limit; a second *core* card is exception-based ("floater" card, RM/branch). Online portal blocks a fresh application if any HDFC card application exists in the last 6 months. | Infinia and Diners Club Black: "By Invite Only" (issuer page). Not formally account-gated, but community reports upgrade offers track salary/wealth relationship. | Yes: FD-backed credit card via branch/NetBanking (issuer markets it; not fetched this run). | Rejection: 6 months before the online portal accepts a new application (community-consistent; several TechnoFino threads cite HDFC customer care). Closure: same 6-month cooldown reported. | TechnoFino "HDFC doesn't let me apply for a second credit card" (thread 32102, Wayback 2024-09-19): "If you have an existing CoBranded or Core Card with HDFC you will not be issued a new card. Only way now to get a 2nd card from HDFC is through Floater card."; "Wait for 6 months to cool down or apply offline from your branch."; one member reports getting Swiggy after IRCTC. TechnoFino "Can I have Infinia and DCB both" (thread 12116, search snippet): co-brand shares limit with core card; Infinia + DCB with split limits exists but is exception-based. HDFC Infinia page https://www.hdfc.bank.in/credit-cards/infinia-credit-card (fetched 2026-10-07: "By Invite Only"). |
| ICICI Bank | No published cap. Community compilation (TechnoFino thread 258, July 2023 table): **1 core + 2 co-brand**; HNI / high-NRV customers more. One member reports 4 ICICI cards on a merged limit (thread 258 p.4, Wayback 2024-05-09). | Emeralde Private: invite only (no public form). Emeralde: issuer page says existing ICICI Global Private Client customers are eligible to apply. | Yes: FD-backed "Instant Platinum"/secured card (not fetched this run). | Rejection: 6 months (community-consistent; TechnoFino "ICICI credit card application rejected", thread 37133). | Amazon Pay ICICI for an existing ICICI cardholder shares the existing card's limit and skips a fresh bureau pull (livefromalounge.com/amazon-icici-bank-credit-card-approval, aggregator). |
| Axis Bank | No published cap. Practice: **2 cards** standard, **3rd** on RM/branch approval; limits usually merged. Desidime "maximum credit cards given by bank to one person" and TechnoFino post 558482 both say 2 is normal, 3 is SOP with approval. | Burgundy Private card: Burgundy Private relationship. Magnus for Burgundy: Burgundy account (TechnoFino thread 40625 reports 30 L TRV, some report 10 L AMB offers). Reserve: invite / RM. | Yes: FD-backed card (issuer markets it; not fetched this run). | Conflicting: 12 months (customer-care statement), 6 months (CIBIL-reason rejection), 3 months / 90 days (document-reason rejection, or per a branch head "whether accepted or rejected"). TechnoFino threads 37129 and 1752, posts 919076, 919003, 513138. | Account holders get more lenient treatment than non-account holders (TechnoFino, same threads). Burgundy Private T&C v1 PDF on axisbank.com is now a 301 to the sitemap: document withdrawn or moved. |
| SBI Card | No published cap. Practice: **2–4 cards** on separate limits; one member reports SBI customer care saying "maximum of 4" (thread 258 p.4). **3-month gap between SBI applications** (TechnoFino "SBI credit card queries", thread 44601). | None; SBI savings/salary account helps approval (aggregator claim). | Yes: Secured Card "granted to SBI and co-brand banking partner customers, by marking lien on the fixed deposit" (SBI Card issuance policy PDF, policy). | Rejection: ~90 days (TechnoFino "How long is the wait before reapplying for an SBI CC", thread 44569; community-consistent). | Policy PDF also gives a 37-day post-issuance cooling period during which closure is free, and 1-year-inactivity closure. Upgrade/downgrade rules are policy: see (d). |
| American Express | **2 credit cards + 1 charge card** (cardinsider.com, 2024-09-17; no Amex text cites this; community-consistent). Six-month wait after a new card is the commonly quoted rule, but TechnoFino post 811583 reports Platinum Travel and MRCC approved back-to-back. | None. | No. | 6 months after a new card before another (anecdotal/aggregator; contradicted by at least one report). | From 2026-10-11 Amex India stops pooling MR points across cards (livefromalounge.com, Oct 2026), which removes the main reason to hold several Amex cards. |
| IndusInd Bank | No published cap. Core cards can be held on split limits; **Tiger is not issued as a split-limit card, so it cannot be held with another IndusInd card** (TechnoFino posts 1239926 / 1239914 / 1251017, 2026, community-consistent). | None stated. | Yes (secured card for non-serviceable areas with a nearby branch, per cardinsider summary of the issuance policy, 2024-07-04). | After closure: ~30 days before a new IndusInd application (anecdotal; one member approved immediately after Legend closure). | Issuance & Conduct Policy FY24-25 PDF could not be fetched (DNS / 500). |
| IDFC FIRST Bank | No published cap. Issuer FAQ snippet (idfcfirstbank.com, via search): "If you already have an IDFC FIRST Bank Credit Card, you can apply for their co-branded credit cards. The credit limit will be shared." Existing holders can also add FIRST Digital RuPay (UPI) and FIRST WOW!. | FIRST Private: invite only. | FIRST WOW!: FD-backed, no income proof; FD minimum ₹2,000 per idfcfirst.bank.in/credit-card/credit-card-against-fixed-deposits (search snippet); aggregators quote ₹20,000. | Not found. | Issuer FAQ page not fetched directly (404 at guessed slug): treat the shared-limit statement as issuer-page-via-snippet until the live URL is captured. |
| Kotak Mahindra Bank | Community compilation: **1 core + 1 co-brand** (TechnoFino thread 258, July 2023 table); "total 3 possible" per later posts. Kotak itself markets "multiple credit cards" (search snippet; no cap published). | White Reserve: Privy League / high relationship (NRI Privy Black brochure: Relationship Value ₹1 Cr for NRI; resident threshold not published). White Reserve page has no eligibility section. | Kotak811 #DreamDifferent (FD ≥ ₹10,000) and Kotak811 super.money (FD from ₹1,000, limit up to 90%). | Not found. | |
| YES BANK | No published cap. Marquee eligibility (aggregator copy of issuer text): **"applicant should not be an existing YES BANK credit card holder"**: issuer page timed out, so confidence is aggregator-only. | Marquee: ITR ₹36 L or income ₹3 L p.a. (aggregator); YES First / Private relationship favours invite. | Yes (FD-backed). | Not found. | Kiwi RuPay cards are issued by YES BANK (and reportedly AU): see Kiwi row. |
| AU Small Finance Bank | Community: **AU is not issuing a second card to existing AU cardholders** (TechnoFino posts 1055784, 493453, 843985, 811159, 1174184; community-consistent). Some reports that this is loosening for RuPay variants. | Zenith+: income ₹2.5 L per month (aggregator). | NOMO (FD ≥ ₹10,000), issuer page https://www.au.bank.in/personal-banking/credit-cards/nomo-credit-card. | Not found. | |
| RBL Bank | Community: **2 co-brand + 1 regular**, shared limit (TechnoFino thread 258 p.4, Wayback 2024-05-09). | None. | Yes: "Secured Card (FD backed credit card) to the existing customers who are holding fixed deposit account with Bank or agrees to open a new FD"; "may offer its Proprietary Credit Card or Co-brand card ... under the Secured Card program" (RBL policy PDF, policy). | Not published. Policy PDF: card not activated within 30 days of issuance is closed; unused 37 days from origination or 12 months inactive triggers closure. | Upgrade rule is policy: "When cardmember has agreed to take better variant card, existing card gets blocked." |
| HSBC India | No published cap; multiple cards allowed subject to assessment (cardadvisor, aggregator). | Premier card: must be an HSBC Premier customer (TRB ₹40 L, or salary credit ₹3 L per month, or mortgage ₹1.15 Cr + TRB within 12 months) per hsbc.co.in Premier pages (search snippet; issuer). | Not found. | Not found. | |
| Standard Chartered | Not found. | Priority Visa Infinite: "Reserved for Priority Banking customers" (sc.bank.in page, fetched: policy); Priority Pass lounge needs FUM ₹30 L. Ultimate: age 21–65, sourcing cities; no account requirement stated (sc.bank.in). | Not found. | Not found. | |
| Federal Bank / Scapia | Not found. Scapia page (fetched) lists only age/citizenship and "other criteria as per bank's onboarding policy". | None. | Not found for Scapia; Federal offers FD cards separately (not verified). | Not found. | Claim that existing Federal / BOBCARD cardholders are ineligible for Scapia appears only on aggregators (wise.com / stablemoney): **unverified**. |
| BOBCARD | Community: 2 BOB cards on separate limits (TechnoFino thread 258 p.4). | Eterna: income ₹12 L p.a. (cardinsider). | Yes (FD-backed, issuer markets it; not fetched). | Not found. | bobcard.co.in canonical domain still unverified in `official-domains.yaml`. |
| OneCard (FPL) | Community: 2 OneCards via different partner banks (TechnoFino thread 258 p.4). | None. | FD-backed OneCard exists (partner-bank FD). | Not found. | Desidime thread titled "OneCard directed to halt all new credit card issuances" exists: date and status unverified. |
| Kiwi (YES BANK / AU RuPay) | Not found. | None. | No. | Not found. | Existing YES BANK cardholders are excluded from certain Kiwi reward offers (CashKaro); Kiwi runs "upgrade to YES BANK card" offers for existing Kiwi users (gokiwi.in/offers). Whether an existing YES card blocks a Kiwi YES card is **not confirmed**. |

---

## (b) Compatibility / mutual-exclusion rules

Rule types: `blocks` (B cannot be obtained while holding A), `shares-limit` (allowed, but limit is shared/split), `requires-closure` (must close A to get B), `allowed-after-N-months`, `replaces` (B is issued by converting A).

| # | Card(s) A | Card(s) B | Rule type | Detail | Source URL | Date | Confidence |
|---|---|---|---|---|---|---|---|
| 1 | Any HDFC credit card (core or co-brand) | Any second HDFC card via online application | blocks | Online portal rejects: "It seems that you have recently applied for a credit card"; members state HDFC issues a second card only as a "floater" via RM/branch. | https://technofino.in/community/threads/hdfc-doesnt-let-me-apply-for-a-second-credit-card.32102/ | Wayback 2024-09-19 | community-consistent |
| 2 | HDFC core card (Millennia, Regalia, DCB, Infinia) | HDFC co-brand (Tata Neu, Swiggy, Marriott, IRCTC, IndianOil, Shoppers Stop) | shares-limit | Co-brand is issued against the core card's limit ("Tata Neu shares the overall limit with the core card"). | https://technofino.in/community/threads/can-i-have-infinia-and-dcb-both.12116/ | 2023–24 posts (snippet) | community-consistent |
| 3 | HDFC co-brand held first | HDFC core card later | blocks (soft) | Members report HDFC refuses a core card to someone whose first HDFC card is a co-brand; workaround is upgrade of the co-brand. | thread 32102 above | 2024-09 | anecdotal |
| 4 | HDFC IRCTC co-brand | HDFC Swiggy co-brand | allowed | One member: "I just got swiggy cc after having hdfc irctc cc". Contradicts rule 1 for co-brand-to-co-brand. | thread 32102 above | 2024-09 | anecdotal |
| 5 | HDFC Infinia | HDFC Diners Club Black | allowed (exception) | Both held with split limits reported (e.g. 8 L / 5 L); depends on approver. | thread 12116 above | 2023–24 | anecdotal |
| 6 | Any IndusInd credit card | IndusInd Tiger (Bajaj co-brand) | blocks / requires-closure | "Tiger Card is not issued as a split-limit card ... cannot hold it alongside another IndusInd credit card"; no conversion offered; close existing card and apply fresh. | https://technofino.in/community/posts/1239926/ ; https://technofino.in/community/posts/1251017/ | 2026 (snippet) | community-consistent |
| 7 | IndusInd card closed | New IndusInd card | allowed-after-N-months (≈1) | Members report ~30 days after closure; one approved immediately after Legend closure. | https://technofino.in/community/posts/1251001/ | 2026 (snippet) | anecdotal |
| 8 | Any ICICI credit card | Amazon Pay ICICI | shares-limit | Existing ICICI cardholder gets Amazon Pay on the existing credit line, without a new bureau pull. | https://livefromalounge.com/amazon-icici-bank-credit-card-approval/ | undated (aggregator) | anecdotal |
| 9 | ICICI core card | 3rd ICICI co-brand | blocks (soft) | Compilation: ICICI "1 core + 2 co-brand"; HNI more. Contradicted by a member with 4 ICICI cards (merged limit). | https://technofino.in/community/threads/how-many-credit-cards-are-allowed-per-customer.258/ | table July 2023; p.4 Wayback 2024-05-09 | community-consistent (soft) |
| 10 | Two Axis cards | 3rd Axis card | blocks (soft) | 2 is standard; 3rd needs RM/branch approval; limits merged. | https://technofino.in/community/goto/post?id=558482 ; https://www.desidime.com/discussions/maximum-credit-cards-given-by-bank-to-one-person | 2023–24 | community-consistent |
| 11 | Axis Magnus (non-Burgundy) | Axis Magnus for Burgundy | replaces | Issued as an upgrade of the existing Magnus once a Burgundy relationship exists; old Magnus is converted, not added. | https://technofino.in/community/threads/upgrading-magnus-5-2-to-5-4.40625/ | 2024–25 | community-consistent |
| 12 | Any SBI Card | 2nd SBI Card | allowed-after-N-months (3) | "cooling period of at least 3 months before you can apply for a second SBI card"; separate limit in most cases; v-KYC and bureau pull repeat. | https://technofino.in/community/threads/sbi-credit-card-queries.44601/ | 2025 (snippet) | community-consistent |
| 13 | SBI Cashback | SBI SimplyCLICK / BPCL / PhonePe Black | allowed | Members hold Cashback + another SBI card for sale offers; no exclusion found in SBI documents. | thread 44601 above | 2025 | community-consistent |
| 14 | SBI core card | SBI co-brand (upgrade/flip) | replaces | Policy: flip core→co-brand requires using all reward points first; co-brand→core does not carry points; old plastic active 90 days. | https://www.sbicard.com/sbi-card-en/assets/docs/pdf/tnc/Cardupgradeprocess.pdf | fetched 2026-10-07 | policy |
| 15 | Amex credit card (MRCC, Plat Travel, SmartEarn) | 3rd Amex credit card | blocks | "two credit cards and one charge card at the same time". | https://cardinsider.com/blog/can-i-have-multiple-american-express-credit-cards-india/ | 2024-09-17 | community-consistent (aggregator; no Amex text) |
| 16 | New Amex card | Another Amex card | allowed-after-N-months (6) | "won't be able to apply for another one for the next six months". Contradicted by TechnoFino post 811583 (Plat Travel then MRCC back to back). | cardinsider above; https://technofino.in/community/goto/post?id=811583 | 2024 | anecdotal |
| 17 | Any YES BANK credit card | YES Marquee | blocks | Eligibility line: "The applicant should not be an existing YES BANK credit card holder." | https://bankbazaar.com/credit-card/yes-bank-marquee-credit-card.html (aggregator copy; issuer page timed out) | 2025–26 | anecdotal until issuer page is captured |
| 18 | Any AU SFB credit card | 2nd AU card | blocks | "AU Small Finance Bank is not issuing a second credit card." | https://technofino.in/community/goto/post?id=1055784 ; https://technofino.in/community/posts/811159/ | 2024–25 | community-consistent |
| 19 | RBL 2 co-brand + 1 regular | 4th RBL card | blocks (soft) | "You can have 2 Co-Branded + 1 Regular RBL Card." Limit shared. | thread 258 p.4 above | Wayback 2024-05-09 | community-consistent |
| 20 | RBL lower variant | RBL better variant | replaces | Policy: "When cardmember has agreed to take better variant card, existing card gets blocked." | https://webassets.rbl.bank.in/document/bank-policies/policy-for-credit-card-issuance-and-conduct.pdf | fetched 2026-10-07 | policy |
| 21 | IDFC FIRST core card | IDFC FIRST co-brand (e.g. Mayura/Ashva partners, LIC, Vistara) | shares-limit | Issuer FAQ: co-brand allowed; "credit limit will be shared with your existing IDFC FIRST Bank Credit Card". | idfcfirstbank.com FAQ (search snippet; live URL not captured) | 2025 | policy (snippet, needs URL) |
| 22 | Kotak core card | 2nd Kotak co-brand | blocks (soft) | Compilation: Kotak 1 core + 1 co-brand; later posts say 3 possible. | thread 258 above | 2023–24 | anecdotal |
| 23 | Federal Bank / BOBCARD credit card | Scapia Federal | blocks | Aggregator claim only; issuer Scapia page is silent. | https://wise.com/in/blog/federal-bank-scapia-credit-card-review ; https://www.federal.bank.in/scapia (fetched, silent) | 2025 | anecdotal (unverified) |
| 24 | YES BANK credit card | Kiwi (YES) reward offers | blocks (offers only) | Existing YES cardholders excluded from some Kiwi CashKaro reward offers; not a card-holding rule. | https://cashkaro.com/stores/kiwi-credit-card-offers-cci | 2025 | anecdotal |

---

## (c) Relationship-gated cards

| Issuer | Card | Gate | Threshold / wording | Source | Confidence |
|---|---|---|---|---|---|
| HDFC | Infinia (Metal) | Invite only | Issuer page: "By Invite Only". Income thresholds circulating (₹5 L pm salaried non-govt, ₹3.5 L govt, ₹60 L p.a. self-employed) are from cardinsider, not the issuer page. | https://www.hdfc.bank.in/credit-cards/infinia-credit-card ; https://cardinsider.com/blog/eligibility-criteria-hdfc-infinia-dcb-biz-black-regalia-gold-credit-card/ | policy (invite); aggregator (income) |
| HDFC | Diners Club Black (Metal) | Invite / upgrade | Same cardinsider article; co-brand → DCB "alumni route" upgrade reported on TechnoFino thread 12116. | as above | aggregator / community |
| ICICI | Emeralde Private (Metal) | Invite only | "issued strictly by invitation, there is no public application form"; relationship (balances, spend, segment) drives invites. | https://cardadvisor.in/cards/icici-emeralde-private | aggregator |
| ICICI | Emeralde | Relationship | "all existing ICICI Bank Global Private Client customers are eligible to apply". | https://www.icici.bank.in/personal-banking/cards/credit-card/emeralde-credit-card-new (snippet) | policy (snippet) |
| Axis | Burgundy Private | Burgundy Private banking | Card is tied to Burgundy Private relationship; T&C v1 PDF no longer served (301 to sitemap). | https://cardadvisor.in/articles/axis-burgundy-private-credit-card-review-2026 | aggregator |
| Axis | Magnus for Burgundy | Burgundy account | Members cite 30 L TRV; some got upgrade links at ~10 L AMB. | https://technofino.in/community/threads/upgrading-magnus-5-2-to-5-4.40625/ | community-consistent |
| Kotak | White Reserve | Privy League | NRI Privy Black brochure: RV ₹1 Cr; resident threshold not published; product page has no eligibility section. | https://www.kotak.bank.in/content/dam/Kotak/Customer-Service/Download-Forms/nri-privy/nr-privy-black-brochure.pdf ; https://www.kotak.bank.in/en/personal-banking/cards/credit-cards/white-reserve-credit-card.html | policy (NRI); gap (resident) |
| HSBC | Premier (Mastercard) | HSBC Premier | TRB ₹40 L, or salary credit ₹3 L pm, or mortgage ₹1.15 Cr with TRB within 12 months. | https://www.hsbc.co.in/premier/features/ ; https://www.hsbc.co.in/credit-cards/products/premier-mastercard/ | policy (snippet) |
| Standard Chartered | Priority Visa Infinite | Priority Banking | "Reserved for Priority Banking customers"; Priority Pass needs FUM ₹30 L. | https://www.sc.bank.in/credit-cards/priority-banking-visa-infinite/ (fetched) | policy |
| Standard Chartered | Ultimate | None stated | Age 21–65, income, sourcing cities. | https://www.sc.bank.in/employee-banking/ultimate-card/ | policy (snippet) |
| YES BANK | Marquee | No existing YES card; income/ITR | "should not be an existing YES BANK credit card holder"; ITR ₹36 L or income ₹3 L. | bankbazaar copy (issuer page timed out) | aggregator |
| IDFC FIRST | FIRST Private | Invite only | "Invite Only"; concentrated among top wealth-relationship clients. | https://cardinsider.com/idfc-first-bank/idfc-first-private-credit-card/ | aggregator |
| BOBCARD | Eterna | Income | ₹12 L p.a. | https://cardinsider.com/bank-of-baroda/bank-of-baroda-eterna-credit-card/ | aggregator |
| AU SFB | Zenith+ | Income | ₹2.5 L net per month. | https://bankbazaar.com/credit-card/au-bank-zenith-plus-metal-credit-card.html | aggregator |

Secured / FD-backed options (per issuer): HDFC (FD card), ICICI (FD card), Axis (FD card), SBI Card (lien on FD; "SBI and co-brand banking partner customers", policy PDF), IndusInd (secured where unserviceable), IDFC FIRST WOW! (FD ≥ ₹2,000 per issuer page snippet; aggregators say ₹20,000), Kotak811 #DreamDifferent (FD ≥ ₹10,000) and super.money (FD ≥ ₹1,000), AU NOMO (FD ₹10,000, issuer page), RBL (proprietary or co-brand on FD lien, policy PDF), BOBCARD (FD card), OneCard (FD variant), Yes Bank (FD card). Amex, HSBC, SC, Scapia, Kiwi: none found.

---

## (d) Product-change (upgrade / downgrade) paths

| Issuer | Path | Mechanism | Rules | Source | Confidence |
|---|---|---|---|---|---|
| SBI Card | Any → higher core (e.g. SimplyCLICK → Prime → Elite → AURUM); core ↔ co-brand flips | Offer-based ("The upgrade would be offered to eligible customers basis internal evaluation") | Core→core: points transfer. Core→co-brand: use points first. Co-brand→core: points do not move. Old plastic active 90 days. **Downgrade only within 90 days of an upgrade; after a downgrade no upgrade for 6 months.** Fee date unchanged. | https://www.sbicard.com/sbi-card-en/assets/docs/pdf/tnc/Cardupgradeprocess.pdf | policy |
| RBL | Lower → better variant | Bank offer | Existing card is blocked on acceptance of the better variant. | RBL policy PDF (above) | policy |
| HDFC | Millennia / Regalia → Regalia Gold; co-brand (Tata Neu) → Millennia / Diners Privilege / IndiGo XL; DCB → Infinia | NetBanking "upgrade" option, or Grievance.Redressalcc@hdfcbank.com request | Upgrade replaces the card; NetBanking shows "you already have the best card" when no offer exists. Infinia is invite-only. | https://www.hdfcbank.com/personal/resources/learning-centre/pay/upgrade-to-regalia-gold-credit-card ; TechnoFino thread 32102 | policy (Regalia Gold page); community (routes) |
| Axis | Magnus → Magnus for Burgundy; (historic) Magnus/Reserve devaluations | RM / Burgundy upgrade link | Burgundy relationship required; conversion, not a second card. | TechnoFino thread 40625 | community-consistent |
| ICICI | Platinum → Coral → Rubyx → Sapphiro → Emeralde | Customer-care / offer | Ladder exists; Emeralde Private is invite only; no issuer upgrade T&C found. | https://cardadvisor.in/articles/icici-credit-card-ladder-guide | aggregator |
| IndusInd | Core → Tiger | Not allowed | "IndusInd does not officially allow conversion or upgrade to the Tiger Card" (co-brand). | TechnoFino posts 1239926 / 1239914 | community-consistent |
| Kiwi / YES | Kiwi card → YES BANK credit card | In-app upgrade offer | For selected users "who have an existing credit card issued via the Kiwi App and have received communication for upgrade". | https://gokiwi.in/offers/other-offers/march-offers-2025/card-upgrade-offer2/ | partner page (policy for partner-owned field) |
| Amex | Within family (e.g. MRCC → Gold Charge, Plat Travel → Platinum Charge) | Customer care | No Amex India document found this run; from 2026-10-11 MR points are no longer pooled across cards. | https://livefromalounge.com/american-express-membership-rewards-india-changes-coming-october-11-2026 | aggregator |

Cooling-off / BRE hard stops found (all community unless noted):

- HDFC: 6 months after rejection; the same 6-month "recently applied" block applies after any application; offline/branch and partner-app (Swiggy app, Tata Neu app, Paytm) routes reportedly bypass the online check. (TechnoFino posts 142180, 897451, 70978, thread 32102; paisabazaar cooling-off article.)
- ICICI: 6 months after rejection (TechnoFino thread 37133, post 1122050).
- Axis: 90 days / 6 months / 12 months depending on who is asked and on rejection reason (TechnoFino threads 1752, 37129; posts 919076, 919003, 513138).
- SBI Card: ~90 days after rejection (thread 44569); 3 months between successful applications (thread 44601). Policy: 37-day post-issuance free-closure window; downgrade/upgrade timing in (d).
- Amex: 6 months after a new card (aggregator; contradicted once).
- IndusInd: ~30 days after closure (anecdotal).
- Generic BRE signals cited across threads (not issuer-published): number of enquiries in the last 6 months, cards opened in the last 6–12 months, and delayed payments in the last 12 months (IndusInd Tiger eligibility copy on cardadvisor says "no delayed payments in the last 12 months"). No issuer publishes an enquiry-count hard stop.

---

## (e) Unverified / conflicting

1. **HDFC second card.** TechnoFino members state "HDFC has stopped issuing 2nd card" (2024-09), yet the same thread has a member who got Swiggy after IRCTC, and thread 12116 has Infinia + DCB holders. Treat as "one core card + co-brands on shared limit; anything else is exception". No HDFC document says any of this.
2. **Amex 2 credit + 1 charge cap** and **6-month gap**: only cardinsider (2024-09-17) and no Amex text; at least one back-to-back approval reported.
3. **YES Marquee "not an existing YES cardholder"**: aggregator copy only; the issuer page timed out twice. Must be re-fetched before being used as a `policy` rule.
4. **Scapia blocks existing Federal / BOBCARD cardholders**: wise.com / stablemoney only; federal.bank.in/scapia (fetched) is silent.
5. **Axis rejection cooldown**: 90 days vs 6 months vs 12 months, all attributed to Axis staff.
6. **Axis max cards**: 2 vs 3; TechnoFino thread 258 member reports 3 Axis cards on merged limit.
7. **ICICI max cards**: "1 core + 2 co-brand" (2023 table) vs "Any" (later posts) vs 4 cards merged (member report).
8. **IDFC WOW! minimum FD**: ₹2,000 (issuer page snippet) vs ₹20,000 (aggregators).
9. **Kotak cap**: 1 core + 1 co-brand vs 3 total; a member in thread 258 explicitly asks "Are you sure about Kotak card limit?" with no reply.
10. **IndusInd policy PDF** (Credit Cards Issuance and Conduct Policy FY24-25) could not be fetched; the cardinsider summary (2024-07-04) says it is silent on multiple cards and cooling-off.
11. **OneCard halt of new issuances** (desidime thread title): date and current status unverified.
12. **Kiwi vs existing YES card**: only offer-level exclusion found; card-level rule unknown.
13. **Axis Burgundy Private T&C v1 PDF** withdrawn (301 to sitemap): relationship-lapse downgrade rule not captured.
14. **Reddit**: Arctic Shift API failed (HTTP 422 timeout on every call); no Reddit thread links could be captured this run. Re-run the four queries (HDFC co-brand second card; IndusInd Tiger existing card; Axis max cards; Amex second card six months) when the API is responsive.

---

## (f) Proposed JSON shapes

### `compatibility_rule`

```json
{
  "id": "indusind.tiger.blocks-other-indusind",
  "issuer_id": "indusind_bank",
  "cards_a": ["indusind:*"],
  "cards_b": ["indusind:tiger"],
  "rule_type": "requires-closure",
  "direction": "a_to_b",
  "detail": "Tiger is not issued as a split-limit card; holders of any other IndusInd credit card must close it before applying. No conversion offered.",
  "cooling_off_days": 30,
  "limit_mode": null,
  "confidence": "community-consistent",
  "sources": [
    {"url": "https://technofino.in/community/posts/1239926/", "kind": "forum", "observed_on": "2026-09-15", "snapshot": null},
    {"url": "https://technofino.in/community/posts/1251017/", "kind": "forum", "observed_on": "2026-09-30", "snapshot": null}
  ],
  "first_seen": "2026-10-07",
  "last_verified": "2026-10-07",
  "status": "active",
  "advisor_action": "warn"
}
```

Field notes: `rule_type` ∈ {`blocks`, `shares-limit`, `requires-closure`, `allowed-after-N-months`, `replaces`, `allowed`}; `direction` ∈ {`a_to_b`, `symmetric`}; `cards_*` accept `issuer:card_slug` or `issuer:*` or `issuer:cobrand:*`; `limit_mode` ∈ {`shared`, `split`, `separate`, null}; `confidence` ∈ {`policy`, `community-consistent`, `anecdotal`}; `advisor_action` is derived: `block` only when `confidence == "policy"`, else `warn`.

### `issuer_policy`

```json
{
  "issuer_id": "sbi_card",
  "as_of": "2026-10-07",
  "max_cards": {"policy": null, "practice": 4, "counts_cobrand_separately": true, "limit_mode": "separate",
                "sources": [{"url": "https://technofino.in/community/threads/how-many-credit-cards-are-allowed-per-customer.258/page-4", "kind": "forum", "snapshot": "2024-05-09"}],
                "confidence": "community-consistent"},
  "relationship": {"required_for": [], "favoured": ["sbi_savings_or_salary_account"], "confidence": "anecdotal"},
  "secured_card": {"available": true, "product": "SBI Card (FD lien)", "min_fd_inr": null,
                   "source": "https://www.sbicard.com/sbi-card-en/assets/docs/pdf/who-we-are/notices/policy-for-the-Issuance-and-conduct-of-credit-cards.pdf",
                   "confidence": "policy"},
  "cooling_off": {
    "after_rejection_days": {"value": 90, "confidence": "community-consistent", "source": "https://technofino.in/community/threads/how-long-is-the-wait-before-reapplying-for-an-sbi-cc.44569/"},
    "between_applications_days": {"value": 90, "confidence": "community-consistent", "source": "https://technofino.in/community/threads/sbi-credit-card-queries.44601/"},
    "after_closure_days": {"value": null, "confidence": null, "source": null},
    "post_issuance_free_closure_days": {"value": 37, "confidence": "policy", "source": "same policy PDF"}
  },
  "product_change": {
    "upgrade_allowed": true,
    "downgrade_allowed": true,
    "downgrade_window_days_after_upgrade": 90,
    "no_upgrade_days_after_downgrade": 180,
    "old_plastic_active_days": 90,
    "points_on_core_to_cobrand": "must_redeem_first",
    "points_on_cobrand_to_core": "forfeited",
    "source": "https://www.sbicard.com/sbi-card-en/assets/docs/pdf/tnc/Cardupgradeprocess.pdf",
    "confidence": "policy"
  },
  "bre_hard_stops": [],
  "notes": "Issuer publishes no card-count cap; customer care has quoted 'maximum of 4'."
}
```

---

Sources list (all consulted 2026-10-07)

- https://www.sbicard.com/sbi-card-en/assets/docs/pdf/tnc/Cardupgradeprocess.pdf (policy)
- https://www.sbicard.com/sbi-card-en/assets/docs/pdf/who-we-are/notices/policy-for-the-Issuance-and-conduct-of-credit-cards.pdf (policy)
- https://webassets.rbl.bank.in/document/bank-policies/policy-for-credit-card-issuance-and-conduct.pdf (policy)
- https://www.hdfc.bank.in/credit-cards/infinia-credit-card (policy)
- https://www.sc.bank.in/credit-cards/priority-banking-visa-infinite/ (policy)
- https://www.federal.bank.in/scapia (policy, silent on exclusions)
- https://www.au.bank.in/personal-banking/credit-cards/nomo-credit-card (policy)
- https://www.hdfcbank.com/personal/resources/learning-centre/pay/upgrade-to-regalia-gold-credit-card (issuer)
- https://technofino.in/community/threads/how-many-credit-cards-are-allowed-per-customer.258/ (Wayback 2025-01-18, page-4 Wayback 2024-05-09)
- https://technofino.in/community/threads/hdfc-doesnt-let-me-apply-for-a-second-credit-card.32102/ (Wayback 2024-09-19)
- https://technofino.in/community/threads/can-i-have-infinia-and-dcb-both.12116/ (snippet)
- https://technofino.in/community/threads/sbi-credit-card-queries.44601/ ; https://technofino.in/community/threads/how-long-is-the-wait-before-reapplying-for-an-sbi-cc.44569/ (snippets)
- https://technofino.in/community/threads/upgrading-magnus-5-2-to-5-4.40625/ ; https://technofino.in/community/threads/axis-credit-card-rejected.37129/ ; https://technofino.in/community/threads/axis-bank-rejects-credit-card-application.1752/ (snippets)
- https://technofino.in/community/threads/icici-credit-card-application-rejected.37133/ (snippet)
- https://technofino.in/community/posts/1239926/ ; /posts/1239914/ ; /posts/1251017/ ; /posts/1251001/ (IndusInd Tiger, snippets)
- https://technofino.in/community/goto/post?id=1055784 ; /posts/811159/ (AU second card, snippets)
- https://cardinsider.com/blog/can-i-have-multiple-american-express-credit-cards-india/ (2024-09-17)
- https://cardinsider.com/indusind-bank-credit-cards-issuance-conduct-policy/ (2024-07-04)
- https://livefromalounge.com/amazon-icici-bank-credit-card-approval/ ; https://livefromalounge.com/american-express-membership-rewards-india-changes-coming-october-11-2026
- https://www.desidime.com/discussions/maximum-credit-cards-given-by-bank-to-one-person
- https://bankbazaar.com/credit-card/yes-bank-marquee-credit-card.html ; https://cardadvisor.in/cards/icici-emeralde-private ; https://cardinsider.com/idfc-first-bank/idfc-first-private-credit-card/ ; https://www.hsbc.co.in/premier/features/ ; https://gokiwi.in/offers/other-offers/march-offers-2025/card-upgrade-offer2/ ; https://cashkaro.com/stores/kiwi-credit-card-offers-cci ; https://wise.com/in/blog/federal-bank-scapia-credit-card-review
