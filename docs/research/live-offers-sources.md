# Live card-offer sources for cc-smith

Research note, 2026-10-07. Question: where are "pay with card X at merchant Y this week" offers published, in what form, how stable are the sources, and can we extract them on a schedule?

Method: every URL below was fetched on 2026-10-07 from a sandbox with curl (desktop Chrome UA, `--compressed`) and/or Claude's WebFetch, plus web search. "Render" describes what the raw HTML contains without executing JS. One fetch each; counts are what that one response contained. Wayback checks hit a 429 rate limit part-way, so Wayback coverage is only reported where a CDX query succeeded. Nothing here was checked in a real browser.

Related: `docs/research/official-domains.yaml` (issuer allow-list). Offer portals live on the same `.bank.in` canonical hosts (all legacy `.com` offer URLs 301'd to `.bank.in`), except SBI Card (`sbicard.com`) and Amex.

---

## (a) Summary table

Feasibility = how hard a scheduled extractor is, given render type, structure, blocking and ToS. "no" = do not build against it.

| # | Source | Type | URL (verified 2026-10-07) | Render | Structured? | Fields present | Access / ToS | Feasibility | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| 1 | SBI Card offers | issuer | https://www.sbicard.com/en/personal/offers.page | HTML page with an inline JSON array of offer objects (95 objects in one fetch) | **yes** | offerId, card (comma list of card slugs), category, brand, brandName, discountBlock, text, isOnline, pinCode, city, startDate, endDate, priority, dcrPath, type | 200 to curl; robots `Allow: /*`; tnc.page has no anti-scraping clause found | **easy** | curl + python parse |
| 2 | Axis Grab Deals | issuer | https://grabdeals.axis.bank.in/ (Angular SPA) backed by `https://grabdealsapi.vernost.in` | SPA shell; data from a vendor JSON API | **yes** (API) | `/partnerList` returned JSON: PARTNER_NAME, RIBBON_TEXT, JPMILE_DESC ("Flat 8% cashback or 5X EDGE REWARD Points"), PARTNER_LANDING_URL (affiliate link), STATUS. Other endpoints named in main.js: allOffer, offerDetails, categoryList, getCountdown, getBanners | `/partnerList` 200 to curl GET with an Origin header; no robots.txt (returns the SPA HTML); third-party vendor host, no published API terms | **medium** (API is undocumented and vendor-owned; may change or get locked) | curl of main.js and /partnerList |
| 3 | Kotak offers | issuer | https://www.kotak.bank.in/en/offers.html | AEM; the listing grid is a Handlebars template filled by AJAX, but the first page's 22 cards are also present as text; `data-resultcount="57"` | semi | template fields: merchantName, description, endDate ("Offer ends: 27 March 2027"), uniqueId, offerIdLink, thumbnailImage, offerViewCount, offerRatings; min txn / max discount / card names appear inside `description` free text; T&C PDFs on images.kotak.com | 200; robots allows `*`, GPTBot and ClaudeBot (`Allow: /`); terms page anti-mining clauses are scoped to Digital Rupee wallet, not the website | **medium** (parse HTML, or find the AJAX URL in the clientlib) | curl; `articlelistingfilter.json` returned component config, not the list |
| 4 | HDFC offers (bank site) | issuer | https://www.hdfc.bank.in/ps/offers (+ /ps/offers/<category>) | Next.js App Router (RSC payload, `__next_f.push` x55); featured offers are in the HTML | semi | merchant, headline discount, "Valid till: 30 Nov 2026", eligible-card note ("All Credit/Debit except co-branded"), 10 categories with subcategories, per-offer URL `/ps/offers/<slug>-<id>`; detail page links T&C to SmartBuy `offer_details/<id>` | 200 to curl; page claims "up to 10,000 offers year-round" (unverified) | **medium** | WebFetch + curl |
| 5 | HDFC SmartBuy | issuer (operated by Reward360) | https://offers.smartbuy.hdfc.bank.in/ (301 → /v2/foryou); old host offers.smartbuy.hdfcbank.com no longer resolves | Next.js; home/justforyou are mostly a shell ("Loading..."); `/offer_details/26850` returned HTTP 500 | unknown | n/a in one fetch | Reward360 T&C (https://offers.reward360.in/terms_conditions) forbids "Aggregate or scrape any content, data or other information from the Website" | **no** (ToS) — use the bank's /ps/offers instead | curl; Wayback CDX: 34 snapshots of old host since 2025, last 2026-03-06 (301) |
| 6 | ICICI offers | issuer | https://www.icici.bank.in/offers | AEM; filter UI + 8 "handpicked coupons" in HTML; main grid appears JS-filled (`offer-cards-section hide`) | semi | merchant, headline, coupon code (FLYMON, ICICILUXWEEKEND, ICICIWEEKEND), payment-mode ("Avail on Credit Card"), categories (Travel/Lifestyle/Electronics/Food/Grocery/Entertainment/Special), sort "Expiring Soon"; per-offer pages exist e.g. /offers/amazon-super-value-day-offer (from search) | 200; robots only blocks `Enterprise_Search` from `/`; site has no sitemap | **medium** (headless needed for the full grid; coupons + per-offer pages are static) | curl |
| 7 | HSBC India offers | issuer | https://www.hsbc.bank.in/credit-cards/offers/ | server-rendered AEM, ~23 offers | semi | merchant, headline, "Offer valid until 31 October 2026", T&C PDF link per offer (/content/dam/hsbc/in/documents/offers/*.pdf), grouped by category | 200; robots disallows only non-IN promo folders | **medium** (regular HTML) | curl; Wayback CDX 95 snapshots of legacy URL since 2025 |
| 8 | RBL offers | issuer | https://www.rbl.bank.in/offers | server-rendered, "We found 12 offers" | semi | category, title, "Expires on December 31, 2026", Read More link; per-merchant pages exist (/offers-and-promotions/amazon on legacy host, from search) | 200; robots `User-agent: *` with no relevant disallow | **medium** (small catalogue) | curl |
| 9 | Amex India offers | issuer | https://www.americanexpress.com/en-in/benefits/amex-offers/offers/ (via go.amex short link) | server-rendered hub; offers only after picking a card; per-offer pages like /en-in/benefits/amex-offers/dining/cha.html | semi | hub shows card list + programmes (Hotel Edit, EMI, RewardXcelerator); per-offer pages (from search) carry discount, min purchase, promo code (e.g. AMEX20) | 200; robots `User-agent: *` only | **medium** (crawl per-offer pages) | WebFetch + search |
| 10 | IDFC FIRST offers | issuer | https://www.idfcfirst.bank.in/offers | 2 MB HTML (`ng-app`) but no offer text in the HTML | no | — | 200 | **hard** (headless) | curl |
| 11 | YES Bank offers | issuer | https://www.yes.bank.in/personal-banking/yes-individual/yes-privileges/yes-privileges-offers | Oracle Content JS shell ("This site requires JavaScript") | no | — | 200 | **hard** (headless) | curl |
| 12 | Standard Chartered | issuer | https://www.sc.bank.in/promotions/ | server-rendered but the listing had 0 promotion links in HTML | no | — | 200; per-offer T&C pages exist (/in/terms-and-conditions/amazonemifeb-offers-tnc, from search) | **hard** | curl |
| 13 | AU SFB | issuer | https://www.au.bank.in/offers | 403 (Cloudflare) | — | — | blocked to curl and WebFetch | **no** | curl |
| 14 | Federal Bank | issuer | https://www.federalbank.co.in/offers | Radware "Verifying your browser" page | — | — | blocked | **no** | curl |
| 15 | IndusInd | issuer | guessed URL 301'd to /in/en/500.html | — | — | — | URL unknown | **unverified** | curl |
| 16 | Cleartrip offers | merchant | https://www.cleartrip.com/all-offers/ | server-rendered, ~134 offer cards | semi | title ("Flat 10% off on SBI Cards"), applicability ("Applicable on Credit Cards"), promo code (SBICC, NOVCC), per-offer URL (/all-offers/bus-sbicc/), `data-start-time`/`data-end-time` attributes (values seen were stale, 2024) | 200; robots disallows /promotions/ and /promos/ only; terms-of-use had no scraping clause in the text matched | **easy** | curl |
| 17 | Amazon.in bank offers | merchant | no stable public page found; help page nodeId=GZ6XA4Y3GNZ7SPRZ returned 200 with no bank text; /events/greatindianfestival 200 with 0 bank-offer strings | JS/personalised | no | — | robots `Disallow: /` for `*` and ClaudeBot; Conditions of Use: "you may not utilise any data mining, robots, or similar data gathering and extraction tools" | **no** (ToS + robots) | curl |
| 18 | Flipkart | merchant | https://www.flipkart.com/offer-store (React, `__INITIAL_STATE__`), 0 bank strings; https://stories.flipkart.com/ 200 (press) | SPA | no | — | Terms: "You shall not use any deep-link, page-scrape, robot, spider or other automatic device" | **no** (ToS); BBD bank partners are announced on stories.flipkart.com / press | curl |
| 19 | Swiggy / Zomato | merchant | swiggy.com/offers 404; zomato.com/offers resolves to a user profile | — | no | — | offers are in-app at checkout | **no** public source | curl |
| 20 | BookMyShow | merchant | in.bookmyshow.com/offers and /explore/offers → Cloudflare 403 | blocked | — | — | blocked | **no** | curl |
| 21 | MakeMyTrip | merchant | https://www.makemytrip.com/promos/ — curl 000, WebFetch timeout | unreachable from sandbox | — | — | — | **unverified** | curl/WebFetch |
| 22 | EaseMyTrip | merchant | /offers/ 403; /offers/bank-offers.html 404 | blocked | — | — | — | **no** | curl |
| 23 | Myntra | merchant | https://www.myntra.com/offers 200, SPA (`__myx`), 0 bank strings | SPA | no | — | — | **hard** | curl |
| 24 | Ajio, Croma, Nykaa | merchant | /offers → Akamai "Access Denied" 403 | blocked | — | — | — | **no** | curl |
| 25 | Tata Neu | merchant | https://www.tataneu.com/offers 200 but 71 chars of text (JS shell) | SPA | no | — | — | **hard** | curl |
| 26 | BigBasket / Blinkit / Uber | merchant | bigbasket /offers/ 302→404; blinkit /offers 403 "you have been blocked"; uber /ride/offers/ 406 | blocked / none | — | — | — | **no** | curl |
| 27 | GrabOn bank offers | aggregator | https://www.grabon.in/bank-offers/ | server-rendered, ld+json | semi | per-bank counts ("HDFC Card 41 Coupons 78 Offers", "SBI Card 15 Coupons 50 Offers"), "Verified On: 07 Oct 2026"; per-bank page URL pattern not found (/hdfc-bank-coupons/ 404) | robots allows most; T&C page URL not found | **medium** | curl |
| 28 | CouponDunia bank offers | aggregator | https://www.coupondunia.in/bank-offers | server-rendered, ld+json | semi | bank list (HSBC, Axis, ICICI, DBS, SC), wallet list, store counts; per-bank page pattern not found (/hdfc-bank 404) | robots disallows /redirect-offer/, /load-offer*, /*?offer*; GPTBot section present; T&C URL not found | **medium** | curl |
| 29 | DesiDime | aggregator/community | https://www.desidime.com/groups/bank (200, server-rendered, 13 kB text); /credit-card-offers 404 | server-rendered + ld+json | semi | deal titles with bank/merchant in text (e.g. "amazon-gif-bank-offers-10-instant-discount-up-to-33-000-with-sbi-credit-card-credit-emi"), community votes | robots `Allow: /` with specific disallows (/search_result/, /users*, /goto/); site is in the project denylist for *facts* | **medium** (as a signal feed, not a fact source) | curl |
| 30 | TechnoFino offers forum | aggregator/community | https://www.technofino.in/community/forums/offers.15/ | Cloudflare challenge ("Just a moment...") 403 to curl and WebFetch | — | — | blocked; Wayback CDX query for it hit "Temporarily Offline" | **no** (direct); Wayback **unverified** | curl/WebFetch |
| 31 | r/CreditCardsIndia via Arctic Shift | aggregator/community | https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=CreditCardsIndia&limit=5 | JSON | **yes** | full Reddit post objects: title, selftext, created_utc, link_flair_text (e.g. "Card & Merchant Offers"), url, author | 2 of 3 calls returned 422 `{"error":"Timeout. Maybe slow down a bit"}`; README calls the API "(limited)"; no written ToS found; /api-docs 404 | **medium** (rate-limited; flair filter `Card & Merchant Offers` is useful) | curl |
| 32 | Dealsrank | aggregator | dealsrank.com — DNS resolves but connection timed out; .in variants also 000 | unreachable | — | — | — | **unverified** | curl/WebFetch |
| 33 | CashKaro, Paisabazaar | aggregator | cashkaro.com/bank-offers 404, /credit-card-offers 404; paisabazaar.com/credit-card/offers/ 404, /credit-card-offers/ 404 | — | — | — | — | **unverified** (URLs not found) | curl |
| 34 | Visa India offers | network | https://www.visa.co.in/en_in/visa-offers-and-perks/ | 992-byte Angular shell (`portal-ui`), no content | no | per-offer pages exist (/visa-offers-and-perks/arrow/156494, from search) | 200; no developer programme seen | **hard** | curl/WebFetch |
| 35 | Mastercard India | network | https://www.mastercard.co.in/en-in/personal/offers-and-promotions.html | Akamai 403 to curl and WebFetch | — | — | blocked | **no** | curl/WebFetch |
| 36 | RuPay | network | https://www.rupay.co.in/offers | 403 to curl; WebFetch got only the page title | — | — | blocked | **no** | curl/WebFetch |
| 37 | Diners Club India | network | dinersclubindia.com does not resolve; Diners in India is HDFC-issued, offers surface on HDFC pages | — | — | — | — | **n/a** | curl |
| 38 | GPay / PhonePe / Paytm | wallet | pay.google.com/intl/en_in/about/offers/ 404; phonepe.com/offers/ 404; paytm.com/offer 200 but stale content (an "iPhone 12" contest) | — | no | — | offers are in-app | **no** | curl |
| 39 | Telegram channels | community | not verified; search found no specific channel; DesiDime links "Handpicked Deals on Telegram" | — | — | — | Telegram ToS; needs a bot/API | **unverified** (existence only) | search |

---

## (b) Per-category findings

### 1. Issuer offer portals

**Best structured: SBI Card.** `offers.page` embeds a JSON array (95 objects on 2026-10-07) with `startDate`/`endDate` (range seen: 2026-10-07 to 2029-09-30), `discountBlock` ("Up to ₹9000 Instant Discount"), `brandName`, `category`, `isOnline`, `pinCode`/`city` for in-store, and `card` as a comma-separated list of card slugs (eligibility). What it lacks: min transaction, max discount as numbers, promo code and T&C link; those are on the detail page. The detail route is `/en/personal/offers/offer-detail.page` (JS reads a param; `?offerId=` returned the shell only) and the `dcrPath` data file 404s when fetched directly, so detail fields need a headless browser. Wayback: 17 snapshots of offers.page in 2026, last 2026-09-15 (200), so the page is also diffable historically. Verified fetches: two in one day (new offers dated 2026-10-02 and 2026-10-07 were present), which suggests weekly or better updates.

**Axis Grab Deals** is an Angular SPA whose data comes from a third-party vendor API `https://grabdealsapi.vernost.in` (Vernost). `GET /partnerList` returned 32 kB JSON without auth (fields: PARTNER_NAME, RIBBON_TEXT e.g. "8% CB OR 5X RP", JPMILE_DESC, PARTNER_LANDING_URL = admitad affiliate link, STATUS). main.js names `allOffer`, `offerDetails`, `categoryList`, `getCountdown`, `getBanners` etc. (method/payload not tested). Grab Deals is an affiliate-cashback programme (shop via portal), not "pay with Axis at merchant" instant discounts; those appear on merchant pages. Being vendor-hosted, the API can change without notice and has no published terms.

**Kotak** lists 57 offers (`data-resultcount`) in an AEM "articlelistingfilter" component; 22 are in the HTML, the rest via AJAX. Each card has merchantName, description, endDate, a detail URL `/content/kotakcl/en/offers/offer-details/<uniqueId>/<slug>.html`. Min txn and max discount are only in the free-text description ("12.5% instant discount | Minimum transaction ₹3,000 | Maximum discount ₹1,000 on select Kotak Bank Credit Cards at Tata CLiQ"). Network-level deal PDFs exist (`/content/dam/Kotak/deals-offers/others/{visa,rupay,emi}-deals.pdf`). robots.txt explicitly allows GPTBot and ClaudeBot.

**HDFC** has two surfaces. `www.hdfc.bank.in/ps/offers` (Next.js, 10 categories, offers with "Valid till" and eligible-card text, per-offer slugs with numeric ids) is the bank-owned page and is server-rendered enough to parse. SmartBuy moved to `offers.smartbuy.hdfc.bank.in` (old host no longer resolves; 34 Wayback snapshots since 2025, last a 301 in March 2026). SmartBuy is operated by Reward360 (support@smartbuyoffers.co) and its T&C prohibits aggregating or scraping, so treat SmartBuy as T&C-link-only.

**ICICI** `/offers` is AEM with a filter UI (payment mode, 7 categories, "Expiring Soon" sort). Eight coupon tiles with codes are in the HTML; the main offer grid is hidden until JS runs. Per-offer pages such as `/offers/amazon-super-value-day-offer` exist (search result) and are plain pages. No sitemap, so discovering offer URLs needs the listing.

**HSBC** and **RBL** are plain server-rendered lists (23 and 12 offers) with validity text and (HSBC) a T&C PDF per offer. **Amex** is a hub with per-offer HTML pages under `/en-in/benefits/amex-offers/<category>/<slug>.html`. **IDFC FIRST**, **YES**, **SC** render nothing useful without JS. **AU** (Cloudflare) and **Federal** (Radware) block non-browser clients. **IndusInd** offers URL was not found.

### 2. Merchant-side bank-offer pages

Only **Cleartrip** publishes a stable, server-rendered offers list (`/all-offers/`, ~134 cards, each with title, "Applicable on Credit Cards", promo code, per-offer page and start/end data attributes). Everything else is either an SPA with offers injected per-user (Flipkart, Myntra, Tata Neu, Amazon), anti-bot blocked (BookMyShow, Ajio, Croma, Nykaa, Blinkit, EaseMyTrip), or in-app only (Swiggy, Zomato, Uber, BigBasket). Amazon and Flipkart terms expressly forbid automated extraction, and Amazon's robots.txt disallows everything to `*` and to ClaudeBot. Flipkart's bank partners for sale events are announced on `stories.flipkart.com` (200, press site), which is a legitimate text source for "BBD: 10% off Axis" claims. Merchant pages are therefore a verification target (open the link), not an extraction source.

### 3. Aggregators and communities

- **GrabOn** (`/bank-offers/`) and **CouponDunia** (`/bank-offers`) are server-rendered with ld+json and per-bank counts, but per-bank page URLs were not discoverable in one pass and their T&C pages were 404 at the guessed URLs. Affiliate sites: offer text is marketing copy, validity is often missing or stale; no provenance to the issuer T&C.
- **DesiDime** `groups/bank` is server-rendered and crawlable under robots (specific disallows only). Deal titles are informative ("Amazon GIF bank offers: 10% instant discount up to 33,000 with SBI credit card / credit EMI"). Community-sourced, so speculation-tier per `official-domains.yaml`.
- **TechnoFino** is behind a Cloudflare challenge; Wayback could not be queried (archive returned "Temporarily Offline"/429 during this run). Unusable for scheduled extraction.
- **Arctic Shift** (Reddit archive) works and returns full post JSON including `link_flair_text`; r/CreditCardsIndia uses the flair "Card & Merchant Offers", which is an ideal filter. The API is rate-limited (422 "Timeout. Maybe slow down a bit" on 2 of 3 calls) and described as "limited" by its author; no ToS page. Posts are screenshots half the time (`i.redd.it` URLs), so the text often says only "Will this offer work on Gift Voucher Purchase?".
- **Dealsrank** was unreachable from the sandbox (DNS resolves, connection times out). **CashKaro** and **Paisabazaar** bank-offer pages were not found at any guessed URL.
- **Telegram**: existence not verified in this pass. DesiDime advertises its own "Handpicked Deals on Telegram" channel.

### 4. Official / semi-official network and wallet offers

- **Visa India**: `/visa-offers-and-perks/` is an Angular shell (992 bytes). Per-offer pages exist (`/visa-offers-and-perks/arrow/<id>`). No public developer API for consumer offers was found; Visa's offer platform is B2B (issuers/merchants), not open to third parties.
- **Mastercard India**: offers page is Akamai-blocked (403) to both tools. Priceless India exists only as press.
- **RuPay** (`rupay.co.in/offers`): 403 to curl; WebFetch saw only a title. NPCI publishes offer circulars as PDFs under `npci.org.in` (not enumerated here).
- **Diners Club**: no India site; Diners is issued by HDFC in India and its offers appear on HDFC pages.
- **GPay / PhonePe / Paytm**: no public offer page found (404s); Paytm `/offer` is a stale SEO page. Offers are shown in-app.

Conclusion: no network or wallet offers a third-party-accessible feed. Only issuer portals and a handful of merchants publish anything a server can read.

### 5. ToS / robots.txt for the top sources

| Source | robots.txt (relevant lines) | Terms text found | Verdict |
|---|---|---|---|
| sbicard.com | `User-agent: *` `Allow: /*` `Disallow: /en/webform/*`, sitemap listed | /en/tnc.page: no scraping/robot/automated-access clause matched | crawlable |
| kotak.bank.in | `User-agent: *` allowed; `GPTBot: Allow: /`; `ClaudeBot: Allow: /` | /en/terms-conditions.html: anti-data-mining clauses are scoped to the Digital Rupee wallet/app | crawlable |
| icici.bank.in | only `Enterprise_Search` is `Disallow: /`; a few NRI promo paths disallowed | terms page URL not found (404 at two guesses) | crawlable (terms unverified) |
| hsbc.bank.in | disallows only other countries' `/content/dam/hsbc/<cc>/promos*` | terms URL 404 at guess | crawlable (terms unverified) |
| hdfc.bank.in | not checked line-by-line; /terms-and-conditions has no website-scraping clause (its "automated processing" text is about customer data) | SmartBuy (reward360.in): "Aggregate or scrape any content, data or other information from the Website" is prohibited | bank page OK; SmartBuy no |
| grabdeals.axis.bank.in | no robots.txt (SPA served) | vendor API has no terms | grey |
| amazon.in | `User-agent: *` `Disallow: /`; `ClaudeBot: Disallow: /`; `GPTBot`, `CCBot` disallowed | Conditions of Use prohibit "data mining, robots, or similar data gathering and extraction tools" | do not scrape |
| flipkart.com | query-parameter disallows only | Terms prohibit "deep-link, page-scrape, robot, spider or other automatic device" | do not scrape |
| cleartrip.com | `Disallow: /promotions/`, `/promos/`, `/sem-flights-offer-lp` (not /all-offers/) | /terms-of-use: no scraping clause matched | crawlable |
| coupondunia.in | disallows `/redirect-offer/`, `/load-offer*`, `/*?offer*`; has a GPTBot section | terms URL 404 at guess | listing crawlable, redirects not |
| desidime.com | `Allow: /` with specific disallows (/goto/, /search_result/*, /users*, vote/reply paths) | not checked | crawlable |

---

## (c) Recommended v1 approach

**Manual curation with scheduled fetch-and-diff assistance, not autonomous extraction.** Reasoning:

1. The only sources that are both structured and permitted are SBI Card's inline JSON, Axis's vendor API (grey), Kotak/HSBC/RBL/HDFC HTML, and Cleartrip. Together that covers 5 issuers out of 14 and 1 merchant out of 16. Merchants that drive most "this week" offers (Amazon, Flipkart, Swiggy, Zomato, BookMyShow, Myntra) either forbid automation or render nothing server-side. A fully automated pipeline would silently miss the offers users care about most.
2. Even on the good issuer pages, the fields the recommender needs for maths (min transaction, max discount, per-card eligibility, exclusions like "not on co-branded cards") live in free text or in T&C PDFs. Extraction would produce a headline and a date, not a computable rule.
3. The `.bank.in` migration just happened (all legacy offer URLs 301'd; SmartBuy changed host; Kotak's Wayback trail stops at Oct 2025 on the old host). Portals are in flux; scrapers written today will break.
4. Scope matches the product: at payment time the user is at one merchant. A curated table of ~50-150 live offers across the top 20 merchants is small enough to maintain by hand if the tooling points a curator at changes.

Concrete v1:

- **Watchers (scheduled, read-only, robots-respecting):** daily fetch of SBI `offers.page` JSON (diff on offerId/endDate), Kotak `/en/offers.html` (diff card list), HSBC and RBL offer pages, HDFC `/ps/offers` per category, ICICI `/offers` coupon block, Cleartrip `/all-offers/`, Axis `partnerList` (and `allOffer` once its method is confirmed). Emit "new / expired / changed" events to a curator queue. These seven are "easy/medium" above and ToS-clean.
- **Signal feeds (hourly, not facts):** Arctic Shift search on r/CreditCardsIndia with flair `Card & Merchant Offers`, throttled to one call per few minutes; DesiDime `groups/bank`. A new post about "Amazon 10% HDFC" prompts the curator to find the issuer or merchant page and record it with a canonical link.
- **Curator writes the `offer` record** (schema below) with `source_url` on an allowed host and `confidence` per the provenance rules in `official-domains.yaml`: issuer/merchant page = official; aggregator/community = speculation (shown with a "reported" label, never used in the rewards maths unless `min_txn`/`max_discount` were copied from an official T&C).
- **Expiry is automatic:** `valid_to` drives removal; records without `valid_to` expire 14 days after `last_verified_at` unless re-verified.
- Revisit full automation once headless-browser extraction for IDFC/YES/SC/Visa is justified by usage, and only for hosts whose terms allow it.

---

## (d) Proposed `offer` record (JSON Schema draft + example)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://cc-smith/schemas/offer.json",
  "title": "offer",
  "type": "object",
  "required": ["id", "merchant", "issuer", "benefit", "valid_to", "source", "status", "last_verified_at"],
  "properties": {
    "id": {"type": "string", "description": "stable slug: <issuer>-<merchant>-<yyyymmdd of valid_from or first_seen>-<short hash>"},
    "merchant": {
      "type": "object", "required": ["name"],
      "properties": {
        "name": {"type": "string"},
        "merchant_id": {"type": "string", "description": "cc-smith merchant key used by the payment-time matcher, e.g. amazon.in"},
        "channel": {"type": "string", "enum": ["online", "in_store", "both"]},
        "category": {"type": "string", "description": "cc-smith MCC-style category, e.g. travel.flights"}
      }
    },
    "issuer": {"type": "string", "description": "issuer key from official-domains.yaml, e.g. hdfc_bank, sbi_card"},
    "network": {"type": ["string", "null"], "enum": ["visa", "mastercard", "rupay", "amex", "diners", null], "description": "set when the offer is network-funded (e.g. Visa Signature) rather than issuer-funded"},
    "card_eligibility": {
      "type": "object",
      "properties": {
        "card_types": {"type": "array", "items": {"type": "string", "enum": ["credit", "debit", "credit_emi", "debit_emi", "netbanking", "upi"]}},
        "include_cards": {"type": "array", "items": {"type": "string"}, "description": "cc-smith card ids; empty = all cards of the issuer"},
        "exclude_cards": {"type": "array", "items": {"type": "string"}, "description": "e.g. co-branded cards, corporate cards"},
        "raw_text": {"type": "string", "description": "eligibility sentence as published, kept for audit"}
      }
    },
    "benefit": {
      "type": "object", "required": ["kind"],
      "properties": {
        "kind": {"type": "string", "enum": ["instant_discount", "cashback", "voucher", "bonus_points", "emi_discount", "no_cost_emi", "other"]},
        "percent": {"type": ["number", "null"]},
        "flat_amount_inr": {"type": ["number", "null"]},
        "max_discount_inr": {"type": ["number", "null"]},
        "min_txn_inr": {"type": ["number", "null"]},
        "per_card_cap": {"type": ["string", "null"], "description": "e.g. once per card per offer period; free text until modelled"},
        "headline": {"type": "string", "description": "as published, e.g. '10% instant discount up to ₹1,500'"}
      }
    },
    "promo_code": {"type": ["string", "null"]},
    "days_of_week": {"type": ["array", "null"], "items": {"type": "string", "enum": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]}, "description": "null = every day"},
    "valid_from": {"type": ["string", "null"], "format": "date"},
    "valid_to": {"type": "string", "format": "date"},
    "tnc_url": {"type": ["string", "null"], "format": "uri"},
    "source": {
      "type": "object", "required": ["url", "host_class", "fetched_at"],
      "properties": {
        "url": {"type": "string", "format": "uri"},
        "host_class": {"type": "string", "enum": ["issuer", "merchant", "network", "aggregator", "community", "manual"]},
        "fetched_at": {"type": "string", "format": "date-time"},
        "extractor": {"type": "string", "description": "watcher name + version, or 'curator'"},
        "raw_ref": {"type": ["string", "null"], "description": "pointer to the stored raw HTML/JSON snapshot"},
        "secondary_refs": {"type": "array", "items": {"type": "string", "format": "uri"}}
      }
    },
    "confidence": {"type": "string", "enum": ["official", "speculation"], "description": "official only when source.host_class is issuer or merchant and the host is in official-domains.yaml"},
    "status": {"type": "string", "enum": ["draft", "live", "expired", "withdrawn"]},
    "first_seen_at": {"type": "string", "format": "date-time"},
    "last_verified_at": {"type": "string", "format": "date-time"},
    "notes": {"type": ["string", "null"]}
  }
}
```

Example (values from the Kotak listing fetched 2026-10-07; the min/max numbers come from the published description text, not from the T&C PDF, so `confidence` stays `official` only for the fields the listing itself states):

```json
{
  "id": "kotak_mahindra_bank-tatacliq-20261007-3f9a",
  "merchant": {"name": "Tata CLiQ", "merchant_id": "tatacliq.com", "channel": "online", "category": "shopping.fashion"},
  "issuer": "kotak_mahindra_bank",
  "network": null,
  "card_eligibility": {
    "card_types": ["credit"],
    "include_cards": [],
    "exclude_cards": [],
    "raw_text": "on select Kotak Bank Credit Cards at Tata CLiQ Fashion & Luxury"
  },
  "benefit": {
    "kind": "instant_discount",
    "percent": 12.5,
    "flat_amount_inr": null,
    "max_discount_inr": 1000,
    "min_txn_inr": 3000,
    "per_card_cap": null,
    "headline": "12.5% instant discount | Minimum transaction ₹3,000 | Maximum discount ₹1,000"
  },
  "promo_code": null,
  "days_of_week": null,
  "valid_from": null,
  "valid_to": "2027-03-27",
  "tnc_url": null,
  "source": {
    "url": "https://www.kotak.bank.in/en/offers.html",
    "host_class": "issuer",
    "fetched_at": "2026-10-07T00:00:00+05:30",
    "extractor": "kotak-offers-watcher@0.1",
    "raw_ref": "snapshots/2026-10-07/kotak-offers.html",
    "secondary_refs": []
  },
  "confidence": "official",
  "status": "live",
  "first_seen_at": "2026-10-07T00:00:00+05:30",
  "last_verified_at": "2026-10-07T00:00:00+05:30",
  "notes": "'select' cards not enumerated on the listing; detail page / T&C PDF needed before using in rewards maths"
}
```

---

## (e) Unverified / not checked

- HDFC SmartBuy offer-detail pages (one id returned 500); whether `/ps/offers` really has "up to 10,000 offers"; HDFC robots.txt line-by-line.
- Axis vendor API: method/payload for `allOffer`, `offerDetails`, `categoryList`; whether it needs a token (`createToken` exists); its stability and any terms. Only `GET /partnerList` was observed to work.
- Kotak: the AJAX URL behind `articlelistingfilter` (the `.json` variants tried returned component config or 400); full 57-offer list beyond the 22 in HTML.
- SBI Card: how the detail page receives its offer id; min txn / max discount / T&C per offer; whether the inline JSON is complete or only "featured" (95 objects vs "510+ brands" in filters).
- ICICI: whether the main grid is filled by an AJAX endpoint (none found in HTML); terms-of-use text.
- HSBC, GrabOn, CouponDunia, DesiDime terms pages (404 at guessed URLs or not fetched).
- IndusInd offers URL; MakeMyTrip promos page (unreachable from sandbox); Dealsrank (unreachable); CashKaro and Paisabazaar bank-offer URLs; Telegram channel names.
- TechnoFino Wayback coverage (archive rate-limited/"Temporarily Offline" during this run); Wayback for Axis Grab Deals, ICICI /offers (0 snapshots since 2026 for the legacy URL), IDFC, RBL.
- Arctic Shift usage policy and real rate limits (only observed: 2 of 3 calls returned 422).
- Visa per-offer page structure; whether RuPay/Mastercard pages work in a real browser.
- Update frequency for every portal (only SBI showed two in-week start dates; nothing else was observed over time).
- Everything above was fetched once, from one IP, with one UA; behaviour under scheduled load is untested.
