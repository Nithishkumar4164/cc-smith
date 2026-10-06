# r/CreditCardsIndia — pain-point sweep (Oct 2026)

## Method and caveats
- Reddit blocked every direct route (web, JSON endpoints, mirrors, browser extension). Data came from the public Arctic Shift Reddit archive API: all ~56,879 posts from r/CreditCardsIndia for 2025-10-01 → 2026-10-06 (title, body, score, comments, flair) plus comment trees (top ~10) of 55 selected posts. Scores are live Reddit scores.
- Frequency labels are regex counts over title+body of all posts: *very common* ≈ >5% of posts (≥3,000), *common* ≈ 1–5% (500–3,000), *occasional* ≈ <1%. Flair mix: 20k "Help Needed/Question", 8.3k "General Discussion", 4.8k "Card Recommendation", 542 "Devaluation".

---

## 1. Choosing a card
**1a. "Which card should I get for X" is the single most repeated question type** — very common (~5,000 posts; 4,776 Card Recommendation flair). Askers post salary/CIBIL/spend profile and wait for strangers to compute it.
- https://www.reddit.com/r/CreditCardsIndia/comments/1taflx5 (225↑) ; https://www.reddit.com/r/CreditCardsIndia/comments/1rarm4z ("Which cards should I keep, close, or replace?")

**1b. Too many opinions / no way to decide; people default to whatever the RM sold them** — common (~1,700 "confused" posts).
- "there are SO many opinions on this sub alone. So I just never did anything." (450↑) https://www.reddit.com/r/CreditCardsIndia/comments/1r9t68x
- "I'm just fed up with these Infinia and regalia guys, it's too overwhelming." https://www.reddit.com/r/CreditCardsIndia/comments/1qlfodr

**1c. Beginners / first card: don't know how to start, get rejected, get hostile answers** — common (~2,100 posts).
- "803 CIBIL but getting rejected for every first credit card" (180↑) https://www.reddit.com/r/CreditCardsIndia/comments/1uzvgmi ; https://www.reddit.com/r/CreditCardsIndia/comments/1ou1qbm

**1d. Card looks good on paper but reality differs (MCC exclusions, caps, rounding) and nobody warned them** — common.
- Tata Neu "1.5% on UPI that quietly becomes 0%" — cashback floors to 0 under ₹67 (252↑) https://www.reddit.com/r/CreditCardsIndia/comments/1pcfiy1
- "Influencers hyped HSBC cards… reality is very different" (132↑) https://www.reddit.com/r/CreditCardsIndia/comments/1sew2dp

## 2. Eligibility and rejections
**2a. Rejections with no reason ("internal policy"), repeated re-applications** — very common (~5,000 posts).
- "6th rejection for Amazon Pay ICICI Card despite 777 CIBIL" (226↑) https://www.reddit.com/r/CreditCardsIndia/comments/1q7ge7s ; approval call then rejection (360↑) https://www.reddit.com/r/CreditCardsIndia/comments/1qus308 ; compensation for erroneous rejection (1124↑) https://www.reddit.com/r/CreditCardsIndia/comments/1p8uds5

**2b. "Pre-approved" offers trigger hard enquiries then reject** — common (~1,160 posts; CIBIL/enquiry theme in 17.8% of all posts).
- "PSA: HDFC 'You have an offer' → HARD CIBIL enquiry → 'Sorry, no offers available'" (269↑) https://www.reddit.com/r/CreditCardsIndia/comments/1pm7p9d ; wrong enquiry not removed after 5 months https://www.reddit.com/r/CreditCardsIndia/comments/1uly11o

**2c. CIBIL score is opaque: unexplained drops, bank misreporting, no clear dispute path** — very common.
- https://www.reddit.com/r/CreditCardsIndia/comments/1w4js7g (148↑) ; SBI Card misreporting PSA (336↑, 375 comments) https://www.reddit.com/r/CreditCardsIndia/comments/1uu3lhd ; 1-day late EMI → 680 (285↑) https://www.reddit.com/r/CreditCardsIndia/comments/1pr90pv

**2d. Self-employed / students / new joiners / "no salary account" can't get cards** — common (~2,800 posts; FD-backed 1,600).
- https://www.reddit.com/r/CreditCardsIndia/comments/1ud6jak (313↑) ; https://www.reddit.com/r/CreditCardsIndia/comments/1po1dho

**2e. Application stuck / VKYC / pincode not serviceable / agent-only channels** — common (~1,350).
- https://www.reddit.com/r/CreditCardsIndia/comments/1pwudqs (336↑) ; https://www.reddit.com/r/CreditCardsIndia/comments/1uyli33

**2f. Credit limits: arbitrary cuts, "limit increase" that is a decrease, upgrade refused** — common (~2,400).
- "limit revised from 20L to 20K" (743↑) https://www.reddit.com/r/CreditCardsIndia/comments/1uzqggj ; (511↑) https://www.reddit.com/r/CreditCardsIndia/comments/1s34aia ; (398↑) https://www.reddit.com/r/CreditCardsIndia/comments/1qwhxi9

## 3. Tracking rewards, caps, milestones
**3a. Merchant MCC mis-tagging silently kills cashback; found only in the statement; bank blames merchant** — common (~630 MCC posts, ~3,200 exclusion posts; among the most-upvoted complaint types).
- "Closed my SBI Cashback Card today" — Flipkart as "Education", Yatra as "Railways"; RBI Ombudsman to recover ₹4,500 (580↑) https://www.reddit.com/r/CreditCardsIndia/comments/1u4wg9u
- "My ₹4,500 PhD" (495↑) https://www.reddit.com/r/CreditCardsIndia/comments/1p2sw2w — comment: "the SMS about the spend should also contain the mcc code"
- Magnus classified a ₹90,400 phone as Utilities (111↑) https://www.reddit.com/r/CreditCardsIndia/comments/1v1cvkg

**3b. Caps, "once per cycle" rules, rounding and refund-reversal logic are opaque** — common (~1,100 cap posts).
- SBI PhonePe 10% only on first txn per category per cycle — "dark patterns that could make Zepto jealous" https://www.reddit.com/r/CreditCardsIndia/comments/1pye8w9
- HDFC Swiggy cashback reversed on refunds without recomputing cap (493↑) https://www.reddit.com/r/CreditCardsIndia/comments/1qybdiq ; https://www.reddit.com/r/CreditCardsIndia/comments/1s9f1on

**3c. Milestones / welcome benefits / waiver thresholds missed for lack of a tracker** — common (~3,100 milestone posts).
- Missed DCBM welcome benefit by ₹9k; "DCBM doesn't have a spend tracker in the app" https://www.reddit.com/r/CreditCardsIndia/comments/1sw0914 ; https://www.reddit.com/r/CreditCardsIndia/comments/1qx70o2 ; https://www.reddit.com/r/CreditCardsIndia/comments/1pxv2cr

**3d. Points/cashback not credited; must audit statements and chase** — occasional in titles but severe.
- https://www.reddit.com/r/CreditCardsIndia/comments/1u1b972 ; IndusInd ₹25,000 + 46,000 Avios after 11 ignored tickets (442↑) https://www.reddit.com/r/CreditCardsIndia/comments/1s668n4

**3e. No good way to track spends across cards** — common. "How are you guys tracking your credit card spends?" (206↑, 157 comments: Money Manager, Google Sheets, manual) https://www.reddit.com/r/CreditCardsIndia/comments/1tnk6sq

## 4. Devaluations and rule changes
**4a. Wave of devaluations; users feel baited** — very common (~3,100 posts, 542 Devaluation-flaired, many of the year's top posts).
- Airtel Axis (800↑, 781 comments) https://www.reddit.com/r/CreditCardsIndia/comments/1rpplp7 ; (613↑) https://www.reddit.com/r/CreditCardsIndia/comments/1rpsctn
- "RIP SBI Cashback credit card" (1031↑) https://www.reddit.com/r/CreditCardsIndia/comments/1rgxk7y
- Infinia ₹18L/yr minimum (666↑) https://www.reddit.com/r/CreditCardsIndia/comments/1rebss6 ; (585↑) https://www.reddit.com/r/CreditCardsIndia/comments/1sl97iv
- "Why so many devaluation from so many banks?" (547↑) https://www.reddit.com/r/CreditCardsIndia/comments/1rh3juy ; HDFC Swiggy discontinued (725↑) https://www.reddit.com/r/CreditCardsIndia/comments/1r1xlj0 ; https://www.reddit.com/r/CreditCardsIndia/comments/1rq4yg9

**4b. Changes communicated badly: website edits without email, T&C PDFs, RM phone threats** — common.
- Infinia Priority Pass confusion; "I don't know who to trust if not them" https://www.reddit.com/r/CreditCardsIndia/comments/1on3zct ; https://www.reddit.com/r/CreditCardsIndia/comments/1pn655l ; https://www.reddit.com/r/CreditCardsIndia/comments/1vyom37

**4c. Transfer partners removed, points' value collapses overnight** — common. https://www.reddit.com/r/CreditCardsIndia/comments/1sa6964 ; https://www.reddit.com/r/CreditCardsIndia/comments/1rhx4et

## 5. Redemption
**5a. "I have lakhs of points and don't know what to do with them"** — very common (~5,300 redemption posts). https://www.reddit.com/r/CreditCardsIndia/comments/1r1bng1 (480↑) ; https://www.reddit.com/r/CreditCardsIndia/comments/1q3nrcq ; https://www.reddit.com/r/CreditCardsIndia/comments/1t3ewwp

**5b. SmartBuy vs Gyftr vs Amazon Pay vs transfer partner math is too hard** — common. Community-built tool, first bug report "This is old reward rate" (210↑) https://www.reddit.com/r/CreditCardsIndia/comments/1vgzeft ; Axis post-partner-removal megathread https://www.reddit.com/r/CreditCardsIndia/comments/1sppmvu

**5c. Redemption friction/fees; support doesn't know its own program; points lost** — occasional-to-common. https://www.reddit.com/r/CreditCardsIndia/comments/1ps3pck ; 50k Amex points lost to "Pay with points" (492↑) https://www.reddit.com/r/CreditCardsIndia/comments/1r0t8xt ; https://www.reddit.com/r/CreditCardsIndia/comments/1rsk5zo ; https://www.reddit.com/r/CreditCardsIndia/comments/1u5i72n

## 6. Fees, waivers, renewals, closures
**6a. "Is it really LTF?" / LTF promised verbally, fee appears later; FYF vs LTF confusion** — very common (~6,700 LTF posts, 800 FYF).
- https://www.reddit.com/r/CreditCardsIndia/comments/1t8x81g ; "SBI AGENT FOOLED ME!" (421↑) https://www.reddit.com/r/CreditCardsIndia/comments/1sex5ds ; https://www.reddit.com/r/CreditCardsIndia/comments/1t1y6qf ; https://www.reddit.com/r/CreditCardsIndia/comments/1qbkhy2

**6b. Annual fee charged despite meeting waiver; rules and timing unclear** — common (~3,400 fee posts).
- SBI charges then reverses next cycle, undocumented (205↑) https://www.reddit.com/r/CreditCardsIndia/comments/1pa93fl ; https://www.reddit.com/r/CreditCardsIndia/comments/1p2co2h ; https://www.reddit.com/r/CreditCardsIndia/comments/1uulga4

**6c. Closure is hard: banks don't close, tiny residual balances, retention harassment, fees on unactivated/closed cards** — very common (~3,500 closure posts; the year's #2 post).
- ₹3.21 lakh compensation from Kotak for not closing (6253↑) https://www.reddit.com/r/CreditCardsIndia/comments/1ssihqu ; ICICI 200+ days unclosed (396↑) https://www.reddit.com/r/CreditCardsIndia/comments/1u5hkef ; "Owe ₹0.27" (259↑) https://www.reddit.com/r/CreditCardsIndia/comments/1rm5zr3 ; ₹59k billed on unactivated card (272↑) https://www.reddit.com/r/CreditCardsIndia/comments/1u82aau ; https://www.reddit.com/r/CreditCardsIndia/comments/1tcc3l8

**6d. Interest / late fee / "no-cost EMI" mechanics misunderstood and punitive** — common (~1,700 EMI, ~940 interest posts).
- ₹24,000 interest on ₹870.96 short payment (415↑) https://www.reddit.com/r/CreditCardsIndia/comments/1p19fjw ; No-cost EMI explainer (572↑) https://www.reddit.com/r/CreditCardsIndia/comments/1voaboa ; https://www.reddit.com/r/CreditCardsIndia/comments/1stxtaa ; https://www.reddit.com/r/CreditCardsIndia/comments/1tkba9v

**6e. Hidden surcharges (fuel, tax gateway, DCC) above the OTP amount** — common (~900). https://www.reddit.com/r/CreditCardsIndia/comments/1ru6te1 (164↑) ; https://www.reddit.com/r/CreditCardsIndia/comments/1u229hv (276↑)

## 7. Offers and discounts
**7a. Offer eligibility unclear: co-branded cards silently excluded** — common (~650). https://www.reddit.com/r/CreditCardsIndia/comments/1vhv3o7 ; https://www.reddit.com/r/CreditCardsIndia/comments/1vwboqy

**7b. "Offer processing fees" / dark patterns claw back the discount** — common. BookMyShow (780↑) https://www.reddit.com/r/CreditCardsIndia/comments/1svytmf ; (300↑) https://www.reddit.com/r/CreditCardsIndia/comments/1olhiw6 ; Swiggy convenience fees (663↑) https://www.reddit.com/r/CreditCardsIndia/comments/1qgedsb

**7c. Offers found by accident / too late** — occasional. https://www.reddit.com/r/CreditCardsIndia/comments/1sb951z (551↑) ; https://www.reddit.com/r/CreditCardsIndia/comments/1ua3lr3

## 8. UPI / RuPay credit cards
**8a. Which RuPay card for UPI, especially small-ticket spends; rewards round to zero** — very common (~6,700 UPI/RuPay posts). https://www.reddit.com/r/CreditCardsIndia/comments/1sr0ymr ; https://www.reddit.com/r/CreditCardsIndia/comments/1rhmujl ; "every day i buy milk which is 27rs… I am lost now." (1pcfiy1)

**8b. Merchants switching off RuPay-credit-on-UPI** — common. (190↑) https://www.reddit.com/r/CreditCardsIndia/comments/1spn88m ; https://www.reddit.com/r/CreditCardsIndia/comments/1oa6o6x ; "End of UPI cards is near." (400↑) https://www.reddit.com/r/CreditCardsIndia/comments/1sil189

**8c. Rewards depend on which UPI app is used (own app vs GPay/Cred)** — common. (1u34yfj, 1sr0ymr)

## 9. Lounge, forex and travel perks
**9a. Lounge eligibility is a black box: spend criteria, specific lounges/POS machines, denied at the desk** — very common (~5,400 lounge posts).
- Works only on a Pine Labs POS https://www.reddit.com/r/CreditCardsIndia/comments/1rj0m57 ; (225↑) https://www.reddit.com/r/CreditCardsIndia/comments/1taflx5 ; Adani lounge devalued (594↑) https://www.reddit.com/r/CreditCardsIndia/comments/1oehd1m ; https://www.reddit.com/r/CreditCardsIndia/comments/1rtbu9z ; hand-maintained lounge list https://www.reddit.com/r/CreditCardsIndia/comments/1q9smha

**9b. Priority Pass vs card swipe confusion; surprise charges months later** — common (~540). (1on3zct)

**9c. Forex: which zero-markup card, DCC trap, markup on INR-billed foreign merchants, bonus points reversed** — common (~2,800). https://www.reddit.com/r/CreditCardsIndia/comments/1vjcdi7 ; HSBC forex rewards reversed (113↑) https://www.reddit.com/r/CreditCardsIndia/comments/1reyoop ; https://www.reddit.com/r/CreditCardsIndia/comments/1nzhzbe

**9d. Amex / Diners acceptance** — occasional (~275) but bitter. (336↑) https://www.reddit.com/r/CreditCardsIndia/comments/1p14lhs ; (258↑) https://www.reddit.com/r/CreditCardsIndia/comments/1o5gs77

## 10. Billing, statements, disputes, customer service
**10a. Customer care can't answer basic questions; only PNO/RBI Ombudsman works** — very common (~4,700 posts; 848 mention the Ombudsman).
- (718↑) https://www.reddit.com/r/CreditCardsIndia/comments/1ryzux9 ; (799↑) https://www.reddit.com/r/CreditCardsIndia/comments/1vy6frj ; "no way you can know rewards or points earned transaction-wise unless you call them" (1sew2dp)

**10b. Bill-payment apps (CRED/CheQ) fail silently or complicate reconciliation** — common (~2,700). (286↑) https://www.reddit.com/r/CreditCardsIndia/comments/1odjpnc ; (489↑) https://www.reddit.com/r/CreditCardsIndia/comments/1nv85jf ; (488↑) https://www.reddit.com/r/CreditCardsIndia/comments/1r8810y

**10c. Chargebacks/disputes refused or mishandled; refunds stuck** — common. (226↑) https://www.reddit.com/r/CreditCardsIndia/comments/1r4hk9l ; https://www.reddit.com/r/CreditCardsIndia/comments/1ssogs3 ; https://www.reddit.com/r/CreditCardsIndia/comments/1oz68hq

**10d. Fraud / unauthorised debits / cards blocked without notice** — common. (977↑) https://www.reddit.com/r/CreditCardsIndia/comments/1ul6cf6 ; https://www.reddit.com/r/CreditCardsIndia/comments/1t81h2d

**10e. Mis-selling by agents/RMs and spam calls** — common. (564↑) https://www.reddit.com/r/CreditCardsIndia/comments/1tqyebc ; "Do not blindly trust HDFC RMs" (521↑) https://www.reddit.com/r/CreditCardsIndia/comments/1pqts9v ; https://www.reddit.com/r/CreditCardsIndia/comments/1tgcozs

**10f. Statement-level surprises: unexplained debits, overdue on closed card** — occasional. (191↑) https://www.reddit.com/r/CreditCardsIndia/comments/1v1gq5f ; https://www.reddit.com/r/CreditCardsIndia/comments/1p66cs4

## 11. Multi-card management
**11a. Users hold 8–19 cards and can't remember which to use where; wrong card at checkout costs real money** — common (~950).
- "Nobody opens a spreadsheet mid-checkout" https://www.reddit.com/r/CreditCardsIndia/comments/1u34yfj ; "From 14 Cards to 3" (337↑) https://www.reddit.com/r/CreditCardsIndia/comments/1urggin ; 19 physical cards (283↑) https://www.reddit.com/r/CreditCardsIndia/comments/1v6bfup ; https://www.reddit.com/r/CreditCardsIndia/comments/1t83lus

**11b. Due dates / statements scattered across banks and inboxes** — common. "14 credit cards across 4 Gmail accounts" (240↑) https://www.reddit.com/r/CreditCardsIndia/comments/1rp6zl0 ; https://www.reddit.com/r/CreditCardsIndia/comments/1viqhez

**11c. Closing cards to simplify is itself scary (CIBIL age, retention games)** — common. https://www.reddit.com/r/CreditCardsIndia/comments/1owq6hm

## 12. Information quality
**12a. Influencer/affiliate bias; hacks that get patched; stale reward rates** — common (~710). (177↑) https://www.reddit.com/r/CreditCardsIndia/comments/1quiiqy ; (552↑) https://www.reddit.com/r/CreditCardsIndia/comments/1pjxu5r ; (1rhx4et)

**12b. Conflicting / outdated info even from the bank; LLMs hallucinate rates** — common. (1on3zct) ; "This is old reward rate" (1vgzeft) ; "I've tried the ChatGPT route — it hallucinated a Swiggy cashback rate for one of my cards that was wrong by 3x." (1u34yfj)

**12c. Community itself is hostile/gatekeeping; many lurk rather than ask** — occasional but high-engagement. https://www.reddit.com/r/CreditCardsIndia/comments/1qlfodr

## Top 10 (post volume × upvote weight)
1. CIBIL opacity and hard-enquiry damage (~18% of posts mention CIBIL/enquiry).
2. "Which card should I get / keep / close" with no way to decide.
3. Devaluations and silent rule changes.
4. Rejections without reasons / eligibility black box.
5. MCC mis-tagging, caps and exclusions eating rewards.
6. LTF / fee-waiver confusion and mis-selling.
7. Closure friction and retention games.
8. Lounge access uncertainty.
9. Points redemption paralysis and shrinking value.
10. Multi-card overload: wrong card at checkout, scattered due dates, missed milestones; distrust of bill-pay apps.

Runners-up: UPI/RuPay small-ticket rounding and acceptance; customer-care incompetence forcing Ombudsman escalation; influencer-skewed and stale information.
