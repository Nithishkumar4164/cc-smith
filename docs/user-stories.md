# cc-smith — User stories

Companion to `docs/prd.md`. Stories are grouped by epic; each has acceptance criteria, a priority (P0 = v1, P1 = v2, P2 = v3) and the PRD / feature references.

Format: **US-xx** · As a *persona*, I want … so that … · AC: Given / When / Then.

---

## Epic 1 — Onboarding, profile and preferences

**US-01 · Create account and consent** (P0 · FR-TR-3)
As a new user, I want to sign up with my phone number and see exactly what data the app will collect, so that I can decide what to share.
- Given I open the app for the first time, when I sign up, then I complete phone OTP (or Google) login and see a consent screen listing each data source (profile, budgets, statements, notifications, location) with separate toggles; only toggled sources are ever read.
- Given I am signed in, when I open Settings → Privacy, then I can view the data map, export my data, and request deletion; deletion completes within 30 days and I receive confirmation.

**US-02 · Enter my credit profile** (P0 · FR-RE-1)
As a user, I want to enter my credit score band, income band, age, employment type and bank relationships, so that eligibility and likelihood are computed for me.
- Given the profile screen, when I enter values, then each field is optional with "unknown" allowed; recommendations show which fields are missing and how they would change the result.
- Given I later update my score band, then likelihood bands on all recommendations recompute immediately.

**US-03 · Add the cards I hold** (P0 · FR-KB-13, FR-RE-12)
As a user, I want to add my existing cards by searching the master list, so that the app knows my stack.
- Given the add-card search, when I type an issuer or card name, then variants are suggested with issuer, network and fee; I pick one and enter open date, statement date, due date, fee date, credit limit, and whether it is LTF (with a prompt to upload the written confirmation).
- Given my card is not in the list, when I choose "card not listed", then I enter issuer and name, the app warns about similar existing variants, creates a custom card marked "rewards can't be assessed yet", and tells me an intake request has been raised.
- Given the card's official page is later found and the card is published into the master list, then I am notified and the card is linked with full assessment available.

**US-04 · Set my spend budget** (P0 · FR-LD-1)
As a user without statements connected, I want to enter my typical monthly spend by category with top merchants, so that recommendations and the picker have a baseline.
- Given the budget screen, when I enter amounts per category, then entries are saved as estimated ledger entries and labelled "estimated" wherever shown.
- Given I later upload a statement for a month, then estimates for that month are replaced by actuals and the label changes.

**US-05 · Set my preferences** (P0 · FR-VAL-3, FR-RE-1)
As a user, I want to state hard constraints and what I value, so that rankings reflect me.
- Given the preferences screen, when I set hard constraints (max annual fee, LTF only, max cards, issuers to avoid, must-have perks), then cards violating them are filtered out of recommendations with the reason shown.
- Given I answer the valuation questions (flights per year, points stance: cash-only / cash+vouchers / transfer optimiser with partners I use, international spend, memberships already paid), then the engine values perks and points at my numbers and shows the assumptions on every ranking.
- Given I pick a preset (cashback-first, travel-first, simplicity-first), then valuations are pre-filled and editable.

---

## Epic 2 — Card glossary

**US-06 · Browse and filter all cards** (P0 · FR-GL-1)
As a user, I want to browse every card in the market with filters, so that I can explore options.
- Given the glossary, when I filter by issuer, network, fee band, LTF availability, reward type, perks, co-brand or UPI capability, then the list updates and shows the count.
- Given I search by name, then matches include variants and co-brand names.

**US-07 · See my status on each card** (P0 · FR-GL-2)
As a user, I want each card tagged as held / pre-qualified / not eligible / blocked by compatibility, so that I know where I stand before reading details.
- Given my profile and held cards, when I view the glossary, then each card shows one tag; "not eligible" and "blocked" tags name the failing rule or blocking card on tap.

**US-08 · Read a card's full detail** (P0 · FR-GL-3/4/5)
As a user, I want a card page with fees, waiver rules, earn rules with caps and exclusions, milestones, perks, redemption routes, eligibility, compatibility restrictions and changelog, so that I understand the card before applying.
- Given a card page, when I tap any value, then I see its source URL, as-of date and who verified it.
- Given I have a spend profile, then the page shows my effective annual value and effective rate after caps, exclusions and rounding, labelled "your numbers".
- Given the page, when I tap "Should I get this?", "Report a correction" or "How to apply", then the respective flow opens.

**US-09 · Report a wrong fact** (P1 · FR-KB-11)
As a user, I want to report an incorrect value with evidence, so that the knowledge base gets fixed.
- Given a field, when I report it with optional statement line / email / screenshot, then a review item is created, I can see its status, and I am notified on resolution with the outcome.

---

## Epic 3 — Recommendation engine

**US-10 · Get a ranked portfolio** (P0 · FR-RE-2)
As a user, I want a ranked set of card portfolios with rupee value per card and line-item breakdown, so that I can see what to acquire.
- Given my spend profile, held cards and preferences, when I open Recommendations, then I see 1–3 portfolios ranked by annual ₹ value; each card shows value by category, milestones, perks (at my valuation), minus fee unless waiver is on track, and marginal gain over my current best card per category.
- Given a pending devaluation on a candidate card, then the value shown is post-devaluation with a note.
- Given a card only duplicates my existing best card, then it ranks low with the reason "duplicates <card>".

**US-11 · See the honest effective rate** (P0 · FR-RE-2, FR-GL-3)
As a cashback-first user, I want to see the effective rate on my spends after caps, minimums and rounding, so that brochure rates do not mislead me.
- Given a card with a per-transaction minimum or rounding rule, when my budget includes small-ticket spends, then the effective rate accounts for transactions earning zero and shows an example.

**US-12 · Know my likelihood of approval** (P0 · FR-RE-5)
As a user, I want each recommended card to show a likelihood band with the factors, so that I do not waste a hard enquiry.
- Given my profile, when a card is shown, then I see High / Medium / Low with contributing factors (score band, income vs minimum, relationship, existing issuer cards, compatibility, enquiries) and the label "estimate".
- Given a known compatibility restriction (e.g. I hold only a co-brand with this issuer), then the card shows "blocked" with the rule and source instead of a likelihood.

**US-13 · Respect issuer card limits** (P0 · FR-RE-3)
As a user with several cards from one issuer, I want recommendations to respect the issuer's maximum cards per customer, so that I am not sent to apply for something I cannot get.
- Given an issuer policy with a source, when I already hold the maximum, then that issuer's cards are marked "issuer limit reached" and excluded from acquire recommendations.

**US-14 · Should I get this card?** (P0 · FR-RE-7)
As a user, I want to ask about a named card, so that I get a yes/no with numbers.
- Given a card, when I ask, then I see annual ₹ value for me, marginal gain over my stack, eligibility, likelihood, compatibility impact and a plain-language verdict.

**US-15 · Keep, convert or close** (P0 · FR-RE-4)
As a user, I want each held card assessed for keep / convert / close, so that I stop paying for cards that do not pay.
- Given 12 months of ledger data (or budget estimates), when I open Portfolio review, then each card shows rewards earned net of fee, what the rest of my stack would earn instead, waiver status, available LTF/downgrade conversion, and credit-profile side effects of closing (utilisation, oldest card).
- Given conversion is available, then "convert" is recommended before "close".

**US-16 · Get a path when I am not eligible** (P0 · FR-RE-10)
As a hard-profile user, I want an action plan when a card is out of reach, so that I can work toward it.
- Given a failed eligibility rule, when I open the card, then I see the failing rule and steps (relationship account, FD-backed first, utilisation under threshold, wait N months after last enquiry), each with a "done" toggle; eligibility re-checks when steps are done.

**US-17 · Learn how others got the card** (P2 · FR-RE-6)
As a user, I want a summary of community acquisition experiences per card, labelled as community reports with source links, so that I apply the way that works.
- Given a card page, when I open "How people get it", then I see routes (pre-approved, card-to-card, FD-backed, relationship), common rejection reasons, typical turnaround, with source links to allow-listed community threads and a last-reviewed date.

**US-18 · Avoid harmful enquiries** (P1 · FR-RE-11)
As a user, I want a warning before applying when my recent enquiries or a known hard-pull channel make rejection likely, so that my score is protected.
- Given my enquiry log shows N enquiries in the last 6 months, when I tap "Apply", then I see a warning with the recommended wait.
- Given a channel known to hard-pull then reject, then the warning names it.

**US-19 · Honest answers for hard categories** (P0 · FR-RE-8)
As a user paying rent, utilities, insurance, fuel, tax or education, I want to know whether anything earns and what the surcharge is, so that I stop expecting rewards that do not exist.
- Given a hard category in my budget, when I view recommendations, then the category shows the best option, its net after surcharge, and whether the spend counts toward milestones and waivers.

**US-20 · Trust the ranking** (P0 · FR-RE-13)
As a user, I want to know rankings are never paid for, so that I can trust them.
- Given the recommendations screen, then a statement says cc-smith takes no affiliate, referral or issuer money, and every rank shows its breakdown.

---

## Epic 4 — Spend tracking and ledger

**US-21 · Upload a statement** (P1 · FR-LD-2)
As a user, I want to upload a statement PDF (with password), so that actual transactions replace my estimates.
- Given a statement, when I upload it, then transactions are parsed with merchant, amount, date, card and reward lines; the PDF is deleted after parsing; unparsed lines are listed for manual correction.
- Given the parsed period, then estimates for that period are replaced and trackers recompute.

**US-22 · Capture transactions automatically on Android** (P1 · FR-LD-3)
As an Android user, I want transaction alerts captured automatically, so that trackers are live without manual work.
- Given I grant notification access with a clear explanation, when a bank alert arrives, then a ledger entry is created within a minute with amount, merchant string, card, and provenance "notification".
- Given iOS, then this option is hidden and statement upload is offered instead.

**US-23 · Correct a merchant's category** (P1 · FR-LD-6, FR-PK-4)
As a user, I want to correct the category/MCC of a transaction, so that my trackers and the merchant map are right.
- Given a ledger entry, when I change its MCC, then my trackers recompute and the observation is added to the merchant map for that issuer.

**US-24 · See spend summaries** (P1 · FR-LD-8)
As a user, I want per-card, per-category and per-FY totals with forex in INR, so that I can see where money goes and answer FY questions.

---

## Epic 5 — Payment method picker

**US-25 · Pick a card by typing the merchant** (P0 · FR-PK-1/5/6)
As a multi-card user, I want to type a merchant and amount and get the best card with a reason, so that I stop guessing at checkout.
- Given held cards and tracker state, when I enter "Croma, 45000", then within 1 s I see ranked cards with ₹ reward now, progress contribution, warnings (excluded, cap exhausted) and a one-paragraph reason, plus the margin over the next best.
- Given no card earns on this payment, then the picker says so and recommends the card closest to a milestone or waiver.

**US-26 · Scan a merchant QR** (P1 · FR-PK-2, FR-PK-13)
As an offline payer, I want to scan the merchant's UPI QR, so that the merchant and MCC are read without typing.
- Given a merchant QR, when I scan, then payee name and (when present) MCC are read; if MCC is absent, the merchant map or category selection fills it; the picker result appears.
- Given Android, when I confirm, then my UPI app opens with the payee prefilled.

**US-27 · Pick from nearby merchants** (P1 · FR-PK-2)
As an offline payer without a QR, I want to see nearby shops and pick the one I am paying, so that the right MCC is used.
- Given location permission, when I open the picker, then nearby merchants are listed, previously used ones first; selecting one resolves the expected MCC; results are cached per place.

**US-28 · Get the pick at checkout (Autofill) or by sharing a link** (P1 · FR-PK-3)
As an online shopper, I want the card pick to appear when a checkout asks for my card, or in one tap by sharing the URL, so that I never leave the merchant's flow.
- Given cc-smith is enabled as the Android autofill service, when a form field is detected as a card-number field, then the autofill dropdown shows the recommended card with its reason, the app package or domain resolves to the merchant, and no card number is stored or filled.
- Given a shared URL, when the app receives it, then the domain resolves to the merchant and the picker opens with amount entry; for marketplaces the marketplace MCC applies.
- Given no match, then I can pick from recent merchants or type the name.
- Given iOS, then share-sheet is the primary path and the Autofill path is not offered.

**US-29 · See the plan-aware ranking** (P0 · FR-PK-6/7)
As a user working toward a milestone or lounge spend lock, I want the picker to weigh my plan against raw reward, so that I can choose deliberately.
- Given an active notice on card C (e.g. ₹8,000 short of the waiver, 12 days left), when I run the picker, then "my plan" ranking raises card C with the notice as reason, while "max reward now" shows the raw best; the ₹ difference between the two is shown.
- Given a spend-and-time lock (e.g. ₹20k this quarter → lounge next quarter) valued in my preferences, then its option value appears as a line item.

**US-30 · Choose the channel** (P1 · FR-PK-8)
As a RuPay credit card holder, I want to know whether to pay by UPI or card, so that I earn the most and avoid rejections.
- Given a merchant with acceptance reports, when I run the picker, then UPI options show per-app rates, small-ticket rounding, and an acceptance warning when reports indicate RuPay credit is switched off.

**US-31 · Avoid forex and DCC traps** (P1 · FR-PK-9)
As a traveller, I want the picker to show the markup and the pay-in-local-currency reminder, so that I do not lose 3–4% silently.

**US-32 · See surcharges before paying** (P1 · FR-PK-10)
As a user paying fuel, rent or tax, I want surcharges shown before I pay, so that the charged amount is not a surprise.

**US-33 · Confirm the payment** (P0 · FR-PK-12)
As a user, I want to confirm I paid with the picked card, so that trackers update immediately.
- Given a picker result, when I tap "Paid with this card", then a ledger entry is created and cap/milestone/waiver positions update; if capture later detects the same transaction, it is de-duplicated.

---

## Epic 6 — Notice board

**US-34 · See fee-waiver gaps in time** (P0 · FR-NB-1/2)
As a user, I want to know when a fee renewal is near and I am short of the waiver spend, so that I can route spend there.
- Given fee date in 45 days and waiver spend short by ₹X, then a notice shows card, ₹X, days left, and a button that opens the picker with that card prioritised.

**US-35 · Milestone deadlines** (P0 · FR-NB-1)
As a user, I want milestone notices with remaining amount and days, so that I do not miss benefits by a few thousand rupees.

**US-36 · Spend-and-time locks** (P1 · FR-NB-1)
As a lounge user, I want notices for "spend ₹X by date to unlock next quarter's lounge", so that I plan spend across quarters.
- Given a card with a quarterly lounge spend criterion using non-calendar quarters, then the notice uses the card's actual period dates.

**US-37 · Expiring points and vouchers** (P1 · FR-NB-1, FR-RD-2)
As a points holder, I want expiry notices 90/60/30 days ahead with the best route, so that points never lapse.

**US-38 · Due dates and short-payment warning** (P0 · FR-NB-1)
As a multi-card user, I want all due dates and amounts in one place with reminders, so that I never pay late or short.
- Given a due date in 3 days, then a reminder shows amount; given I mark a partial payment, then a warning explains interest on the full statement amount.

**US-39 · Devaluation replan** (P1 · FR-NB-4)
As a user, when a held card is devalued, I want a notice with what to move where and the ₹ impact, so that I adjust without reading T&Cs.
- Given a confirmed KB change on a held card, then the notice lists category moves within my stack, net impact, and only suggests a new card if value is still lost.

**US-40 · Missing rewards flagged** (P1 · FR-NB-5)
As a user, I want to be told when a statement's posted rewards are below what the rules say, so that I can claim them.
- Given a reconciled statement, then discrepancies list transaction, expected vs posted, suspected cause (excluded MCC, cap, lag) and a button to draft a complaint.

**US-41 · Pending benefit overdue** (P1 · FR-NB-1)
As a user, I want to know when a milestone voucher or offer cashback is past its expected credit date, so that I chase it.

**US-42 · Keep/convert/close reminder** (P0 · FR-NB-6)
As a user, I want a decision notice ~45 days before renewal with the inputs, so that I act before the fee posts.

**US-43 · Close a card safely** (P1 · FR-NB-7)
As a user closing a card, I want a checklist (zero balance incl. paise, pending reversals, written NOC, account-level closure, credit-report check after 45 days) with reminders, so that closure actually completes.

**US-44 · Escalate with evidence** (P1 · FR-NB-8)
As a user whose rewards were not credited, I want a per-issuer escalation ladder and a drafted complaint built from my ledger evidence, so that I reach the right desk fast.
- Given a discrepancy, when I tap "Escalate", then I see customer care → nodal/PNO → RBI Ombudsman steps with contacts and timelines, a draft with transactions, MCCs and expected vs posted, and a case tracker.

**US-45 · Keep my proof** (P0 · FR-NB-9)
As a user, I want to store LTF confirmations, offer T&C snapshots and chat screenshots per card, so that I have proof in a dispute.

**US-46 · New card worth a look** (P2 · FR-NB-1)
As a user, I want a heads-up only when a new launch beats my stack by a meaningful amount, so that I am not spammed.

---

## Epic 7 — Redemption optimizer

**US-47 · Best route for my balance** (P2 · FR-RD-1/5)
As a points holder, I want routes ranked by net ₹ per point after fees, GST, caps and minimums for my balance, so that I redeem well.
- Given a balance, then each route shows ₹ outcome for the full balance and partials, with fees and caps applied; routes outside my points stance are shown but de-prioritised.

**US-48 · Redeem now or wait** (P2 · FR-RD-3)
As a points holder facing an announced partner devaluation, I want a now-vs-after comparison, so that I decide before the effective date.

**US-49 · Partner changes with my impact** (P2 · FR-RD-4)
As a transfer-partner user, I want alerts on ratio changes or partner removals with the ₹ impact on my stored points.

**US-50 · Cashback vs points, translated** (P0 · FR-VAL-4)
As a user comparing a cashback card with a points card, I want points translated into ₹ at my stance with assumptions shown, so that the comparison is fair.

---

## Epic 8 — Trust and community

**US-51 · See where every fact comes from** (P0 · FR-TR-1)
As a user, I want source and as-of date on every fact, so that I can judge it.

**US-52 · Read a card's changelog** (P1 · FR-KB-12)
As a user, I want the history of changes to a card with dates and sources, so that I can see devaluation patterns.

**US-53 · Report acceptance, lounge denial or MCC** (P2 · FR-TR-2)
As a user, I want to report that a merchant refused RuPay credit on UPI, a lounge denied my card, or a merchant's MCC, so that others benefit at the decision point.
- Given a report, then it is stored pseudonymously, aggregated, and shown in the picker / card page / lounge perk with counts and recency.

**US-54 · Delete my data** (P0 · FR-TR-3)
As a user, I want to delete my account and data, so that I control my information.

---

## Epic 9 — Owner and knowledge base operations

No human approves anything (plan DR-12). Official-source facts publish automatically; everything else is speculation; the owner is alerted.

**US-55 · Get alerted on every knowledge change** (P1 · FR-AD-1, FR-KB-9)
As the owner, I want an alert for every change to the knowledge base with the references used, so that I can see what changed without being a bottleneck.
- Given an official page changes and the quote check passes, then the new version publishes without waiting and I receive an alert with card, field, old → new value, tier, event type and every reference (URL, quoted text, fetch time, evidence id).
- Given a rate, cap or fee moves more than 50%, then the alert is flagged as a large change with the number of users holding the card.
- Given a day of changes, then I receive a daily digest; affected users' trackers and notices have already been recomputed.

**US-56 · New cards join the catalogue automatically** (P1 · FR-KB-8/14, FR-AD-2)
As the owner, I want discovered and user-requested cards added without my approval, so that the master list grows where it matters.
- Given Launch Radar or a custom-card request finds a card with an official page, then it is profiled, published and alerted; linked custom cards are converted and their users notified.
- Given a card has no official page, then it is listed as a speculative launch: not scored, no user notification, until an official page promotes it.

**US-57 · Manage the official-source allow-list** (P1 · FR-AD-3, FR-KB-7)
As the owner, I want to maintain the issuer and co-brand partner domains, with the fields each owns, so that only official text becomes facts.
- Given I edit the allow-list, then the edit is versioned and alerted.

**US-58 · History and rollback** (P1 · FR-AD-4)
As the owner, I want field-level history with automatic and manual rollback, so that a misread official page is undone quickly.
- Given the weekly re-check cannot reproduce a published fact, then it is rolled back automatically and I am alerted.
- Given I choose a previous version, then it is restored, the changelog records the rollback, and affected users are recomputed.

**US-59 · See community-reported changes as speculation** (P1 · FR-KB-10)
As a user, I want forum-reported changes (e.g. a devaluation thread) shown on the card, clearly labelled, so that I hear early without bad data changing my numbers.
- Given a community claim, then the card page shows it labelled "reported, not confirmed by the bank" with its refs, an official re-fetch is triggered, and no ranking or tracker changes.
- Given an official quote later confirms it, then it is promoted to a fact; given an official source contradicts it, it is closed; otherwise it expires after 60 days.

**US-60 · Report a wrong answer** (P1 · FR-KB-11)
As a user, I want to report a wrong rate or rule with evidence, so that it gets checked against the bank's page.
- Given I report a correction, then it becomes speculation with my report as the ref, the official page is re-fetched immediately, and I see the outcome (promoted, contradicted or expired).

---

## Priority summary

| Priority | Stories |
|---|---|
| P0 (v1) | 01–08, 10–16, 19, 20, 25, 29, 33, 34, 35, 38, 42, 45, 50, 51, 54 |
| P1 (v2) | 09, 18, 21–24, 26–28, 30–32, 36, 37, 39–41, 43, 44, 52, 55–60 |
| P2 (v3) | 17, 46–49, 53 |
