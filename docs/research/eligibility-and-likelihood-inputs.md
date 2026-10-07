# Eligibility gates and approval-likelihood inputs (research, 7 Oct 2026)

Purpose: inputs for the cc-smith recommender's eligibility gates (hard pass/fail) and its High / Medium / Low approval-likelihood band. Everything here is cited. Issuer pages were fetched on 7 Oct 2026 unless the row says "seed-cards.md" / "verified-card-facts.json" (fetched 6–7 Oct 2026 in those files). Community material is anecdote, not policy. Numbers that could not be confirmed are in §F "Unverified", not in the tables.

How to read "min income": issuers publish it as *net monthly income* (HDFC, ICICI, SBI) or *net annual income / ITR* (Axis, Amex, HSBC, IDFC, Kotak). The table keeps the issuer's own unit; the app should normalise to annual (monthly × 12) at ingestion and store `income_basis` (`net_salary` vs `itr`).

---

## A. Published eligibility per card

Legend: S = salaried, SE = self-employed, NMI = net monthly income, "—" = not stated on the official page. Age ranges are primary cardholder. "Indicative" = the issuer page says criteria are indicative and the bank may decline anyway (Axis says this on every card page).

| # | Card | Issuer | Min age (S / SE) | Min income S | Min income SE | ITR needed? | City / relationship constraint | Stated credit-score rule | Source (fetched 7 Oct 2026) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | INFINIA Metal Edition | HDFC | — | — | — | — | **By invite only** ("To get this card, you need an invitation") | — | https://www.hdfc.bank.in/credit-cards/infinia-credit-card (page text: "INFINIA Metal Edition By Invite Only"; FAQ "To get this card, you need an invitation") |
| 2 | Diners Club Black Metal Edition | HDFC | 21–60 / 21–65 | Net income (monthly) > ₹2.5 lakh | Net income > ₹30 lakh p.a. | SE: yes (ITR figure) | Indian national | — | https://www.hdfc.bank.in/credit-cards/diners-club-black-metal-edition-credit-card |
| 3 | Regalia Gold | HDFC | 21–60 / 21–65 | NMI > ₹1,50,000 (non-govt); > ₹1,00,000 (govt) | ITR > ₹18 lakh p.a. | SE: yes | — | — | verified-card-facts.json → https://www.hdfc.bank.in/credit-cards/regalia-gold-credit-card |
| 4 | Millennia | HDFC | 21–40 / 21–40 | NMI > ₹35,000 | ITR > ₹6 lakh p.a. | SE: yes | — | — | verified-card-facts.json → https://www.hdfc.bank.in/credit-cards/millennia-credit-card |
| 5 | Tata Neu Infinity HDFC | HDFC | 21–60 / 21–65 | Income (monthly) ₹1,00,000 | Annual ITR > ₹12,00,000 | SE: yes | Indian | — | https://www.hdfc.bank.in/credit-cards/tata-neu-infinity-hdfc-bank-credit-card |
| 6 | Tata Neu Plus HDFC | HDFC | 21–60 / 21–65 | Income (monthly) ₹25,000 | Annual ITR > ₹6,00,000 | SE: yes | Indian | — | https://www.hdfc.bank.in/credit-cards/tata-neu-plus-hdfc-bank-credit-card |
| 7 | Swiggy BLCK HDFC | HDFC | 21–60 / 21–65 | NMI > ₹1,00,000 | Annual ITR > ₹12 lakh | SE: yes | — | — | verified-card-facts.json → https://www.hdfc.bank.in/credit-cards/swiggy-blck-hdfc-bank-credit-card |
| 8 | Swiggy ORNGE HDFC | HDFC | 21–60 / 21–65 | NMI > ₹20,000 | Annual ITR > ₹6 lakh | SE: yes | — | — | verified-card-facts.json → https://www.hdfc.bank.in/credit-cards/swiggy-ornge-hdfc-bank-credit-card |
| 9 | MoneyBack+ | HDFC | 21–60 / 21–65 | NMI > ₹20,000 | ITR > ₹6 lakh p.a. | SE: yes | Indian | — | https://www.hdfc.bank.in/credit-cards/moneyback-plus-credit-card |
| 10 | IndianOil HDFC | HDFC | 21–60 / 21–65 | NMI > ₹12,000 (eligibility block); FAQ on same page says > ₹10,000 — **page is self-inconsistent** | ITR > ₹6 lakh p.a. | SE: yes | Indian | — | https://www.hdfc.bank.in/credit-cards/indianoil-hdfc-bank-credit-card |
| 11 | Amazon Pay ICICI | ICICI | 21+ | Monthly income ≥ ₹30,000 | Monthly income ≥ ₹30,000 | not stated | Indian citizen | — | verified-card-facts.json → https://www.icici.bank.in/personal-banking/cards/credit-card/amazon-pay-credit-card |
| 12 | Coral | ICICI | 21+ (FAQ: 21–65) | Monthly income ₹20,000 | Annual income ₹2,40,000 | not stated | Indian citizen | — | https://www.icici.bank.in/personal-banking/cards/credit-card/coral-credit-card |
| 13 | Sapphiro | ICICI | 21+ | Monthly income ₹20,000 | Annual income ₹2,40,000 | not stated | Indian citizen | Page: "Your credit score, repayment history and overall credit profile may also be considered"; "Offerings are subject to applicable bank policies" | https://www.icici.bank.in/personal-banking/cards/credit-card/sapphiro-credit-card |
| 14 | Flipkart Axis | Axis | 18–70 | — (no income stated) | — | — | Resident of India; indicative | — | verified-card-facts.json → https://www.axis.bank.in/cards/credit-card/flipkart-axisbank-credit-card |
| 15 | Atlas | Axis | 18–70 | Net annual income ₹12 lakh+ | Net annual income ₹15 lakh+ | — | — | — | verified-card-facts.json → https://www.axis.bank.in/cards/credit-card/axis-bank-atlas-credit-card |
| 16 | Magnus | Axis | 18–70 | Net salary ₹24 lakh p.a. | Net annual ITR filed for ₹24 lakh | SE: yes | Resident of India; indicative. Burgundy variant tied to Burgundy relationship (seed-cards.md) | — | https://www.axis.bank.in/cards/credit-card/axis-bank-magnus-credit-card ("Net Salary of ₹24 lakhs per annum or Net Annual Income Tax Return filed for ₹24 Lakhs") |
| 17 | Select | Axis | 18–70 | Net income min ₹6 lakh p.a. | same | — | indicative | — | https://www.axis.bank.in/cards/credit-card/axis-bank-select-credit-card |
| 18 | Airtel Axis | Axis | 18–70 | — | — | — | Resident of India; indicative | — | https://www.axis.bank.in/cards/credit-card/airtel-axis-bank-credit-card |
| 19 | NEO | Axis | 18–70 | — | — | — | Resident of India **or NRI**; indicative | — | https://www.axis.bank.in/cards/credit-card/axis-bank-neo-credit-card |
| 20 | ACE | Axis | 18–70 | — (income proof required: payslip / Form 16 / ITR) | — | proof required | Resident of India | — | search snippet of https://axisbank.com/retail/cards/credit-card/axis-bank-ace-credit-card/eligibility-documentation (old domain; now 301s to sitemap — **re-verify**) |
| 21 | Cashback SBI Card / SimplyCLICK | SBI Card | 21–70 (aggregator) | not published on sbicard.com (aggregators say ~₹18k–20k/month) | — | — | Indian resident | sbicard.com product pages are JS-rendered; no eligibility text in HTML | Aggregators only: https://vicky.bankbazaar.com/credit-card/sbi-cc-eligibility.html , https://groww.in/credit-card/sbi-simplyclick-credit-card — **treat as unverified** |
| 22 | Platinum Travel | Amex | 18+ | Personal annual income ₹6 lakh+ | ₹6 lakh+; company trading > 12 months | — | Issued only to residents of Delhi/NCR, Mumbai, Bangalore, Chennai, Pune, Hyderabad, Jaipur, Indore, Coimbatore, Chandigarh, Ahmedabad, Surat, Vadodara, Lucknow, Ludhiana, Nagpur, Nasik, Trivandrum, Mysuru; must hold an Indian savings/current account | "I have a good credit history and no payment defaults" | https://www.americanexpress.com/in/credit-cards/platinum-travel-credit-card/ |
| 23 | Membership Rewards (MRCC) | Amex | 18+ | Personal annual income ₹4.5 lakh+ | ₹6 lakh+; trading > 12 months | — | same 19-city list as above | "good credit history and no payment defaults" | https://www.americanexpress.com/in/credit-cards/membership-rewards-card/ |
| 24 | Live+ | HSBC | 18–65 / 25–65 | ₹6,00,000 p.a. | ₹12,00,000 p.a. | SE: PAN + proofs | Indian resident in Chennai, Gurgaon, Delhi NCR, Pune, Noida, Hyderabad, Mumbai, Bengaluru, Kochi, Coimbatore, Jaipur, Chandigarh, Ahmedabad, Kolkata, Amritsar, Baroda, Indore, Lucknow, Nagpur, Surat, Trivandrum | — | https://www.hsbc.bank.in/credit-cards/products/live-plus/ |
| 25 | FIRST Millennia | IDFC FIRST | — | Annual income ₹3 lakh or more | same | — | — | — | https://www.idfcfirst.bank.in/credit-card/millennia ("Eligibility: Annual income of ₹3 lakhs or more") |
| 26 | FIRST Wealth | IDFC FIRST | — | Annual income ₹36 lakh or more | same | — | — | — | https://www.idfcfirst.bank.in/credit-card/wealth |
| 27 | League Platinum | Kotak | 21–60 | ₹5 lakh p.a. and above | same | — | Resident of India; **sourcing cities**: Ahmedabad, Bangalore, Chandigarh, Chennai, Delhi (incl. Gurgaon, Noida), Hyderabad, Kolkata, Mumbai, Navi Mumbai, Pune | — | https://www.kotak.bank.in/en/personal-banking/cards/credit-cards/league-platinum-card.html |
| 28 | Smart | Standard Chartered | 21–65 | "stable monthly income" (no figure) | same | — | "Applicants should belong to credit cards sourcing cities/locations of the Bank"; "subject to credit and other policy checks" | — | https://www.sc.com/in/credit-cards/smart-credit-card/ |
| 29 | All cards (bank-level blog) | IndusInd | 18+; upper 60–75 by card | Min monthly income ₹20,000 | same | — | some cards city-restricted; NRI rules differ | Bank blog lists credit history, utilisation (<30% "favourable"), existing debt as factors | https://www.indusind.bank.in/iblogs/credit-card/eligibility-criteria-for-credit-card/ (bank blog, not a card page; Legend/Platinum pages show no criteria) |
| 30 | LIT | AU SFB | — | — | — | — | au.bank.in blocks bots (403); Wayback capture had no eligibility text | — | **Unverified**; aggregators (select.finology.in) say 21–60 and no stated income |
| 31 | ShopRite / all cards | RBL | — | — | — | — | Product page shows no criteria | — | https://www.rbl.bank.in/personal-banking/cards/credit-cards/shoprite-credit-card (no criteria on page) |
| 32 | Scapia (Federal / BOBCARD / Axis) | Federal, BOBCARD, Axis | — | — | — | — | Federal page is JS-rendered; BOBCARD apply page lists process only ("Provide your occupation, income, address") | — | https://www.federal.bank.in/scapia-federal-bank-credit-card (15 KB, JS) ; https://www.bobcard.co.in/apply-for-credit-card |
| 33 | Kiwi (YES Bank) | YES Bank | — | — | — | — | Issuer page unverified (seed-cards.md); gokiwi.in blog claims 21–60, "CIBIL 650+ considered" — **fintech claim, unverified** | — | https://gokiwi.in/blog/yes-bank-credit-card-apply |

Patterns worth encoding:
- **HDFC** publishes a net-monthly salaried floor and an ITR floor for self-employed, plus an age cap (60 S / 65 SE; Millennia caps at 40 for both). Seven HDFC cards share the ITR > ₹6 lakh SE floor.
- **ICICI** publishes the lowest floors (₹20k–30k/month) and no age cap on the page; Sapphiro's page is the only one found that explicitly says credit score and repayment history are considered.
- **Axis** publishes age 18–70 and "Resident of India" on every card, income only on the premium cards, and labels all criteria "indicative".
- **Amex, HSBC, Kotak, Standard Chartered** publish **serviceable-city lists** (Amex 19 cities, HSBC 21, Kotak 10, SC "sourcing cities" without a list). The app must gate on PIN code / city for these issuers.
- **Invite/relationship-only**: Infinia Metal (invite only); Magnus for Burgundy (Burgundy relationship, LTF for Burgundy Salary accounts from 1 Jul 2026 per seed-cards.md).

---

## B. Credit-score conventions and bureau access

### B1. Score bands that issuers and communities treat as approvable

| Band (CIBIL 300–900) | How sources describe it | Source |
|---|---|---|
| 750+ | "For credit cards, 750 is the required minimum CIBIL score" (Bank of Baroda); "approximately 79% of loans and credit cards approved in India go to individuals with a CIBIL score of 750 or above" (Paisabazaar) | https://bankofbaroda.bank.in/banking-mantra/digital/articles/cibil-score-for-credit-card ; https://paisabazaar.com/credit-score/cibil-score-for-credit-card/ |
| 700–749 | "standard cards generally require 700–749"; "several banks do accept a credit score between the range of 700-750" | https://www.iifl.com/index.php/blogs/credit-score/how-much-cibil-score-is-required-for-credit-card ; https://cardadvisor.in/articles/cibil-score-credit-card-eligibility-guide |
| 650–699 | "Entry-level cards may be available from 650–699 with limited credit limits" | IIFL blog above |
| < 700 | "A CIBIL score below 700 is the #1 killer"; "most major banks like HDFC, ICICI, SBI Card, and Axis want 720+ for mid-tier and premium cards" (aggregator claim) | https://cardtrail.in/basics/credit-card-rejected-india-what-to-do/ |
| Community floor | TechnoFino posters say "at least 760" before applying for Amazon Pay ICICI; a 772-score ICICI customer was still rejected | TechnoFino thread https://technofino.in/community/threads/amazon-pay-icici-card-rejection-reason.20878/ (via search snippet; Wayback capture was a Cloudflare page) |
| CRED sign-up bar | "credit score of at least 750 to be able to sign up for CRED" | https://techcrunch.com/2021/04/06/indias-cred-valued-at-2-2-billion-in-new-215-million-fundraise |

No issuer page fetched in this pass publishes a numeric minimum score. Only aggregator/bureau/community sources do. The rubric in §D therefore uses 750 / 700 / 650 as band edges and flags them as convention, not policy.

### B2. The four bureaus and how they differ

| Bureau | Score range | Notes | Source |
|---|---|---|---|
| TransUnion CIBIL | 300–900 | Most-cited by issuers and community ("CIBIL" is used as a synonym for credit score). Free score + report once per calendar year on cibil.com (next free report 1 Jan of the following year) | https://cibil.com/freecibilscore ; https://www.cardtrail.in/glossary/glossary-cibil-score-india/ |
| Experian India | 300–900 | Free score on experian.in; paid report subscription ₹499/year; "Experian V4" is the current consumer score; free score also via WhatsApp (Gupshup) | https://www.experian.in/consumer/ (page text: "Subscribe for just ₹499/year", "Free Experian Credit Score"); https://www.experian.in/2022/11/09/experian-india-to-offer-free-credit-scores-on-whatsapp/ |
| Equifax India | 300–900 | RBI-licensed CIC since 2010; consumer portal "ePort"; free report via bankbazaar co-brand | https://www.bankbazaar.com/equifax/free-equifax-credit-score-report.html ; https://www.smfgindiacredit.com/knowledge-center/what-is-equifax-eport.aspx |
| CRIF High Mark | 300–900 | Fourth CIC; consumer score sold through fintech partners | https://en.wikipedia.org/wiki/CRIF_High_Mark_Credit_Information_Services ; https://www.paisabazaar.com/credit-score/crif-highmark-credit-score/ |
| All four | — | RBI directive: every CIC must give individuals one **free full credit report (incl. score) per calendar year**, effective 1 Jan 2017 | https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=10590 |

Community caution (TechnoFino Amazon Pay thread, via snippet): issuers may pull any bureau, so a rejection with a good CIBIL score can come from a derogatory mark on CRIF/Equifax/Experian; members advise checking all four.

### B3. Which free tool uses which bureau (for the "paste your score" onboarding step)

| Free tool | Bureau(s) | Source |
|---|---|---|
| cibil.com free score | CIBIL (1/year) | https://cibil.com/freecibilscore |
| experian.in / Experian WhatsApp | Experian | https://www.experian.in/consumer/ |
| Paisabazaar | Experian (original partnership) — now shows CIBIL, Equifax, CRIF as well | https://www.biia.com/paisabazaar-com-launches-free-credit-report-campaign ; https://www.paisabazaar.com/credit-score/what-is-experian-credit-information-report/ |
| BankBazaar | Experian (Experian is an investor) ; Equifax co-brand page | https://blog.bankbazaar.com/check-your-experian-credit-score-for-free-at-bankbazaar-com/ ; https://inc42.com/?p=105317 |
| Google Pay | CIBIL ("authorizes Google Pay to get your credit report and score from CIBIL") | https://support.google.com/pay/india/answer/13017211?hl=en-GB |
| PhonePe | CIBIL | https://moneyview.in/cibil-score/how-to-check-cibil-score-in-phonepe (third-party description) |
| OneScore | CIBIL and Experian | https://www.theweek.in/wire-updates/business/2025/05/02/dcm23-onescore-app.html |
| CRED | CIBIL (per search summaries; CRED's own page not fetched) — **unverified** | https://freo.money/credit/best-credit-score-check-apps/ |
| Wishfin | CIBIL (partnership) | https://channeldrive.in/applications/wishfin-com-partners-transunion-cibil/ |

### B4. Consumer-consented bureau APIs a startup could use

| Bureau product | What it is | Partnership / pricing | Source |
|---|---|---|---|
| TransUnion CIBIL "DTC Consumer Connect Services" | "standardized web service for Partner/Members to access credit products with a seamless consumer authentication. Currently this service offers the CIBIL Credit Information Report (CIR) along with the CIBIL Score ... via a consent-based model" | Listed on CIBIL's API marketplace; page returns 403 to bots, so partner requirements and pricing were **not readable**. Known DTC partners: Paisabazaar, Wishfin, Google Pay, PhonePe (B3). No published price found | https://apimarketplace.transunioncibil.com/products/credit-data/dtc-consumer-connect-services (search snippet) |
| Experian India consumer-consent pull | OTP-based consent flow (name, DOB, mobile → OTP → PAN etc.) used by partners such as BankBazaar, Paisabazaar, Gupshup/WhatsApp | Partnership-based; no public price list found. Resellers (Meon, AuthBridge, Surepass) sell "Experian credit report API" to businesses | https://meon.co.in/experian-credit-report-api ; https://authbridge.com/checks/experian-credit-report/ ; https://startup2.outlookindia.com/sector/fintech/experian-and-gupshup-partners-to-offer-free-credit-scores-on-whatsapp-news-7131 |
| Experian Connect (US) | Consumer authorises Experian to share report with third parties | **US product**, not India — do not rely on it | https://www.experian.com/connect/legal/terms |
| CRIF High Mark | Consumer report API available through resellers (Surepass "Crif Credit Report API": name, mobile, DOB, PAN) | Reseller pricing not published; direct CRIF partnership terms not found | https://surepass.io/crif-credit-report-api/ |
| Equifax India | Partnerships with fintechs (MyMoneyKarma); "ePort" consumer portal | No public API/pricing page found | https://app.dealroom.co/companies/mymoneykarma |

Conclusion for the app: a consent-based bureau pull is possible only through a bureau partnership (CIBIL DTC, Experian partner programme) or a KYC/data reseller; none publishes pricing. Phase 1 should accept a **user-entered score + bureau name + date** and treat it as self-reported. Any live pull is a soft enquiry (B5).

### B5. Soft vs hard enquiry

- Hard enquiry: "Triggered by a formal credit application ... Reduces score by 5–10 points and is visible to all lenders for 2 years." Soft: "checking your own score, pre-approved offers ... No score impact." — https://www.cardtrail.in/basics/credit-score-basics-india-beginners/
- "Before sending such an offer, card issuers usually review your credit profile ... through a soft enquiry ... when you apply, the card issuer performs a hard enquiry" — https://www.paisabazaar.com/credit-score/do-pre-approved-credit-card-offers-affect-your-credit-score-aio/
- AU Bank blog on hard vs soft: https://www.au.bank.in/blogs/hard-vs-soft-credit-inquiry

---

## C. Community-observed approval patterns (anecdotes)

All items below are single-user reports from r/CreditCardsIndia (via the Arctic Shift archive, post IDs link as `https://www.reddit.com/r/CreditCardsIndia/comments/<id>`) or TechnoFino (via search snippets; direct and Wayback fetches return Cloudflare pages). They are **anecdotes**, not issuer policy. Dates are post dates.

### C1. Amazon Pay ICICI
- 2026-10-04, 151↑, `1wxiqix` "ICICI Coral → Amazon Pay ICICI route": poster rejected for Amazon Pay despite employer having a corporate relationship with ICICI; holds SBI Tata Neu (₹28k limit); asks whether taking Coral first (bank relationship) then switching is viable.
- 2026-09-28, 31↑, `1ws5b8q` "Amazon icici": "They already rejected 2 times despite having 770+ cibil with 1+ years history and no late payment"; poster calls approval "pure luck nowadays".
- 2026-06-22, 133↑, `1ucep88`: approved with ₹1.4L limit after earlier Slice/Roarbank rejections; poster attributes the earlier rejections to "multiple enquiries".
- 2026-09-25, 17↑, `1wpy3zc`: Amazon ICICI rejected; IDFC Millennia and Flipkart Axis approved; CIBIL 752 → 728 after ~15 applications in a month; income ~₹50k/month.
- 2026-09-15, 42↑, `1wgpp2m`: 22-year-old student, CIBIL 773 (4 y 2 m history, 180+ on-time payments), **income 0**, holds Kotak FD card, IndusInd Aura Edge, IDFC Millennia, BNPL lines — rejected 8 months earlier, asking whether score alone can carry an application (community view: no income → no).
- 2026-10-04, 2↑, `1wx4x8w`: self-employed, **no ITR**, CIBIL 770, rejected twice before; application now shows "added you to waitlist as per Bank's credit card checks".
- 2026-10-02, 3↑, `1wvnu03`: after applying, ICICI phoned to ask whether the applicant held other cards or an existing ICICI relationship — i.e. relationship and existing-card questions are part of ICICI's screen.
- TechnoFino thread 20878 "Amazon pay ICICI card rejection reason" (started 18 Dec 2023; Wayback capture read 7 Oct 2026): OP "I have 3 icici card and icici sb account. 772 cibil score" rejected for "internal policies". Replies: "Did you take any CC from icici in the last 6 months?" (6-month cooldown after an ICICI card); "Bre = bureau score. Its other than cibil score" (ICICI's rejection letter cites a bureau score that may not be CIBIL). https://technofino.in/community/threads/amazon-pay-icici-card-rejection-reason.20878/
- Pattern: high rejection rate even at 770+; seed-cards.md records a 226↑ "6th rejection" thread (`1q7ge7s`). Common cited reasons: recent enquiries, thin file (<1 year), no income/ITR, an ICICI card issued in the last 6 months, "internal policy".

### C2. Cashback SBI Card
- 2026-01-09, 57↑, `1q8cruw` "Finally got my hands on the SBI Cashback – after a proper roller coaster": multi-attempt approval story; posted because "many people here struggle with getting SBI Cashback".
- 2026-09-27, 18↑, `1wrikfu`: holder reports SBI Cashback + PhonePe Select Black on a shared ₹1.15L limit (SBI shares limit across its cards).
- 2026-10-05, 7↑, `1wyhjd8`: SBI salary account + 5-year-old SimplyCLICK, CIBIL 789 — Cashback SBI Card rejected repeatedly for 2–3 years. (SBI relationship did not help.)
- 2026-09-12, 19↑, `1weo5y6`: 24-year-old new-to-credit: rejected by HDFC Pixel and Flipkart Axis, approved for SBI SimplySAVE RuPay.
- TechnoFino thread 40195 "Sbi cashback card rejected - pin code issue" (2026; Wayback capture read 7 Oct 2026): applicant "directly rejected after DigiLocker KYC" for over a year despite a good CIBIL, a Canara card (₹50k, pre-approved) and a Flipkart Axis card (₹91k); OP notes "an existing overdraft loan of 5 lakhs and a personal loan of 4 lakhs"; title attributes it to PIN code. https://technofino.in/community/threads/sbi-cashback-card-rejected-pin-code-issue.40195/
- Other TechnoFino posts (tag sbicashbackcreditcard, via search snippets): CIBIL >760 with >10 cards declined; SBI's letter says the application "didn't meet policies set forth for issuance ... purely a business decision"; another's score fell from 780+ to <755 after four applications in a year. https://technofino.in/community/tags/sbicashbackcreditcard/
- TechnoFino thread 258 "How Many Credit Cards Are Allowed Per Customer" (Mar 2022; Wayback capture from an earlier session): admin states "SBI offers 3 cards per customer and separate limit"; HDFC second card is "on approval basis... request your RM". https://technofino.in/community/threads/how-many-credit-cards-are-allowed-per-customer.258/
- Pattern: PIN-code serviceability, existing unsecured debt (OD/PL), and "too many cards" are the recurring rejection reasons; SBI gives no specific reason; an SBI salary account does not appear to help.

### C3. HDFC Regalia Gold / Millennia / Tata Neu (HDFC relationship cards)
- 2026-09-11, 145↑, `1wdkqjc` "Experience getting approved for HDFC Regalia Gold as my 1st unsecured card": age 22, CIBIL **724**, no prior HDFC relationship, only an IDFC WOW FD-backed card (₹30k FD) opened that month; opened an HDFC **corporate salary account** two weeks earlier and deposited ₹1L (no salary credit yet); applied via the HDFC app and was approved with a **₹6L limit**. Strongest single data point that the corporate-salary-account flag dominates score and history at HDFC.
- 2026-09-17, 42↑, `1wimwgb` "Got my first credit card – HDFC Regalia Gold": salary ₹1.5L/month, CIBIL 741, HDFC Preferred salary account for 6 years — approved as a **first card** at a 741 score, i.e. the salary relationship outweighed a sub-750 score.
- 2026-09-16, 36↑, `1whp6cd` "HDFC Millennia Finally Approved": 2-year HDFC savings account; applied after closing Pixel Play; physical office verification was required (agent visit).
- 2026-09-23, 13↑, `1wo4r4g`: Freedom → Millennia RuPay upgrade initially rejected because HDFC wanted current salary slips (applicant had moved to own business); approved after submitting latest ITR/business proof.
- 2026-09-15, 2↑, `1wgupgz`: 21-year-old, ₹25k/month, HDFC salary account, first card from Slice on 14 Aug 2026; HDFC's LTF offer was **Pixel only** (the entry product offered to thin files).
- 2026-10-03, 42↑, `1wwd8hj`: CIBIL 775+, salary ₹1.9L/month, new salary account at HDFC → Regalia Gold sold by a rep as LTF (LTF claim disputed).
- 2026-09-27, 30↑, `1wrq99k` "HDFC Millennia pre-approved offer through salary account?": salary account opened 29 Jun 2026, two credits, asking how many salary credits before a pre-approved offer appears.
- 2026-01-03, 374↑, `1q2ji12` "Closed all HDFC cards → waited 6 months → got better pre-approved offers + 3× credit limit": 10-year relationship had limit stuck at ₹1.6L; closing and re-applying after 6 months produced better pre-approved offers.
- 2026-04-03, 185↑, `1sbifrf` "Why does HDFC play hard to get with some customers?": multi-year rejection saga despite SMS "approved" messages.
- 2026-09-27, 15↑, `1wrm8d4`: Swiggy HDFC LTF offer by email, then rejection, then eventually approved after escalation.
- 2026-09-30, 6↑, `1wtv71l`: HDFC refused a card switch from Tata Neu Plus to Millennia at level 1; got it on escalation.
- Pattern: HDFC approvals cluster around **salary account + pre-approved offer in NetBanking**; cold applications are frequently rejected regardless of score.

### C4. HDFC Infinia / Diners Club Black Metal (upgrade path)
- 2026-07-03, 71↑, `1umit4c` "Upgraded from HDFC Regalia Gold to Diners Club Black Metal": salaried, net monthly > ₹2.5L, existing Regalia Gold, ~₹10L annual card spend, Axis Burgundy account — upgrade granted.
- 2025-11-11, 5↑, `1ou91a7`: "My dad got his infinia approved recently" (no profile numbers).
- Pattern: Infinia/DCB Metal come via upgrade from an existing HDFC card with high spend, or via invite; matches the official "By Invite Only" label. Spend and existing-HDFC-card are the signals, not a fresh application.

### C5. Axis Magnus / Atlas / Select (Burgundy and salary relationship)
- 2026-06-19, 45↑, `1u9rnb2` "Got LTF Axis Magnus Credit Card in salary account": Select LTF came with a Burgundy Salary account opened Aug 2025; Magnus LTF followed via the employer tie-up — consistent with seed-cards.md (Magnus LTF for Burgundy Salary from 1 Jul 2026).
- 2026-07-16, 26↑, `1uy1u6t` "Axis Bank works in mysterious ways": Atlas approved with ₹1.2L limit; limit-enhancement requests with income proof failed; later a pre-approved offer appeared in-app.
- 2026-09-24, 56↑, `1worr8g`: Axis Privilege Amex rejected on 15 Sep 2026; after nodal-officer escalation and opening a savings account, pre-approved offers appeared.
- 2026-09-26, 17↑, `1wqkob7`: Flipkart Axis limit raised ₹22,000 → ₹1,42,000 after providing income proof ahead of the sale season.
- Pattern: Axis co-brands (Flipkart, Airtel) approve with low limits and no stated income floor; Magnus/Atlas approvals correlate with Burgundy or salary relationships; "open a savings account, wait for the in-app offer" is the community's workaround.

### C6. Flipkart Axis / IDFC FIRST Millennia / other LTF entry cards
- 2026-09-25, 17↑, `1wpy3zc`: income ~₹50k/month, CIBIL 752: IDFC Millennia LTF and Flipkart Axis approved out of ~15 applications; Amazon ICICI rejected.
- 2026-09-09, 101↑, `1wbifg8` "I applied 5 cards got 2 approved (got first cc)": income ₹1.5L/month salaried, first cards.
- 2026-09-12, 9↑, `1we3ayg`: rejected by ICICI Amazon, HDFC and Axis for "no credit history" even with an Axis salary account; built history with an FD-backed Axis MyZone for 15 months, then became eligible.
- 2026-09-25, 58↑, `1wpqlhv` "My 6 months Credit Card journey": 23M, no income, started with a SuperMoney FD card (₹10k deposit); CIBIL rose from ~740 over Mar–Jul.
- Pattern: for new-to-credit users the reliable path is FD-backed card → 6–15 months → LTF entry cards (IDFC Millennia, Flipkart Axis, Kotak); Amazon ICICI remains the hardest of the entry cards.

### C7. Amex (Platinum Travel / MRCC)
- 2026-10-04, 27↑, `1wxhe76`: 37-year-old salaried ₹1L+/month, CIBIL 763, 2 years history — holds Amex Privilege (newest) plus Axis Neo, Airtel, Swiggy ORNGE, IDFC Millennia.
- 2026-06-10, 23↑, `1u1rb3n`: holds Amex Platinum Travel with ~₹10L annual spend on it.
- Pattern (thin): Amex approvals reported at ~₹1L/month salaried in serviceable cities; the official gate is the 19-city list and ₹4.5L/₹6L income.

### C8. HSBC Live+ / RuPay Platinum
- 2026-09-29, 6↑, `1wt36gx`: fresh MBA grad, CIBIL ~766, utilisation <10%, HSBC Live+ "came with salary account" (4 cards in 6 months).
- 2026-09-28, 2↑, `1wshcs5` "HSBC RuPay Platinum rejected despite having CTC more than required 6L": CTC ₹8.5 LPA, take-home ₹63,130/month, CIBIL ~740, **2 months in current job** — rejected with "Income below required thresholds". Suggests HSBC's floor is applied to net (take-home ≈ ₹7.6L) or with a tenure condition, not to CTC; the app should compare **net** income to floors and collect `months_in_current_job`.
- seed-cards.md records the 132↑ "Influencers hyped HSBC cards… reality is very different" thread (`1sew2dp`).
- Pattern: Live+ via salary/Premier relationship; city gate applies (21 cities, §A); recent job change is a reported rejection reason.

### C8a. IDFC FIRST Wealth / Millennia
- 2026-07-24, 4↑, `1v5ox2l` "Applied for IDFC Wealth. The bank had other plans": passed VKYC and residence verification, approved — but for **Millennia**, not Wealth. IDFC downgrades the product rather than rejecting; the app should model "approved for a lower variant" as an outcome.
- 2026-08-16, 3↑, `1vpvfpj`: ₹27k/month, CIBIL 773, **31 enquiries**, 6 cards (incl. HDFC MoneyBack+, Axis Flex, ICICI Coral) — recent AU/IDFC/YES rejections; planning a 6–9-month "credit detox". Shows score can stay high (773) while enquiries alone drive rejections.

### C9. Cross-card: "too many enquiries"
- 2026-01-26, 4↑, `1qnd3he` "Multiple Credit Card Rejections Despite 770 CIBIL": 22-year-old freelancer, history built on BNPL (Snapmint), score 770 → 751 after a burst of applications; rejected everywhere — income proof and thin file, not score, were the blockers.
- 2026-05-23, 3↑, `1tld8h5`: FD-backed card holder, CIBIL 768, "applied to many" and all rejected including Swiggy ORNGE.
- 2026-03-03, 2↑, `1rjxs8x`: SimplyFi (secured) Federal card for a year, closed, then Scapia applied.

---

## D. Draft likelihood rubric

### D1. Factors with issuer and community agreement

| Factor | Issuer-side evidence | Community-side evidence | Direction |
|---|---|---|---|
| Hard enquiries, last 6 months | Each hard enquiry ~5–10 points, visible 2 years (cardtrail); "more than 3-4 enquiries within six months" is a red flag and "six or more enquiries in 12 months can lead to automatic rejection" (Airtel finance blog: https://www.airtel.in/blog/free-credit-report/too-many-credit-enquiries-heres-how-to-recover-fast/) | `1wpy3zc` (15 applications → 752→728, most rejected), `1ucep88`, `1qnd3he`, TechnoFino "780+ → <755 after four applications" | Strong negative above 3 in 6 months |
| Credit score band | 750+ convention (BoB, Paisabazaar); 700–749 standard; <700 rejection driver (B1) | Approvals seen at 741 with salary account (`1wimwgb`); rejections at 770+ without relationship (`1ws5b8q`) | Score sets the ceiling; relationship moves within it |
| Credit history length | Amex: "good credit history and no payment defaults" | "no credit history" rejections (`1we3ayg`), "apply after 1 year of first card" (TechnoFino) | <12 months → Low for unsecured non-entry cards |
| Utilisation | IndusInd blog: <30% favourable | `1wt36gx` cites <10% utilisation as a positive | Mild |
| Number of existing cards | — (no issuer page states a cap) | SBI declined a >10-card, 760+ applicant (TechnoFino); Axis rejection letters cite "high number of active cards" (cardtrail) | Negative past ~5–6 cards for SBI/Axis; irrelevant for upgrades |
| Salary account / banking relationship with issuer | Magnus LTF for Burgundy Salary (Axis campaign T&C, seed-cards.md); Kotak/SC/HSBC sourcing-city rules imply branch relationship | `1wimwgb`, `1wwd8hj`, `1u9rnb2`, `1worr8g`, `1wrq99k` | Strong positive (often the deciding factor for HDFC/Axis) |
| Pre-approved offer visible in NetBanking/app | Paisabazaar: pre-approval = issuer soft-checked you; not a guarantee | `1q2ji12`, `1uy1u6t`, `1worr8g` | Strongest single positive signal |
| FD-backed card history | — | `1we3ayg`, `1wpqlhv`, `1tld8h5` | Positive for new-to-credit → entry cards only |
| Employer category / corporate tie-up | HDFC publishes separate govt vs non-govt NMI floors (Regalia Gold ₹1L vs ₹1.5L) | `1u9rnb2` (company tie-up gave Magnus LTF), `1wxiqix` (corporate relationship did not help with Amazon ICICI) | Positive, issuer-specific |
| Self-employed with ITR | HDFC/Axis/Amex/HSBC publish ITR floors; Amex needs 12 months trading | `1qnd3he` freelancer without ITR rejected everywhere | Gate: no ITR → Low for all cards with an ITR floor |
| City / PIN serviceability | Amex 19 cities, HSBC 21, Kotak 10, SC "sourcing cities" | SBI PIN-code rejection (TechnoFino 40195) | Hard gate where a list is published; soft negative for SBI |
| Income vs published floor | §A | `1wimwgb` approved at 1× floor with relationship | Gate at the floor; comfortable margin (≥1.5×) is positive |

### D2. Inputs the app must collect

| Input | Type | Used by |
|---|---|---|
| `age` | int | gates (21+/18+, caps 40/60/65/70) |
| `employment_type` | salaried / self_employed / student / none | gates, ITR requirement |
| `employer_category` | govt / psu / listed / private / self | HDFC govt floors; employer tie-ups |
| `net_monthly_income` (salaried) | ₹ | HDFC/ICICI/SBI floors |
| `itr_annual_income` (self-employed) | ₹ or null | HDFC/Axis/Amex/HSBC ITR floors |
| `itr_filed_last_2_years` | bool | SE gate |
| `pin_code` → city | string | Amex/HSBC/Kotak/SC lists; SBI soft gate |
| `credit_score` + `bureau` + `score_date` | int, enum(CIBIL/Experian/Equifax/CRIF), date | band |
| `credit_history_months` | int | thin-file gate |
| `hard_enquiries_6m` | int | enquiry penalty |
| `utilisation_pct` | int | mild |
| `existing_cards` (issuer, product, limit, LTF) | list | card-count penalty, upgrade paths, same-issuer exposure |
| `relationship` per issuer: salary_account / savings_account / fd / burgundy_or_wealth_tier | enum set | relationship bonus |
| `preapproved_offers_seen` (issuer, product) | list | strongest positive |
| `fd_backed_card_history_months` | int | NTC path |
| `late_payments_24m` | int | Amex "no payment defaults"; hard negative |
| `months_in_current_job` | int | HSBC rejection at 2 months (`1wshcs5`); Amex SE "trading > 12 months" |
| `unsecured_loans_outstanding` (PL/OD ₹) | ₹ | SBI rejection with ₹9L OD+PL (TechnoFino 40195); IndusInd blog "existing debt levels" |
| `same_issuer_card_issued_last_6m` | bool | ICICI 6-month cooldown (TechnoFino 20878) |

### D3. Rubric (draft; band edges are conventions from B1, weights are a starting point to tune against outcome data)

Step 1 — hard gates (fail → "Not eligible", no band):
- age outside the card's published range; employment type without a published floor (e.g. student with no income for cards that publish one);
- salaried NMI < published floor, or self-employed ITR < published floor, or self-employed with no ITR where a floor is published;
- PIN code outside a published city list (Amex, HSBC, Kotak, SC);
- card is invite-only / relationship-only and the user lacks that relationship (Infinia Metal; Magnus for Burgundy).

Step 2 — score points (start at 0):

| Factor | Signal | Points |
|---|---|---|
| Score band | ≥750 | +3 |
| | 700–749 | +1 |
| | 650–699 | −2 |
| | <650 or late payment in 24 m | −5 |
| | unknown (not entered) | 0, and cap band at Medium |
| Hard enquiries, 6 m | 0–1 | +1 |
| | 2–3 | 0 |
| | 4–5 | −2 |
| | ≥6 | −4 |
| Credit history | <6 m | −4 (entry/FD cards exempt) |
| | 6–12 m | −2 |
| | >24 m | +1 |
| Income margin vs floor | ≥2× floor | +2 |
| | 1–2× | +1 |
| Relationship with issuer | pre-approved offer visible | +4 |
| | salary account | +3 |
| | savings account / FD | +1 |
| | none | 0 |
| Existing cards | 0 (new-to-credit) | −1 for non-entry cards |
| | 1–4 | 0 |
| | 5–8 | −1 (SBI/Axis −2) |
| | >8 | −3 |
| Same-issuer exposure | already holds a card from the issuer | +1 for upgrade-type cards (Regalia→DCB, Select→Magnus); −1 for co-brand caps (ICICI Amazon Pay when other ICICI cards exist, per TechnoFino) |
| Utilisation | <30% | +1 ; >70% −1 |
| Employer tie-up with issuer | yes | +2 |
| Job tenure | <6 months in current job | −1 (HSBC/Amex −2) |
| Unsecured loans outstanding | PL/OD > 6× monthly income | −2 |
| Same issuer issued a card in last 6 months | yes | −2 (ICICI) |
| Income entered as CTC rather than net | — | convert to net before the gate; if unknown, apply 0.85× and flag |

Step 3 — band: **High ≥ 6**, **Medium 2–5**, **Low ≤ 1**. Cards with a known hard community pattern (Amazon Pay ICICI, Cashback SBI) carry a −1 "issuer strictness" adjustment until outcome data replaces it.

### D4. Worked example

User: 29, salaried at a private company for 3 years (no outstanding PL/OD), NMI ₹90,000 (net, not CTC), HDFC salary account for 3 years, CIBIL 742 (checked on cibil.com last month), credit history 4 years, 2 hard enquiries in last 6 months, utilisation 20%, holds 3 cards (SBI SimplyCLICK, Flipkart Axis, Amazon Pay ICICI), no pre-approved offer visible, Bengaluru PIN.

- **HDFC Regalia Gold**: gate fails — NMI ₹90k < ₹1.5L non-govt floor → "Not eligible" (the app should show the floor and suggest Millennia / Tata Neu Plus).
- **HDFC Millennia**: gates pass (21–40, NMI > ₹35k). Points: score 700–749 +1; enquiries 2 → 0; history >24 m +1; income margin 90k/35k ≥2× +2; salary account +3; 3 cards 0; utilisation +1 → **8 → High**. Community support: `1wimwgb` (Regalia Gold approved at 741 with a salary account).
- **Amazon Pay ICICI** (already held) — skip. **ICICI Coral**: gates pass; points: +1 +0 +1 +2 (90k/20k) + 0 relationship + 0 cards + 1 utilisation − 1 same-issuer co-brand caution → **4 → Medium**.
- **Amex MRCC**: Bengaluru is on the list; income ₹10.8L > ₹4.5L. Points: +1 +0 +1 +2 +0 +0 +1 → **5 → Medium**.
- **HSBC Live+**: Bengaluru on list; ₹10.8L > ₹6L. Same arithmetic → **5 → Medium**.
- **Cashback SBI Card**: no published floor; points +1 +0 +1 +0 (no floor) +0 +0 +1 −1 strictness → **2 → Medium** (low end).
- **Infinia Metal**: invite-only gate → "Not eligible (invite only)".

---

## E. Public eligibility / pre-approval tools

| Tool | What it does | Enquiry type | Source |
|---|---|---|---|
| Issuer NetBanking / app "pre-approved offers" (HDFC NetBanking, Axis app, ICICI iMobile) | Shows cards the issuer has already soft-screened you for | Soft until you apply, then hard | https://www.paisabazaar.com/credit-score/do-pre-approved-credit-card-offers-affect-your-credit-score-aio/ ; community `1q2ji12`, `1uy1u6t`, `1worr8g` |
| Paisabazaar "check credit card eligibility" | Mobile OTP + occupation + details → list of cards "as per your eligibility"; also free multi-bureau score | Soft (Paisabazaar states checking does not affect score); application to the issuer is hard | https://www.paisabazaar.com/credit-score/soft-inquiry-vs-hard-inquiry-aio/ ; https://www.paisabazaar.com/axis-bank/credit-card-eligibility/ |
| BankBazaar | Free Experian score + card eligibility; "BankBazaar will make a soft enquiry on your behalf which will not affect your Credit Score" | Soft | https://blog.bankbazaar.com/check-your-experian-credit-score-for-free-at-bankbazaar-com/ ; https://blog.bankbazaar.com/unlocking-credit-how-to-boost-your-approval-chances-for-credit-cards/ |
| CRED | Score tracking (CIBIL per third-party descriptions) and card offers; sign-up historically required ≥750 | Soft for score; no public statement found on an eligibility checker | https://techcrunch.com/2021/04/06/indias-cred-valued-at-2-2-billion-in-new-215-million-fundraise ; https://apps.apple.com/in/app/cred-credit-cards-payments/id1428580080 |
| CheQ | Bill-payment and credit-health app positioned against CRED; no eligibility-checker claim found | — | https://www.cbinsights.com/compare/cheq-4-vs-cred-3 ; https://cxotoday.com/newsletter/3-platforms-to-look-for-to-manage-your-credit-score-in-2023/ |
| Issuer "check eligibility" pages (Axis per-card "Eligibility & Documentation" tab; SC "Eligibility & Documents"; Amex self-declaration checklist) | Static criteria, no bureau pull | None | §A sources |
| Axis "Insta Easy" (FD-backed) and other secured cards | Guaranteed issuance against FD; path for new-to-credit users | No bureau gate | Axis listing https://axisbank.com/retail/cards/credit-card/axis-bank-insta-easy-credit-card-bkup/features-benefits (old domain) ; community `1we3ayg`, `1wpqlhv` |

Caveat: no aggregator publishes its matching logic; "eligible" on Paisabazaar/BankBazaar means passes published floors plus the aggregator's own soft score pull, not issuer approval.

---

## F. Unverified / gaps

1. **SBI Card income floors** — sbicard.com pages are JS-rendered; the ~₹18k–20k/month figure is aggregator-only (BankBazaar, Groww). Need a headless fetch or SBI Card KFS/FAQ.
2. **AU LIT eligibility** — au.bank.in 403s and the Wayback capture had no eligibility text; "21–60, no income floor" is from select.finology.in.
3. **Axis ACE income** — only the old-domain eligibility page snippet (18–70, resident, income proof). The new-domain page has no eligibility text in HTML.
4. **RBL, IndusInd per-card floors** — IndusInd ₹20k/month is from the bank's blog, not product pages; RBL product page has no criteria; BankBazaar says RBL 21–65.
5. **Kiwi / YES Bank** — gokiwi.in blog (fintech) claims 21–60 and "CIBIL 650+ considered"; no YES Bank page confirms.
6. **Scapia (Federal / BOBCARD)** — no eligibility text found on either issuer page.
7. **CIBIL DTC Consumer Connect pricing and partner requirements** — API marketplace page returns 403; only the product description is known.
8. **Experian / Equifax / CRIF partner pricing** — none published; reseller APIs exist (Meon, AuthBridge, Surepass).
9. **CRED's bureau** — third-party descriptions say CIBIL; CRED's own page not fetched.
10. **HDFC IndianOil NMI** — page says ₹12,000 in the eligibility block and ₹10,000 in the FAQ.
11. **Numeric score minimums by issuer** — none found on any issuer page; all bands in B1 are bureau/aggregator/community conventions.
12. **TechnoFino thread detail** — WebFetch cannot reach web.archive.org; `curl` of `web.archive.org/web/2026id_/<url>` works but returns gzip bodies (decompress before parsing). Threads 20878, 40195 and 258 were read this way; the tag page sbicashbackcreditcard is from search snippets only. Thread 16806 (Axis rejection) has no Wayback capture (404). Thread 40195's capture shows "Saturday" as the post date, so the exact 2026 date is unknown.
13. **Rubric weights** — the point values in D3 are a design starting point, not derived from data; band edges 750/700/650 are conventions (B1).
14. **Arctic Shift coverage** — the API returned "Timeout. Maybe slow down a bit" for roughly half of the queries even with 8–12 s spacing and three retries; anecdotes in §C come from the queries that succeeded ("atlas approved income", "swiggy hdfc rejected", "magnus approved", "icici rejected cibil", "too many enquiries rejected", "salary account pre-approved", "amazon pay icici rejected", "sbi cashback rejected", "tata neu rejected", "millennia rejected", "idfc millennia approved") plus `/api/posts/ids` lookups. No successful query for Flipkart Axis, Regalia Gold (as a query term), HSBC, Amex, AU LIT, Airtel Axis, Atlas rejection, Scapia or Coral; those cards' entries rest on posts surfaced by other queries. Re-run per §5 of seed-cards.md to widen coverage.
15. **Thread `1wshcs5` (HSBC)** — the inference that HSBC applies the ₹6L floor to net income or job tenure is the poster's and this document's guess; HSBC gave only "Income below required thresholds".
