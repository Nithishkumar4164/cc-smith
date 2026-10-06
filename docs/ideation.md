# cc-smith — Ideation

An AI agent that suggests credit cards from your category-wise spends, tells you how to use them for maximum benefit, how to acquire them, and delivers relevant news.

## Decisions so far

| Decision | Choice |
|---|---|
| Market | India |
| Audience | Personal tool first |
| Surface | Telegram bot |
| Spend input (v1) | Manual entry |

## Core thesis

Build a deterministic rewards engine over a versioned card knowledge base, with the LLM as the interface and the data-ingestion worker — never as the source of card facts or the calculator. Reward rules change monthly and are full of caps and exclusions, so an agent answering from model memory will be confidently wrong.

## Shape of the system

1. **Card knowledge base** — each card is structured data; every fact carries a source URL and an effective date.
   - Earn rates by merchant / MCC, monthly caps, exclusions (rent, fuel, wallets, utilities, insurance).
   - Milestones, fees and waiver thresholds, point redemption values, eligibility rules.
2. **Deterministic engine** — takes a spend profile and a set of cards, returns net annual value: rewards at realistic redemption value, plus milestones, minus fees. Optimises over combinations of 1–3 cards, because the best portfolio is rarely the top single cards.
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

## Where the difficulty is

- **Keeping the knowledge base correct** is the hardest part. Pipeline: scrape issuer terms pages and community sources → LLM extracts into the schema → diff against current rules → review queue before changes go live.
- **Spend granularity** — rewards key on merchant and MCC, not on "shopping". Input grows from manual category entry → statement upload → transaction-alert parsing / Account Aggregator.
- **Trust** — existing players are mostly static comparison tables or affiliate-biased. Personalised maths with citations is the differentiator; affiliate monetisation would undercut it unless ranking is provably independent.

## Roadmap

1. Card knowledge base (~30 hand-verified cards), engine, Telegram bot with portfolio suggestions and a "which card?" command. Manual spend entry.
2. Transaction capture (SMS / email), cap and milestone tracking, missed-rewards report.
3. Backtested suggestions and the news digest with impact in rupees.
4. Browser extension for online checkouts.

## Open questions

1. Android or iPhone? Android allows reliable SMS forwarding to the bot; iPhone leans on email alerts or Shortcuts automations, which are more limited.
2. Which cards are held today? They become the first knowledge-base entries and the engine's test cases.
