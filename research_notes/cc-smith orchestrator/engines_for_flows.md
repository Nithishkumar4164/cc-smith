# SerpApi Engines Beyond AI Mode, Mapped to cc-smith Flows (checked 2026-10-06)

Method: this note builds on `SerpApi capabilities for hackathon/engines_catalog.md` and `serpapi_tool_surface.md`, which I did not redo. On 2026-10-06 I re-read three kinds of source:
- https://serpapi.com/llms.txt (122 doc links; the supported-engines list now also names **Airbnb**).
- Each candidate's `https://serpapi.com/<slug>.md`, or its HTML page when no .md exists.
- Every engine's `https://serpapi.com/<slug>/api-metrics` page. The engine dropdown on those pages lists 125 engines.

Engines found that the earlier catalog did not have:
- `google_ads_transparency_center_ad_details`
- `google_about_this_result`
- `google_trends_news`
- `google_scholar_profiles`
- `airbnb`

Metrics are SerpApi's "last 30 days" average success rate and average response time, read on 2026-10-06.

**Cost:** 1 credit per successful search on every engine. "Cached, errored, and failed searches are not [counted]… responses with 100 results or empty result sets will both count as 1 search" ([pricing.md](https://serpapi.com/pricing.md)). The Google Ads engine's "higher rate" ([google-ads-api](https://serpapi.com/google-ads-api)) means it shows ads more often, not that it costs more. Every token hop to a detail engine (ad details, video transcript, place reviews, immersive product, trends news) is another credit.

**Not verified live:** no SerpApi key was available in this environment, so I ran no India queries. Response fields below come from the docs' sample JSON, which are mostly US examples. India support comes from SerpApi's region/locale lists. Anything marked **UNVERIFIED** needs a test call.

Verdict scale:
- **Strong**: should be in the build.
- **Useful**: worth adding if time allows.
- **Niche**: an edge use only.
- **Not useful**.

---

## 1. Metrics for every candidate (from /api-metrics, 2026-10-06)

| engine | success | avg latency | | engine | success | avg latency |
|---|---|---|---|---|---|---|
| google_ads_transparency_center | 99.99% | 1.40 s | | google_trends | 99.996% | 3.21 s |
| google_ads_transparency_center_ad_details | 99.997% | 3.41 s | | google_trends_trending_now | 100% | 1.36 s |
| google_ads | 93.80% | 12.00 s | | google_trends_news | 100% | 1.61 s |
| youtube | 99.999% | 2.50 s | | google_autocomplete | 99.999% | 0.82 s |
| youtube_video | 100% | 1.52 s | | google_related_questions | 100% | 1.07 s |
| youtube_video_transcript | 99.85% | 10.08 s | | google_about_this_result | 100% | 1.32 s |
| youtube_channel | 99.69% | 1.67 s | | search_index (preview) | 99.97% | **0.43 s** |
| google_light | 99.26% | 3.71 s | | duckduckgo (search_assist) | 99.99% | 2.62 s |
| google (full) | 94.99% | 8.84 s | | bing_copilot | 99.83% | 17.83 s |
| google_forums | **82.96%** | **26.99 s** | | bing | 99.98% | 10.25 s |
| google_news_light | 99.02% | 1.42 s | | bing_news | 99.996% | 1.30 s |
| google_ai_overview | 99.86% | 9.24 s | | baidu | 99.67% | 14.51 s |
| google_play | 100% | 1.56 s | | naver_ai_overview | 99.998% | 6.68 s |
| google_play_product | 99.999% | 2.14 s | | instagram_profile | 99.995% | 2.82 s |
| apple_app_store | 99.999% | 1.83 s | | facebook_profile | 99.999% | 2.08 s |
| apple_product | 100% | 2.22 s | | amazon | 99.97% | 2.18 s |
| apple_reviews | 100% | 1.25 s | | amazon_product | 99.96% | 8.93 s |
| google_lens | 99.35% | 5.37 s | | google_immersive_product | 97.21% | 1.28 s |
| google_maps | 99.996% | 0.72 s | | google_shopping_light | 98.49% | 1.36 s |
| google_maps_reviews | 99.999% | 1.38 s | | google_flights | 99.998% | 6.20 s |
| google_maps_posts | 100% | 1.02 s | | google_hotels | 99.999% | 2.24 s |
| apple_maps | 100% | 0.39 s | | google_images | 99.29% | 6.31 s |
| apple_maps_places | 99.54% | 0.10 s | | google_jobs | 83.75% | 18.86 s |
| google_local | 90.23% | 26.09 s | | google_local_services | 99.999% | 1.58 s |
| google_finance | 99.996% | 0.85 s | | google_videos | 96.87% | 13.88 s |

The URL pattern is `https://serpapi.com/<doc-slug>/api-metrics`, for example [Ads Transparency](https://serpapi.com/google-ads-transparency-center-api/api-metrics), [Search Index](https://serpapi.com/search-index-api/api-metrics) and [Google Forums](https://serpapi.com/google-forums-api/api-metrics). The overall all-engine average is at https://serpapi.com/api-metrics.

**Latency takeaway for Checkout Advisor (~1 s):** only `search_index` (0.43 s), `apple_maps` and `apple_maps_places` (0.39 s / 0.10 s), `google_maps` (0.72 s), `google_autocomplete` (0.82 s) and `google_finance` average under 1 s. Even these should stay off the payment path. Use them in precompute or in a cache-miss fallback that runs after the answer has been given.

---

## 2. Candidates, engine by engine

### 2.1 Ads intelligence (Launch Radar, offers)

**`google_ads_transparency_center`: STRONG (Launch Radar, Cap Watch offers)**
- **Params:** `advertiser_id` (single or comma-separated), or `text`, which is free text "typically related to a domain search" and stands in for `advertiser_id`. Other params:
  - `region`: India = `2356` per the [regions list](https://serpapi.com/google-ads-transparency-center-regions.json).
  - `platform`: SEARCH, YOUTUBE, PLAY, MAPS or SHOPPING.
  - `start_date` / `end_date` as YYYYMMDD.
  - `creative_format`: text, image or video.
  - `num`: default 40.
  - `get_advertiser`: legal name and country.
  - `next_page_token` for paging.
- **Returns:** `ad_creatives[]` with `advertiser_id`, `advertiser`, `ad_creative_id`, `format`, `first_shown`, `last_shown` (epoch), `total_days_shown`, `details_link` and `serpapi_details_link`. Also `advertiser{legal_name, country}` and `search_information.total_results`.
- **Source:** [docs](https://serpapi.com/google-ads-transparency-center-api.md)
- **Follow-up engine `google_ads_transparency_center_ad_details`** takes `advertiser_id` and `creative_id`, both required, plus `region`. It returns:
  - `search_information`: `format`, `last_shown`, and `regions[]` with `first_shown`/`last_shown` per country.
  - `ad_creatives[]`: `title`, `headline`, `snippet`, `visible_link`, `sitelink_texts[]` for text ads; `call_to_action`, `snippet`, `link` and `image` URL for image ads; plus video ads.
  - Source: [docs](https://serpapi.com/google-ads-transparency-center-ad-details)
- **How to use it in Launch Radar:**
  1. Run a nightly job per issuer: `engine=google_ads_transparency_center&text=hdfcbank.com&region=2356&start_date=<today-7>&end_date=<today+1>&creative_format=text&num=100`.
  2. Keep creatives whose `first_shown` falls inside the window and is not yet seen.
  3. Call `..._ad_details` for each one.
  4. An LLM classifies the headline, snippet and sitelinks as new card / new offer / fee change / noise.
- Run the same pass with `creative_format=image`. Image ad text is often only in the image, so it needs a vision model; at least `snippet` and `call_to_action` are sometimes present.
- Store each issuer's `advertiser_id` once the first `text` lookup has found it.
- **Cost:** 1 credit plus N detail credits. Budget the detail calls carefully, for example only new creatives that mention "card".
- **Caveats (UNVERIFIED):**
  - How complete India coverage is.
  - Whether banks advertise through agency accounts, which would give several advertiser IDs per bank.
  - The ad text is marketing copy, not terms. Always confirm against the issuer page via the AI Mode profile refresh.

**`google_ads` (sponsored results on a SERP): USEFUL (Launch Radar, offers)**
- **Params:** `q`, `location`, `hl`, `safe`, `nfpr`, `device`. There is **no `gl` or `google_domain`**, so India has to come from `location`, for example "Mumbai,Maharashtra,India".
- **Returns:** `ads[]` with `title`, `link`, `displayed_link`, `description`, `source` and `sitelinks[]`. Also `inline_videos`, `related_questions` (with AI-overview `page_token`), `ai_overview` and `organic_results`.
- **Source:** [docs](https://serpapi.com/google-ads-api.md)
- **Example:** `q="lifetime free credit card"` or `q="best travel credit card India"` shows which bank is pushing which card and offer this week, for example "₹1,000 voucher on activation". Use it for Launch Radar offer detection and Card Finder "current joining offer" hints.
- **Downsides:** 12.0 s and **93.8%** success. Use it only in a weekly batch. Ads Transparency is the better primary source.

### 2.2 Video (Card Finder qualitative, Launch Radar, Cap Watch)

**`youtube`: USEFUL (Launch Radar, Cap Watch change detection, Card Finder)**
- **Params:** `search_query`, `gl=in`, `hl=en` and `sp` (filter/sort token, e.g. upload date).
- **Returns:** `video_results[]` with `title`, `link`, `video_id`, `channel{name, verified}`, `published_date` (relative, e.g. "8 days ago"), `views`, `length` and `description`. Also `channel_results`, `shorts_results` and `ads_results`.
- **Source:** [docs](https://serpapi.com/youtube-search-api.md)
- **Example:** `search_query="HDFC Infinia devaluation"` or `"new credit card launch October 2026"`. Indian card creators often report devaluations and launches within hours, so this is a good *signal* that triggers an AI Mode re-extract.
- **Caveat:** it is not an authoritative source, so never write a profile field from it.

**`youtube_video_transcript`: USEFUL, batch only**
- **Params:** `v` (required), `language_code` (default `en`; `hi` for Hindi reviews, UNVERIFIED availability), `type=asr` for auto captions, `title`.
- **Returns:** `transcript[]` with `start_ms`, `end_ms`, `snippet` and `start_time_text`, plus chapters and the available transcripts.
- **Source:** [docs](https://serpapi.com/youtube-video-transcript.md) and the [HTML sample](https://serpapi.com/youtube-video-transcript)
- **Uses:**
  - Card Finder "reviewer pros/cons" summary.
  - Launch Radar: extract what changed from a devaluation video, then confirm on the issuer site.
- **Downsides:** 10.08 s. Hinglish ASR quality is UNVERIFIED.

**`youtube_video`: NICHE**
- Returns `title`, `channel`, `extracted_views`, `extracted_likes`, `published_date` (absolute, e.g. "Mar 5, 2016"), `description.content` with links, `chapters` and `related_videos`. ([docs](https://serpapi.com/youtube-video-api.md))
- Use it to get an absolute publish date for dating a claim. The search engine only gives a relative date.

**`youtube_channel` (new Sep 2026): USEFUL (Launch Radar)**
- **Params:** `channel_id` (handle or id), `tab` (videos, shorts, live, …), `sort`, `search_query`, `about`.
- **Returns:** `channel_results{title, handle, external_id, rss_link, subscribers, video_count, …}`, `videos_results[]` with `title`, `video_id`, `published_date` and `views`, plus `filters`.
- **Source:** [docs](https://serpapi.com/youtube-channel-api.md)
- **Example:** a weekly poll of issuer channels (`channel_id=@HDFCBank` etc. — handles UNVERIFIED) and of top Indian card-review creators with `sort=latest`.
- **Credit-saving tip:** the response exposes `rss_link` (`youtube.com/feeds/videos.xml?channel_id=…`). After one SerpApi call to resolve the channel id, poll the free RSS feed instead.

### 2.3 Web, forums and community (Cap Watch, Launch Radar, Eligibility Path)

**`google_light` with `site:` queries: STRONG (Cap Watch, Launch Radar, Eligibility Path)**
- **Params:** `q`, `location`, `uule`, `google_domain=google.co.in`, `gl=in`, `hl`, `lr`, `safe`, `nfpr`, `filter`, `start`, `device`. There is **no `tbs`**, so no date filter.
- **Returns:** `organic_results[]` (title, link, snippet, date where shown), `related_questions` and `related_searches`.
- **Source:** [docs](https://serpapi.com/google-light-api.md)
- **Examples:**
  - `q="site:technofino.in Infinia capping"`
  - `q="site:reddit.com/r/CreditCardsIndia SBI Cashback cap"`
  - `q="<card> pre-approved FD backed eligibility site:technofino.in"` for Eligibility Path: community experiences of card-against-FD and upgrade routes.
- 3.71 s, about 2.4× faster than full `google` (8.84 s).
- When you need a recency filter, use full **`google`** with `tbs=qdr:w`. Full `google` also returns the **`discussions_and_forums`** block (title, link, `date`, `source`, `extensions` such as "40+ comments", `answers[]`) ([Discussions and Forums](https://serpapi.com/google-discussions-forums)), and the `perspectives` block ([Perspectives](https://serpapi.com/perspectives)).
- **Caveat:** community posts are signals. Use them to trigger re-verification, never as a profile source.

**`google_forums`: NOT USEFUL (despite being made for this)**
- It has nice params (`period_unit`/`period_value`, `start_date`/`end_date`) ([docs](https://serpapi.com/google-forums-api.md)).
- But it averages **26.99 s at 82.96% success**. Use `google` (discussions block, `tbs`) or `google_light` + `site:` instead.

**`google_news_light`: USEFUL (Launch Radar, Cap Watch), as a faster version of the google_news already in the plan**
- Returns `news_results` and `top_stories` with `start` paging.
- 1.42 s vs 5.07 s for `google_news`.
- **`site:` no longer supported** (Sep 2026) ([docs](https://serpapi.com/google-news-light-api.md)). Keep `google_news` for `site:` and `when:` queries, and use the light engine for broad sweeps.

**`bing_news`: USEFUL as a second news source**
- **Params:** `q`, `mkt=en-IN`, `cc=in`, `qft` (`interval="7"` = past 24 h, `"8"` = past 7 days), `first`, `count`.
- 1.30 s / 99.996% ([docs](https://serpapi.com/bing-news-api.md)).
- It de-risks Launch Radar against Google News gaps. Indian market support is assumed from the `mkt` format; it is not on a SerpApi list I checked.

**`search_index` (SerpApi's own index, preview): USEFUL, with quality UNVERIFIED**
- **Params:** `q`, `num`, `start`, `safe`, and `mode=deep` ("parallel sub-query fan-out").
- **Returns:** `organic_results[]` (title, link, snippet, **date**, language) and `related_searches`.
- 0.43 s / 99.97% ([docs](https://serpapi.com/search-index-api.md)).
- It is the only sub-second web search. Possible uses:
  - A cheap first pass to find issuer MITC/T&C URLs.
  - A latency-tolerant fallback for "offer at merchant X" lookups in Checkout Advisor precompute.
- **Gaps:** no `gl`/locale param, so India relevance is unknown. Freshness and `site:` support are UNVERIFIED. It is a preview product.

**`google_autocomplete`: USEFUL (Card Finder input, entity resolution)**
- **Params:** `q`, `gl=in`, `hl`, `cp`, `client`. **Returns:** `suggestions[]` (value, relevance, type) ([docs](https://serpapi.com/google-autocomplete-api.md)).
- 0.82 s.
- Normalizes user-typed card names, e.g. "hdfc infinia met" → "hdfc infinia metal edition", before the profile-store lookup.
- **Launch Radar trick:** a weekly `q="<issuer> credit card"` call. New suggestion strings, such as a new card name, are an early launch signal.

**`google_related_questions`: NICHE**
- Expands "People also ask" via `next_page_token`. 1.07 s ([docs](https://serpapi.com/google-related-questions-api.md)).
- Could seed Eligibility Path FAQ ("Can I get <card> on a ₹30k salary?"). AI Mode covers this better.

**`google_about_this_result`: NICHE (Card Profile provenance)**
- `q=<URL>` or `req_token` from `organic_results[].about_page_serpapi_link`.
- Returns `about_this_result{about_the_source{description, in_their_own_words, site_first_indexed_by_google, …}, web_results_about_the_source[]}` ([docs](https://serpapi.com/google-about-this-result)). 1.32 s.
- Could add a "source trust" score per reference domain, e.g. confirm that `<x>.com` is really the issuer before trusting a fee number. Optional.

### 2.4 AI answers from other engines (cross-checking the Card Profile)

**`duckduckgo` `search_assist` block: USEFUL (cheap second opinion)**
- **Params:** `q`, `kl` (region, e.g. `in-en`, UNVERIFIED value), `search_assist`, `df` (date), `start`, `m`.
- **Returns:** `search_assist{answer, expanded_answer (markdown), sources[{link, site, text}]}`, plus `organic_results` and `news_results` ([docs](https://serpapi.com/duckduckgo-search-api.md)).
- 2.62 s, which is far faster than Brave (20.4 s) or Copilot (17.8 s).
- Use it to cross-check a disputed field ("SBI Cashback card monthly cashback cap") when AI Mode and the issuer page disagree.
- Whether the block appears for Indian card queries is UNVERIFIED.

**`bing_copilot`: NICHE**
- The only param is `q`, with no locale control. Returns `header`, `text_blocks` and `references` ([docs](https://serpapi.com/bing-copilot-api.md)).
- 17.83 s. The lack of locale control makes India answers unreliable. Use it only as a tiebreaker.

**`google_ai_overview`: NICHE** (already in the plan as a fallback). 9.24 s on top of the `google` call, and the token expires in 1 minute.

**`baidu` (AI block), `naver_ai_overview`, `yandex`: NOT USEFUL.** These are Chinese, Korean and Russian markets with no Indian card coverage.

### 2.5 Trends (Card Finder popularity, Launch Radar)

**`google_trends`: USEFUL**
- **Params:**
  - `q`: up to 5 comma-separated terms for TIMESERIES and GEO_MAP; 1 for related data.
  - `geo=IN`, plus `region` for state/city.
  - `data_type`: TIMESERIES, GEO_MAP, GEO_MAP_0, RELATED_TOPICS, RELATED_QUERIES.
  - `date`: e.g. `today 3-m`, `now 7-d`.
  - `cat=811` (**Credit Cards** in the [Trends categories](https://serpapi.com/google-trends-categories.json)).
  - `gprop`, `tz`, `csv`, `include_low_search_volume`.
- **Returns:** `interest_over_time` (and related blocks per `data_type`) ([docs](https://serpapi.com/google-trends-api.md)).
- **Uses:**
  - Card Finder "popularity" tie-breaker: `q="HDFC Regalia Gold,Axis Atlas,SBI Cashback,Amex Platinum Travel,ICICI Emeralde"&geo=IN&date=today 3-m`.
  - Launch Radar: `data_type=RELATED_QUERIES&q=credit card&geo=IN&cat=811&date=now 7-d`. "Rising" queries surface new card names.
- 3.21 s.

**`google_trends_trending_now` → `google_trends_news`: NICHE**
- `geo=IN`, `category_id=3` (Business and Finance) ([trending-now](https://serpapi.com/google-trends-trending-now.md), [categories](https://serpapi.com/google-trends-trending-now-categories.json)).
- `google_trends_news` takes the `news_page_token` and returns `news[]` (title, link, date) ([docs](https://serpapi.com/google-trends-news)).
- A card launch will rarely reach national trending, but a big devaluation (e.g. "Infinia") occasionally does.

### 2.6 App stores (Launch Radar for fintech or co-brand cards; Renewal Review context)

**`google_play` → `google_play_product`: USEFUL (Launch Radar, fintech cards)**
- **`google_play` params:** `q`, `gl=in`, `hl`, `apps_category`, `chart`, `store_device`. It returns `organic_results[].items[]` (title, `product_id`, rating, author, downloads).
- **`google_play_product` params:** `product_id`, `store=apps`, `gl=in`, `all_reviews`, `sort_by`, `rating`, `num`. It returns `product_info`, `about_this_app{updated_on, released_on, downloads}`, `what_s_new`, `ratings`, `reviews`, `data_safety` and `similar_results`.
- **Source:** [play](https://serpapi.com/google-play-api.md), [product](https://serpapi.com/google-play-product-api.md)
- **Uses:**
  - A weekly `q="credit card"&gl=in` call and a diff of `product_id`s catches new fintech/UPI-credit-card apps (Scapia/OneCard/Kiwi-type launches), which often appear before any news.
  - Bank-app `what_s_new` is weak but occasionally mentions new card features.
  - Reviews filtered with `rating=1` can flag "card servicing pain" for Renewal Review. That is soft data.

**`apple_app_store` / `apple_product` / `apple_reviews`: NICHE**
- Use `country=in` ([Apple regions](https://serpapi.com/apple-regions)).
- `apple_product` returns `version_history[]` (release_version, notes, date) and ratings ([docs](https://serpapi.com/apple-product.md)).
- It duplicates Play. Use Play first, because Android dominates in India.

### 2.7 Visual

**`google_lens`: NICHE**
- **Params:** `url` or `image_id` (upload via the Image API), `type` (all, products, exact_matches, visual_matches), `q` (with all/products/visual), `country=in` (India is in the [Lens countries](https://serpapi.com/google-lens-countries.json)), `hl`, `auto_crop`.
- **Returns:** `ai_overview`, `visual_matches[]` and `related_content` ([docs](https://serpapi.com/google-lens-api.md)). 5.37 s.
- **Card-art identification:** a photo of a card front with `type=exact_matches` might match the issuer's product image and identify the card. That is UNVERIFIED and a **privacy risk**: it sends card imagery to a third party, so it needs a masked or cropped image and explicit consent.
- **Receipt photo → merchant:** Lens does visual matching, not OCR. A local or LLM vision model reading the merchant name, then the cached merchant → category map, is better and faster.
- **Not for the 1 s Checkout path.**

**`google_images`: NICHE.** Fetches card art for the UI (`q="<card> card image"`). 6.31 s. Fine for a one-off asset fetch.

### 2.8 Maps and local (Checkout Advisor merchant category; already partly in the plan)

**`google_maps` (place_results / local_results `type`, `type_ids`): STRONG** (already in the plan). Precompute merchant → category; it is the fastest Google engine at 0.72 s.

**`apple_maps` / `apple_maps_places`: USEFUL as a fast second categorizer**
- `apple_maps` takes `query` plus `location` or `center`, and `locale=en-IN`. India is in the [Apple Maps locales](https://serpapi.com/apple-maps-locales.json).
- It returns `local_results[]` with `category_id` (e.g. `foodanddrink`) and `category_name`. `apple_maps_places` (`muid`) returns `type` / `type_ids` (e.g. `coffee_roastery`) ([apple-maps](https://serpapi.com/apple-maps-api.md), [places](https://serpapi.com/apple-maps-places-api.md)).
- 0.39 s / 0.10 s, the fastest place engines on SerpApi.
- **Caveats:** Apple's POI coverage in India is thinner than Google's (UNVERIFIED). Neither gives MCCs.

**`google_maps_reviews`: NICHE**
- Params `data_id`/`place_id`, `query`, `topic_id`, `sort_by`. It returns `place_info`, `topics` and `reviews` ([docs](https://serpapi.com/google-maps-reviews-api.md)).
- `query="card"` could surface "only cash/UPI accepted" or "surcharge on credit card" complaints for a merchant. That is a soft Checkout Advisor hint, precomputed only.

**`google_maps_posts`: NICHE.** `data_id` → `posts[]` ([docs](https://serpapi.com/google-maps-posts-api.md)). Merchant Google Business posts occasionally advertise "10% off with <bank> cards". The hit rate is likely low.

**`google_local`: NOT USEFUL** (26.09 s, 90.2%; Maps does the same job faster).

**`google_local_services`: NOT USEFUL.** These are Local Services Ads for home-service trades, from a fixed query list, with `data_cid` required ([docs](https://serpapi.com/google-local-services-api.md)). They are unrelated to cards, and India availability is UNVERIFIED.

### 2.9 Commerce (bank offers at the point of sale)

**`amazon` / `amazon_product` with `amazon_domain=amazon.in`: USEFUL, pending a test (Checkout Advisor merchant offers, Launch Radar offers)**
- `amazon_product` (`asin`, `amazon_domain`, `other_sellers`) returns `product_results{price, discount, coupons[], promotions[{type, text, discount_percent, eligibility}], offers[] (strings), delivery, stock}` and `purchase_options` ([docs](https://serpapi.com/amazon-product-api.md); `amazon.in` is in the [domains list](https://serpapi.com/amazon-domains)).
- **Hypothesis (UNVERIFIED):** on amazon.in, `offers[]` / `promotions[]` carry the "Bank Offer: 10% instant discount on <bank> credit card…" lines.
- If that holds, a nightly scrape of 20–50 high-traffic ASINs gives a live "<bank> card instant discount on Amazon" table for Checkout Advisor (channel = amazon.in), and offer-change events for Launch Radar.
- 8.93 s for product, 2.18 s for search. **Test one ASIN before you commit.**

**`google_immersive_product`: NICHE**
- `stores[]` carry `payment_methods`, `details_and_offers[]`, `discount`, `price` and `total` ([docs](https://serpapi.com/google-immersive-product-api.md)).
- On google.co.in these might show EMI or bank-offer text per seller. That is UNVERIFIED, and the sample shows "PayPal, Affirm accepted" (US).
- 1.28 s, but you need a Shopping call first to get the token.

**`google_shopping_light`: NICHE** (1.36 s; a faster form of the google_shopping already in the plan). It matters only for co-brand voucher valuation.

**`ebay`, `walmart`, `home_depot`, `zillow`, `yelp`, `airbnb`: NOT USEFUL.** These are US-centric (see the earlier catalog), with no card-offer data.

### 2.10 Travel (₹ value of travel-card benefits; Card Finder value and Renewal Review)

**`google_flights`: USEFUL for valuation, batch only**
- **Params:** `departure_id`/`arrival_id` (e.g. DEL/BOM), `outbound_date`, `type=2` (one-way), `currency=INR`, `gl=in`, `include_airlines` (e.g. `AI`, `6E`), `travel_class`.
- **Returns:** `best_flights[].price` and `price_insights{lowest_price, typical_price_range}` ([docs](https://serpapi.com/google-flights-api.md)). 6.20 s.
- **Use:** turn an airline co-brand card's flight voucher or miles into ₹. For example, typical DEL–BOM fare ÷ miles needed = ₹/mile, which feeds the "₹/yr value" figure in Card Finder and Renewal Review.
- Miles-per-route award charts do **not** come from SerpApi; take them from the profile or AI Mode.
- It does **not** give lounge access data.

**`google_hotels`: USEFUL for valuation, batch only**
- **Params:** `q`, `check_in_date`/`check_out_date`, `currency=INR`, `gl=in`, `brands` (e.g. Marriott, Taj), `hotel_class`.
- **Returns:** `properties[].rate_per_night.extracted_lowest` ([docs](https://serpapi.com/google-hotels-api.md)). 2.24 s.
- **Use:** put a ₹ value on a hotel co-brand card's free-night award (Marriott Bonvoy/Taj-type cards) for the Renewal Review "is the fee covered?" check.

**`google_travel_explore`, `google_flights_deals`: NOT USEFUL.** They give no card-specific signal.

### 2.11 Social

**`instagram_profile`: USEFUL (Launch Radar, offers)**
- `profile_id` + `next_page_token` → `profile_results{biography, followers, is_verified, posts[{shortcode, media_captions[], accessibility_caption ("Photo by X on September 05, 2026…"), is_video, product_type}]}` ([docs](https://serpapi.com/instagram-profile-api.md)). 2.82 s.
- **Use:** a weekly poll of issuer handles (`hdfcbank`, `sbicard_official`, `axis_bank`, … — exact handles UNVERIFIED). An LLM classifies `media_captions` as launch / offer / noise.
- **Caveat:** there is no explicit timestamp field in the sample. Parse the date out of `accessibility_caption`, or diff on `shortcode`.

**`facebook_profile`: NOT USEFUL.** It returns only page metadata (name, followers, category, phone, email, links, `photos[]`) and **no post text** ([docs](https://serpapi.com/facebook-profile-api.md)).

### 2.12 Clearly not relevant
- **`google_jobs`**: 83.75%, 18.86 s. No card signal.
- **`google_events`**: deprecated.
- **`google_scholar*`, `google_patents*`, `google_sports`**: no card signal.
- **`google_finance` / `google_finance_markets`**: bank stock prices; no card terms. A results-day news hook at most.
- **`google_short_videos` / `google_videos`**: 14 s; `youtube` is better.
- **`google_reverse_image` / `bing_reverse_image` / `yandex_images`**: no card signal.
- **`tripadvisor*`, `open_table_reviews`**: no card signal.
- **`google_play_games/books/movies`**: no card signal.
- **`naver`, `baidu_news`**: wrong markets.

---

## 3. By flow: what to add beyond the current plan

| Flow | Add (Strong) | Add (Useful) |
|---|---|---|
| Card Profile (shared) | — (AI Mode stays primary) | `duckduckgo` search_assist as a 2.6 s cross-check; `search_index` for fast MITC URL discovery (preview); `google_about_this_result` (niche) for source trust |
| Card Finder | — | `google_autocomplete` (name normalization), `google_trends` cat=811 (popularity tie-break), `youtube` + `youtube_video_transcript` (reviewer pros/cons), `google_flights` / `google_hotels` (₹ value of miles and free nights) |
| Checkout Advisor (~1 s, precompute only) | `google_maps` (already planned) | `apple_maps` / `apple_maps_places` (0.10–0.39 s second categorizer); `amazon_product` on amazon.in bank-offer lines (**test first**) |
| Coach: Eligibility Path | `google_light` + `site:technofino.in` / `site:reddit.com/r/CreditCardsIndia` (community-reported routes; verify with AI Mode) | `google` discussions_and_forums block |
| Coach: Cap Watch | `google_light` + `site:` forum queries (devaluation chatter is usually the earliest signal) | `youtube` (sort by upload date), `google_news_light`, `bing_news` (qft past 24 h) |
| Coach: Renewal Review | — | `google_hotels` / `google_flights` valuation; Play-store reviews (soft) |
| Launch Radar | `google_ads_transparency_center` + `_ad_details` (region 2356, new creatives per issuer domain) | `google_ads` (weekly SERP ads), `instagram_profile` (issuer posts), `youtube_channel` (then free RSS), `google_play` new-app diff, `google_trends` RELATED_QUERIES rising, `google_autocomplete` new-suggestion diff, `bing_news` / `google_news_light` |

## 4. Gaps / to verify with a key
1. Ads Transparency coverage of Indian bank advertisers, and the advertiser IDs per bank.
2. Whether amazon.in `amazon_product` exposes bank offers.
3. Whether `search_index` returns relevant, fresh Indian results (no locale param).
4. Whether the DDG `search_assist` block triggers for Indian card queries, and the correct `kl` value.
5. The Instagram and YouTube handles of each issuer.
6. Apple Maps POI coverage for Indian merchants.
7. Whether Google Immersive Product shows bank/EMI offers on google.co.in.
8. Hindi or Hinglish transcript availability for YouTube.
