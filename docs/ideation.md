# cc-smith — Ideation

An AI agent that suggests credit cards from your category-wise spends, tells you how to use them for maximum benefit, how to acquire them, and delivers relevant news.

## Decisions so far

| Decision | Choice |
|---|---|
| Market | India |
| Audience | Public product (started as a personal-tool idea; see "Building it as a product") |
| Surface | Flutter app, iOS + Android, sole surface — Telegram dropped once the companion app became part of the plan |
| Spend input (v1) | Manual entry, then statement upload |

## Core thesis

Build a deterministic rewards engine over a versioned card knowledge base, with the LLM as the interface and the data-ingestion worker — never as the source of card facts or the calculator. Reward rules change monthly and are full of caps and exclusions, so an agent answering from model memory will be confidently wrong.

## Shape of the system

1. **Card knowledge base** — each card is structured data; every fact carries a source URL and an effective date.
   - Earn rates by merchant / MCC, monthly caps, exclusions (rent, fuel, wallets, utilities, insurance).
   - Milestones, fees and waiver thresholds, point redemption values, eligibility rules.
2. **Deterministic engine** — takes a spend profile, a preference profile and a set of cards, returns a user-specific score: rewards at the user's realistic redemption value, plus milestones and perks valued at the user's own usage, minus fees (see "Preference-driven rankings"). Optimises over combinations of 1–3 cards, because the best portfolio is rarely the top single cards.
3. **Agent** — Claude with tools such as `simulate_rewards`, `optimize_portfolio`, `check_eligibility`, `news_for_cards`. Gathers the spend profile, calls the engine, explains the result with the working shown.
4. **Transaction ledger** — the core data model from day one (see "Payment-time advice and the data loop"). Manually entered category spends are estimated ledger entries; real captured transactions replace them over time, so the engine never needs rewriting.

## The four jobs

| Job | What the agent delivers |
|---|---|
| **Suggest** | Best portfolio for your spends, with rupee value per card and the reason each one earns its slot |
| **Use** | A routing playbook ("Swiggy → card A, flights → card B via the portal"), cap alerts, milestone tracking, redemption advice |
| **Acquire** | Eligibility check, best application path (pre-approved, card-to-card, FD-backed, upgrade, lifetime-free offers), sequencing so applications don't hurt each other |
| **News** | Devaluations, launches and offers filtered to cards you hold or were recommended, translated into impact: "this change costs you ₹4,200 a year; switch dining to card C" |

## Payment-time advice and the data loop

Direct integration with payment apps is not possible, but the outcome is reachable by working on both sides of the payment:

- **UPI apps** (GPay, PhonePe, Paytm, CRED) expose no plugin or API to choose the funding card. Becoming a UPI app requires NPCI approval and a sponsor bank — out of scope.
- **Online card checkouts** run on tokenised cards inside the merchant's gateway, with no hook for us.

### What we build instead

| Moment | Mechanism | Effort |
|---|---|---|
| Offline, before paying | Tell the bot "Croma 45000", or send a photo of the UPI QR. Merchant QRs carry the merchant name and usually a category code, so the bot can answer without typing. | Low |
| Online, before paying | Browser extension that recognises the checkout domain and shows the best card from the stack. | Medium |
| After paying | Automatically capture transaction-alert SMS / emails into the ledger. | Medium |

Open check: how reliably real-world QRs carry a usable category code — small merchants often have a blank or generic one. Needs testing on actual QRs.

### What the bot decides at payment time

The card with the highest **marginal** value for this transaction, not the highest headline rate:

- Merchant / category, amount, channel (card swipe, online, RuPay on UPI — many cards reward UPI differently or not at all).
- Cap state: "card A's 5% cap is exhausted this month, use B".
- Milestone proximity: "₹12,000 more on card C unlocks the fee waiver".
- Live bank offers, e.g. instant discounts during sales.

Cap and milestone awareness only works if the bot knows past transactions — which is why capture matters.

### What the ledger unlocks

- **Missed-rewards report** — "You paid ₹3,400 at Zomato on card X; card Y would have earned ₹170 more."
- **Backtested suggestions** — replay the real last six months against any candidate card: "adding card Z would have earned ₹9,800 more". Far stronger than estimates from category totals.
- **Replacement calls** — "card A earned ₹1,100 net of its fee over 12 months; downgrade or close before the renewal month."
- **Personal merchant map** — the same merchant can post under different categories; your own history is the best source for how each one actually codes.

## Companion app instead of a payment app

Idea raised: build our own payment app with multiple payment integrations, so it suggests the card at pay-time and captures merchant and category data for better suggestions and replacements.

Moving money ourselves is a regulated business: a consumer app that pays merchants needs to be a UPI TPAP (NPCI approval + sponsor bank) for UPI, and a licensed payment aggregator to route card payments. Cards can't be pushed to arbitrary merchants anyway — the merchant's gateway pulls them.

The app doesn't need to move money to deliver the same loop. A thin **Android companion app**:

1. **Owns the scan** — scan the merchant QR in our app → decode merchant name and category → engine picks the card → hand off to the UPI app with payee details prefilled via the UPI deep link. One extra tap versus scanning in GPay directly.
   - To verify: major UPI apps have restricted third-party deep-link flows at times; test on real merchant QRs before committing.
2. **Captures transaction alerts** — on Android via a notification listener on the bank's alert notifications (direct SMS reading is restricted by Play policy for non-default-SMS apps; see "Building it as a product"). The ledger fills itself with amount, merchant and card.
3. **Registers as the `upi://` handler** so any payment link on the phone passes through the recommendation first.

### The app is the only surface

Telegram was originally chosen for speed to v1, but once the companion app is in the plan it would be a second surface with a worse UI for the core screens. Decision: the app is the sole surface.

- Ranked cards with per-line-item breakdowns, valuation adjustments, the routing playbook and the action centre are lists, tables and controls — not chat-shaped.
- Chat with the agent is a screen inside the app, calling the same backend agent.
- Scan → recommend → hand off, SMS capture, and notifications all live in one place.
- Flutter for iOS and Android. Android gets the scanner, UPI hand-off and notification capture; iOS gets manual entry, statement upload and email, since it allows no SMS or notification access.
- The backend stays: agent, engine, knowledge base, and the news / replan jobs run server-side behind an API; the app is a thin client. A future web or browser-extension surface reuses the same API.

## Building it as a product

Decision: this is a public product, not a personal tool. The core architecture (knowledge base + engine + agent + ledger), preference-driven rankings, the companion-app scanner, the action centre and replan all carry over. What changes:

### Data capture under platform rules

- **SMS**: direct `READ_SMS` is restricted by Google Play policy to default SMS handlers and a short list of exceptions. The common approach is a notification listener reading the bank's transaction-alert notifications, with explicit disclosure and consent. iOS allows neither.
- **Email**: Gmail parsing needs Google's restricted-scope review and a security assessment.
- **Account Aggregator**: the clean route for transaction data, but it appears to require being (or partnering with) a regulated entity. Verify before planning around it.
- **Input ladder**: manual entry → statement upload (PDF parsing is universal and policy-free) → notification capture on Android → email → AA later.

### Compliance and trust

- DPDP Act: consent, purpose limitation, deletion on request.
- Never store card numbers — card product and last four digits only. Encryption at rest.
- Every card fact shows its source and "as of" date. Recommendations carry disclaimers.
- A published privacy posture — what is captured, where it goes, how to delete it.

### Knowledge base at scale

The knowledge base is the moat and the liability. Versioned rules with review before publish, user-reported corrections through a reviewer queue, and a public changelog. Card-enthusiast communities (TechnoFino, r/CreditCardsIndia) are both the best source and the first users who will test it.

### Monetisation

Issuer affiliate payouts per approved card are the obvious revenue and the exact thing that makes existing comparison sites untrustworthy. Proposed stance: take affiliate revenue with verifiable ranking independence —

**Decided (owner, 2026-10-06, confirmed 2026-10-07): no affiliate money.** See `docs/decisions.md` A4.

- the engine never sees payouts;
- the per-line-item breakdown is shown for every rank;
- payouts are disclosed on the card.

A premium tier for ledger features (backtests, replan, action centre) is the second line.

### Competition

CRED, SaveSage, Kiwi and the comparison sites overlap. Defensible differences: backtested rupee maths on the user's own transactions, replan-before-recommend, and explainable rankings. Static comparison is not a product.

### Multi-tenant basics

Auth, per-user data isolation, rate limits on the agent, LLM cost control (deterministic engine for all computation; the LLM only for chat and extraction).

### Web recommender

A web flow — paste your spends, get a ranked stack — is worth considering for discovery and SEO, since that result is shareable. Same backend API.

### Open decisions

1. Team and stack — solo or team? Default proposal: Python backend (strongest LLM, PDF-parsing and scraping ecosystem), Flutter client.
2. Monetisation stance — affiliate with verifiable independence (proposed), subscription-only, or decide later.
3. Launch scope — closed beta with card enthusiasts first, or public from day one.

## Per-card action centre and replan-before-recommend

Principle: **when the world changes, first re-route within the stack already held; recommend a new card only for the gap that remains.** Acquisition is the last resort.

### Action centre, per card

- Bill due — date, amount, autopay status
- Milestone nudge — "₹12k to go, 9 days left"
- Cap reset / cap exhausted
- Fee renewal decision — waiver reached? if not, downgrade or close before the renewal month
- Points expiring, offer registrations, welcome-benefit claim deadlines
- **Replan** — triggered by news: devaluation, new category, new exclusion

### Replan flow

1. A rule change lands in the knowledge base (devaluation, new category, exclusion).
2. Engine re-runs the routing playbook against the user's actual ledger.
3. Diff old vs new playbook.
4. Deliver a recap first: "move dining from A to B, stop using C for utilities; net impact ₹X/year".
5. Only if value is still lost after re-routing, suggest a new or replacement card.

## Preference-driven rankings

Card suggestions and rankings are based on the user's preference of perks and rewards, not a single generic "net value" number.

### Engine objective

Each card is scored as the sum of benefit line items, each valued at the user's own usage and weights:

```
score(card) = Σ value_user(line_item) − fees
```

Line items: earn rewards by category, milestones, fee waivers, and every perk below.

### Perks are first-class in the knowledge base

Each perk is typed, with a default cash-equivalent and a flag for whether its value depends on usage:

- Lounge access (domestic / international count, guest allowance)
- Forex markup
- Fuel surcharge waiver
- Memberships bundled (streaming, food delivery, e-commerce)
- Movie / dining offers
- Milestone vouchers
- Insurance covers
- Golf, concierge, airport services
- Welcome benefits — valued in year one only, so steady-state rankings aren't inflated

### Preference profile

Two parts:

1. **Hard constraints** — filter cards out: max annual fee, lifetime-free only, must have zero forex markup, maximum number of cards, issuers to avoid.
2. **Valuations** — weight what remains. The engine values each perk at the user's number, not the brochure's:
   - Lounge: `visits the user would actually make × value per visit`, capped by what the card offers.
   - Points / miles: the user's realistic redemption rate — lower if they won't use transfer partners.
   - Forex waiver: `user's international spend × markup`.
   - Memberships: full value only if the user would otherwise pay for them.

### Elicitation

Behaviour questions, not abstract sliders — each answer maps to a valuation. Roughly eight questions in the app's onboarding:

- Flights per year (domestic / international)?
- Redeem points via airline / hotel transfers, or statement credit only?
- International spend per year?
- Which memberships do you already pay for?
- Fee tolerance? Lifetime-free only?
- How many cards are you willing to manage?

Presets (cashback-first, travel-first, simplicity-first) give a starting point without the questionnaire.

### Learned from the ledger

Valuations are corrected by observed behaviour: a lounge card never used at lounges drops the lounge valuation to zero; unredeemed points discount the redemption value. This keeps replacement calls honest.

### Explainable output

Rankings show the per-line-item breakdown so the user can see why card B beat card A, and adjust a valuation if it's wrong. Changing a valuation re-ranks instantly.

## Where the difficulty is

- **Keeping the knowledge base correct** is the hardest part. Pipeline: scrape issuer terms pages and community sources → LLM extracts into the schema → diff against current rules → review queue before changes go live.
- **Spend granularity** — rewards key on merchant and MCC, not on "shopping". Input grows from manual category entry → statement upload → transaction-alert parsing / Account Aggregator.
- **Trust** — existing players are mostly static comparison tables or affiliate-biased. Personalised maths with citations is the differentiator; affiliate monetisation would undercut it unless ranking is provably independent.

## Roadmap

1. Card knowledge base (~30 hand-verified cards), engine, backend API. Flutter app with three screens: onboarding (preferences + manual spends), rankings with breakdowns, chat with the agent (including "which card?").
2. Statement upload; multi-tenant auth and data isolation; knowledge-base review pipeline with user-reported corrections. Closed beta.
3. App v2: QR scan → recommend → hand off to UPI app (Android); notification capture into the ledger (Android). Cap and milestone tracking, missed-rewards report, per-card action centre.
4. Backtested suggestions, news digest with impact in rupees, replan flow.
5. Web recommender, browser extension for online checkouts, email capture, Account Aggregator if viable.

## Open questions

1. Team and stack, monetisation stance, launch scope — see "Building it as a product".
2. Which ~30 cards seed the knowledge base? Start with the cards the team holds (real test cases), then the most-discussed cards in the enthusiast communities.
