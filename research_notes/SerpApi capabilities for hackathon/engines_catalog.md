# SerpApi Engine Catalog (as of Oct 2026)

Method note: the engine list, `engine=` ids, parameters and top-level response keys below were extracted from SerpApi's machine-readable docs on 2026-10-05: the index at https://serpapi.com/llms.txt (117 doc links) plus each engine's `https://serpapi.com/<slug>.md` page (YAML front-matter `engine:` field, parameter tables, and the "Response Example" JSON). Engines missing from llms.txt but present in the live docs sidebar (https://serpapi.com/search-api) were checked one by one in their HTML pages. Response keys are top-level keys of SerpApi's truncated sample responses, so they are a lower bound: real responses can carry more blocks depending on the query. Every engine also returns `search_metadata`, `search_parameters` and usually `search_information`. All engines are called through `GET https://serpapi.com/search?engine=<id>&api_key=...`, and all accept the common SerpApi params `no_cache`, `async`, `zero_trace` (Enterprise), `output` (`json` | `html` | `md`) and `json_restrictor`.

## What is the complete current list of engines and their engine= identifiers?

### Takeaway
SerpApi now covers 22 "engine families" (Google, Apple App Store, Apple Maps, Baidu, Bing, Brave AI Mode, Amazon, DuckDuckGo, eBay, Facebook, Instagram, Naver, OpenTable, Search Index, Home Depot, Tripadvisor, Walmart, Yahoo!, Yandex, Yelp, YouTube, Zillow). There are about 115 live `engine=` ids, roughly 70 of them Google. Several older engines are deprecated or shut down: `google_product`, `yahoo_shopping` and `google_events` (Aug 2026), and `google_jobs_listing` is now mostly empty.

### Cited Findings

**Families officially supported:** "Google, Apple App Store, Apple Maps, Baidu, Bing, Brave AI Mode, Amazon, DuckDuckGo, eBay, Facebook, Instagram, Naver, OpenTable, Search Index, The Home Depot, Tripadvisor, Walmart, Yahoo!, Yandex, Yelp, YouTube, Zillow" — [SerpApi llms.txt](https://serpapi.com/llms.txt)
- The official Postman collection (Apr 2026) "covers all 113 API endpoints across 21 folders grouped by search engine" — [Changelog Apr 06-12 2026](https://serpapi.com/blog/serpapi-weekly-changelog-april-06-12-2026/). Zillow and the YouTube Channel and eBay Seller APIs were added later, so the count is now higher.

**Catalog. Format: `engine_id`: main top-level response keys | notable params | pagination / follow-up tokens.** The source for each row is `https://serpapi.com/<doc-slug>`.

#### Google: core web search and AI
- `google` (Google Search): local_map, local_results, knowledge_graph, immersive_products, related_questions, organic_results, perspectives, related_searches, refine_this_search, refine_search_filters, things_to_know, pagination, serpapi_pagination. The response also embeds blocks such as `ai_overview` (which may contain only a `page_token`), answer_box, top_stories, events_results, jobs_results, shopping/inline blocks, and (2026) a flight result, a Transport Options answer box, and knowledge-graph products and booking options. | q, location, uule, lat/lon/radius (added Mar 2026), google_domain, gl, hl, cr, lr, tbs, safe, nfpr, filter, kgmid, ludocid, `tbm` (isch / lcl / vid / nws / shop / pts) | `start` offset plus serpapi_pagination — [search-api](https://serpapi.com/search-api); lat/lon — [Changelog Mar 02-08](https://serpapi.com/blog/serpapi-weekly-changelog-march-02-08-2026/); transport options — [Changelog Jul 20-26](https://serpapi.com/blog/serpapi-weekly-changelog-july-20-26-2026/); KG products/booking — [Changelog Sep 14-20](https://serpapi.com/blog/serpapi-weekly-changelog-sep-14-20-2026/); flight result — [Changelog Apr 20-26](https://serpapi.com/blog/serpapi-weekly-changelog-april-20-26-2026/)
- `google_light` (fast, lighter Google Search): organic_results, related_questions, related_searches, serpapi_pagination; the sidebar also lists answer_box, knowledge_graph, top_stories and spell_check | same core params, no tbm | `start` — [google-light-api](https://serpapi.com/google-light-api)
- `google_ai_overview`: the only param is `page_token` (required), taken from `ai_overview.page_token` in a `google` response. The token "expires within 1 minute of the search and should be used immediately." — [google-ai-overview-api](https://serpapi.com/google-ai-overview-api)
- `google_ai_mode`: text_blocks, reconstructed_markdown (added Feb 2026), references, shopping_results, related_questions, subsequent_request_token | q, location, uule, gl, hl, `image_url` (image in prompt, added Apr 2026), `continuable=true` | `subsequent_request_token` for multi-turn follow-ups ("include a new `q`… reuse the same localization settings") — [google-ai-mode-api](https://serpapi.com/google-ai-mode-api); [Changelog Feb 16-22](https://serpapi.com/blog/serpapi-weekly-changelog-february-16-22-2026/); [Changelog Apr 13-19](https://serpapi.com/blog/serpapi-weekly-changelog-april-13-19-2026/)
- `google_ads` (new May 2026; sponsored results "at a higher rate than the standard Google Search API"): ads, inline_videos, related_questions, ai_overview, organic_results, related_searches | q, location, hl — [google-ads-api](https://serpapi.com/google-ads-api); [Changelog May 25-31](https://serpapi.com/blog/serpapi-weekly-changelog-may-25-31-2026/)
- `google_ads_transparency_center`: advertiser, ad_creatives | advertiser_id, text, platform, political_ads, region, start_date/end_date, creative_format | next_page_token — [docs](https://serpapi.com/google-ads-transparency-center-api)
- `google_autocomplete`: suggestions, verbatim_relevance | q, gl, hl, cp, client — [docs](https://serpapi.com/google-autocomplete-api)
- `google_related_questions`: related_questions (expands "People also ask") | next_page_token — [docs](https://serpapi.com/google-related-questions-api)
- `google_forums`: organic_results, related_searches | start + serpapi_pagination — [docs](https://serpapi.com/google-forums-api)

#### Google: shopping and commerce
- `google_shopping`: shopping_results, filters | q, location, google_domain, gl, hl, `shoprs` (filter token), min_price, max_price, sort_by (1 = low→high, 2 = high→low), free_shipping, on_sale, small_business. **Caveat: "Google Shopping's current layout does not support offset pagination: the `start` parameter is ignored and every request returns the first page of results (around 40 items)."** Each result carries an `immersive_product_page_token`. — [google-shopping-api](https://serpapi.com/google-shopping-api)
- `google_shopping_light`: shopping_results, categorized_shopping_results, serpapi_pagination; same params — [docs](https://serpapi.com/google-shopping-light-api)
- `google_shopping_filters`: filter options and shop tokens (brands, prices, colors, sizes) for a query, to feed `shoprs` — [docs](https://serpapi.com/google-shopping-filters-api)
- `google_immersive_product`: product_results (stores/sellers, prices, specs, reviews) | `page_token` (required, from Shopping/AI Mode/Search), `more_stores` | `next_page_token` and `stores_next_page_token` — [docs](https://serpapi.com/google-immersive-product-api)
- DEPRECATED `google_product`: "Google has shutdown the Google Product service… our Google Product API will now return an error… The Google Immersive Product API… should be used instead." — [google-product-api](https://serpapi.com/google-product-api)

#### Google: travel
- `google_flights`: best_flights, other_flights, price_insights, airports | departure_id/arrival_id (IATA or kgmid, comma-separated multi), outbound_date, return_date, `type` (1 round trip, 2 one-way, 3 multi-city via `multi_city_json`), travel_class, adults/children/infants, sort_by, stops, include_airlines/exclude_airlines, bags, max_price, outbound_times, emissions, layover_duration, max_duration, show_hidden, deep_search, `currency`, gl, hl. `exclude_basic` only works for US domestic flights (`gl=us`). | `departure_token` returns the return-leg flights; `booking_token` returns booking options (the two cannot be combined). `selected_flights_json` / flight-number pinning was added in Jul 2026. — [google-flights-api](https://serpapi.com/google-flights-api); [Changelog Jun 29-Jul 05](https://serpapi.com/blog/serpapi-weekly-changelog-june-29-july-05-2026/)
- `google_flights_autocomplete`: suggestions (airports and cities) — [docs](https://serpapi.com/google-flights-autocomplete-api)
- `google_flights_deals` (AI Flight Deals, Jun 2026): departure_informations, deals | departure_id, currency, travel_duration, trip_length, max_price; a `search` param was added in Sep 2026 — [docs](https://serpapi.com/google-flights-deals-api); [Changelog Jun 01-07](https://serpapi.com/blog/serpapi-weekly-changelog-june-01-07-2026/); [Changelog Sep 07-13](https://serpapi.com/blog/serpapi-weekly-changelog-sep-07-13-2026.md)
- `google_travel_explore`: destinations (with flight/price info) | departure_id, arrival_area_id, month, travel_duration, `interest`, travel_mode, currency, max_price, max_duration — [docs](https://serpapi.com/google-travel-explore-api)
- `google_hotels`: brands, ads, properties, serpapi_pagination | q, check_in_date, check_out_date, adults, children, children_ages, `currency`, gl, hl, sort_by, min_price/max_price, property_types, amenities, rating, brands, hotel_class, free_cancellation, special_offers, eco_certified, `vacation_rentals` (with bedrooms/bathrooms) | `next_page_token`; `property_token` returns property details (name, address, phone, prices, nearby places) — [google-hotels-api](https://serpapi.com/google-hotels-api)
- `google_hotels_autocomplete`: suggestions (each with a property_token) — [docs](https://serpapi.com/google-hotels-autocomplete-api)
- `google_hotels_reviews`: reviews | property_token, category_token, sort_by, source_number | next_page_token — [docs](https://serpapi.com/google-hotels-reviews-api)
- `google_hotels_photos` (new Feb 2026): photo galleries by section | property_token, next_page_token — [docs](https://serpapi.com/google-hotels-photos-api); [Changelog Feb 09-15](https://serpapi.com/blog/serpapi-weekly-changelog-february-09-15-2026/)

#### Google: local and maps
- `google_maps`: local_results (for `type=search`) or place_results (for a place), serpapi_pagination | q, `ll` (`@lat,lon,zoom`), location, lat, lon, z, nearby, google_domain, gl, hl, place_id, data_cid, type, min_price, max_price, min_rating, open_state, open_on_day, open_at_hour | `start` offset in steps of 20. The `data` param is deprecated (use place_id or data_cid). Since Apr 2026 it also parses vacation rentals, neighborhoods and hotels. — [google-maps-api](https://serpapi.com/google-maps-api); [Changelog Apr 06-12](https://serpapi.com/blog/serpapi-weekly-changelog-april-06-12-2026/)
- `google_maps_reviews`: place_info, topics, reviews | data_id or place_id, sort_by, topic_id, query, num | next_page_token — [docs](https://serpapi.com/google-maps-reviews-api)
- `google_maps_photos` (data_id, category_id, next_page_token); `google_maps_photo_meta` (data_id of a photo) — [docs](https://serpapi.com/google-maps-photos-api); [photo-meta](https://serpapi.com/google-maps-photo-meta-api)
- `google_maps_posts`: posts | data_id, next_page_token — [docs](https://serpapi.com/google-maps-posts-api)
- `google_maps_contributor_reviews`: contributor, reviews | contributor_id — [docs](https://serpapi.com/google-maps-contributor-reviews-api)
- `google_maps_autocomplete`: suggestions | q, ll, gl, hl — [docs](https://serpapi.com/google-maps-autocomplete-api)
- `google_maps_directions`: places_info, directions, durations | start_addr/end_addr (or data_id or coords), travel_mode, avoid, prefer, route, time, distance_unit — [docs](https://serpapi.com/google-maps-directions-api)
- `google_local`: local_map, local_results | q, location, google_domain, gl, hl, ludocid, tbs, start. `lsig` is deprecated on desktop. — [docs](https://serpapi.com/google-local-api); [changelog notice](https://serpapi.com/blog/llms.txt)
- `google_local_services` (Local Services Ads): local_ads | q (from a supported query list), `data_cid` (required); "Google's ID of a place (`place_id` parameter) has been discontinued by Google." — [docs](https://serpapi.com/google-local-services-api)

#### Google: jobs, news, knowledge, education
- `google_jobs`: filters, jobs_results, serpapi_pagination | q, location, uule, google_domain, gl, hl, lrad (radius), uds | `next_page_token`, 10 results per page. "Usage of `start` parameter… has been discontinued by Google". `chips` and `ltype` are deprecated by Google. — [google-jobs-api](https://serpapi.com/google-jobs-api)
- `google_jobs_listing` (detail by job id): "Google has updated the Jobs Listing endpoint… salaries, salaries_comparison, apply_options, and similar_jobs are no longer available. Currently, the only available field is ratings." `apply_options` now comes directly from google_jobs. — [docs](https://serpapi.com/google-jobs-listing-api)
- `google_news`: news_results, menu_links, related_topics, related_publications | q, gl, hl, topic_token, publication_token, section_token, story_token, kgmid, so (sort) — [docs](https://serpapi.com/google-news-api)
- `google_news_light`: news_results, top_stories, serpapi_pagination | `start`. "The `site:` search operator is no longer supported" (Sep 2026). — [docs](https://serpapi.com/google-news-light-api); [Changelog Sep 07-13](https://serpapi.com/blog/serpapi-weekly-changelog-sep-07-13-2026.md)
- `google_scholar`: organic_results, related_searches, pagination, serpapi_pagination | q, cites, as_ylo/as_yhi, cluster, as_sdt, lr, start, num — [docs](https://serpapi.com/google-scholar-api)
- `google_scholar_author` (author_id, view_op, sort, citation_id; the sidebar lists articles, cited_by, co_authors, citation); `google_scholar_cite` (q = result_id); `google_scholar_case_law` (new Apr 2026): case_results, from `case_id`. The `as_sdt=4` case-law search covers US courts only. — [author](https://serpapi.com/google-scholar-author-api); [cite](https://serpapi.com/google-scholar-cite-api); [case law](https://serpapi.com/google-scholar-case-law-api); [scholar](https://serpapi.com/google-scholar-api)
- `google_patents`: organic_results, summary, pagination | q, inventor, assignee, country, before/after, status, type, litigation, page, num. `google_patents_details` (patent_id) returns title, abstract, claims, inventors, assignees, citations, legal_events, similar_documents, and more. — [patents](https://serpapi.com/google-patents-api); [details](https://serpapi.com/google-patents-details-api)
- `google_trends`: interest_over_time (default), plus region/related data by `data_type` (TIMESERIES, GEO_MAP, GEO_MAP_0, RELATED_TOPICS, RELATED_QUERIES) | q, geo, region, date, tz, cat, gprop. `google_trends_autocomplete` returns suggestions. `google_trends_trending_now` returns trending_searches (geo, hours, category_id). — [trends](https://serpapi.com/google-trends-api); [trending now](https://serpapi.com/google-trends-trending-now)
- `google_finance`: graph, summary, knowledge_graph, news_results, financials, discover_more (q = `TICKER:EXCHANGE`, window). `google_finance_markets` returns markets and news_results (trend = indexes, most-active, gainers, …). — [finance](https://serpapi.com/google-finance-api); [markets](https://serpapi.com/google-finance-markets)
- `google_sports` (new Jul 2026; football, basketball, baseball, cricket, …) | kgmid, season_kgmid, type, tab — [docs](https://serpapi.com/google-sports-api); [Changelog Jul 06-12](https://serpapi.com/blog/serpapi-weekly-changelog-july-06-12-2026/)
- DEPRECATED (Aug 2026) `google_events`: "The Google Events API has been deprecated and no longer accepts new requests. Event data is still available via the `events_results` field of the Google Search API." — [Changelog Aug 24-30](https://serpapi.com/blog/serpapi-weekly-changelog-august-24-30-2026/). The doc page still describes events_results with q, location, htichips (date:today/week/…) and start, and still appears in llms.txt. — [google-events-api](https://serpapi.com/google-events-api)

#### Google: images, visual, video
- `google_images`: images_results, shopping_results, suggested_searches, related_searches | imgar, imgsz, image_color, image_type, licenses, chips | `ijn` page index. `google_images_light` (start); `google_images_related_content` (related_content_id). — [images](https://serpapi.com/google-images-api); [light](https://serpapi.com/google-images-light-api)
- `google_lens`: ai_overview, visual_matches, related_content | `url` or `image_id` (direct upload, Aug 2026), `type` = all / products / exact_matches / visual_matches, q, country, hl — [google-lens-api](https://serpapi.com/google-lens-api); [Changelog Aug 03-09](https://serpapi.com/blog/serpapi-weekly-changelog-august-03-09-2026/)
- `google_reverse_image`: image_results | image_url — [docs](https://serpapi.com/google-reverse-image)
- `google_videos` (video_results, related_searches), `google_videos_light`, and `google_short_videos` (short_video_results), all with `start` — [videos](https://serpapi.com/google-videos-api); [short](https://serpapi.com/google-short-videos-api)

#### Google Play
- `google_play` (apps; organic_results by section), `google_play_games`, `google_play_movies`, `google_play_books` | q, gl, hl, category, chart, age, store_device | next_page_token, section_page_token, see_more_token. `google_play_product` returns product_info, media, about_this_app, ratings, reviews, data_safety, similar_results (product_id, store, all_reviews, sort_by, num, next_page_token). — [play](https://serpapi.com/google-play-api); [product](https://serpapi.com/google-play-product-api)

#### Bing
- `bing`: ads, inline_videos, organic_results, related_searches. The docs also list knowledge_graph, answer_box, local_pack, top_stories, recipes, a Copilot answer, and events_results (added Sep 2026). | q, location, lat, lon, mkt, cc, first, filters — [bing-search-api](https://serpapi.com/bing-search-api); [Changelog Aug 31-Sep 06](https://serpapi.com/blog/serpapi-weekly-changelog-aug-31-sep-06-2026/)
- `bing_copilot`: header, text_blocks, references (q) — [docs](https://serpapi.com/bing-copilot-api)
- `bing_shopping` (shopping_results, filters, ads; `efirst`); `bing_product` (product_results, reviews_results, buying_options, variants; `product_token`) — [shopping](https://serpapi.com/bing-shopping-api); [product](https://serpapi.com/bing-product-api)
- `bing_news` (organic_results; first, count, qft); `bing_images` (images_results; first, count, filters); `bing_videos` (video_results); `bing_maps` (local_results; cp, place_id); `bing_reverse_image` (image_info, related_content, pages_with_this_image; next_page_token) — [news](https://serpapi.com/bing-news-api); [maps](https://serpapi.com/bing-maps-api); [reverse](https://serpapi.com/bing-reverse-image-api)

#### Other general and AI search engines
- `brave_ai_mode` (new Mar/Apr 2026, Brave's Leo): markdown, text_blocks, references, web_results, related_questions | q, location, lat, lon, country, language | `subsequent_request_token` (multi-turn) — [docs](https://serpapi.com/brave-ai-mode-api); [Changelog Mar 30-Apr 05](https://serpapi.com/blog/serpapi-weekly-changelog-march-30-april-05-2026/)
- `duckduckgo`: search_assist (an AI answer, Feb 2026), ads, organic_results, knowledge_graph, news_results, inline_images, related_searches | q, kl (region), safe, df, start. `duckduckgo_light` uses next_page_token. `duckduckgo_news` (news_results) and `duckduckgo_maps` (local_results; bbox, lat/lon). — [ddg](https://serpapi.com/duckduckgo-search-api); [Changelog Feb 02-08](https://serpapi.com/blog/serpapi-weekly-changelog-february-02-08-2026/)
- `yahoo` (organic_results, ads_results, inline_videos/images, shopping_results; p, yahoo_domain, b), `yahoo_images`, `yahoo_videos`. DEPRECATED: `yahoo_shopping` ("deprecated because Yahoo has shut down its Shopping platform… use our Google Shopping API"). — [yahoo](https://serpapi.com/yahoo-search-api); [yahoo shopping](https://serpapi.com/yahoo-shopping-search-api)
- `baidu` (organic_results, answer_box, related_searches, top_searches; an AI overview block was added Apr 2026; pn/rn) and `baidu_news` — [baidu](https://serpapi.com/baidu-search-api); [Changelog Apr 20-26](https://serpapi.com/blog/serpapi-weekly-changelog-april-20-26-2026/)
- `yandex` (organic_results, knowledge_graph; text, yandex_domain, lr, p), `yandex_images` (also covers reverse image via `url`), `yandex_videos` — [yandex](https://serpapi.com/yandex-search-api); [reverse](https://serpapi.com/yandex-reverse-image-api)
- `naver` (ads_results, web_results, place_results, shopping_results, ai_briefing, dictionary_result, …; `where=image` gives images, `where=news` gives news) and `naver_ai_overview` (markdown, text_blocks, references; page_token) — [naver](https://serpapi.com/naver-search-api); [naver images](https://serpapi.com/naver-images-api); [naver AI](https://serpapi.com/naver-ai-overview-api)
- `search_index`: "SerpApi's own, LLM-first web index… for AI grounding… Currently in preview." organic_results, related_searches | q, num, start, safe, mode — [search-index-api](https://serpapi.com/search-index-api)

#### YouTube
- `youtube`: video_results, shorts_results, channel_results, ads_results, plus sections | search_query, gl, hl, `sp` (filter/page token) — [docs](https://serpapi.com/youtube-search-api)
- `youtube_video`: title, channel, views, likes, description, chapters, related_videos, transcript, comments tokens | v, next_page_token (comments, related, replies) — [docs](https://serpapi.com/youtube-video-api)
- `youtube_video_transcript`: v, language_code, type (`asr` = auto-generated) — [docs](https://serpapi.com/youtube-video-transcript)
- `youtube_channel` (new Sep 2026): channel_results, videos_results, filters | channel_id (handle or id), tab (videos, shorts, live, podcasts, playlists, community), sort, search_query | next_page_token — [docs](https://serpapi.com/youtube-channel-api); [Changelog Sep 07-13](https://serpapi.com/blog/serpapi-weekly-changelog-sep-07-13-2026.md)

#### E-commerce
- `amazon`: organic_results, product_ads, featured_products, video_results, sponsored_brands, categories, filters, serpapi_pagination | k, amazon_domain, language, delivery_zip, shipping_location, s (sort), node, rh, page — [amazon-search-api](https://serpapi.com/amazon-search-api)
- `amazon_product`: product_results, purchase_options, about_item, bought_together, related_products, product_details, reviews_information, videos | asin, amazon_domain, other_sellers — [docs](https://serpapi.com/amazon-product-api)
- `amazon_autocomplete` (new Jul/Aug 2026): suggestions | k, amazon_domain — [docs](https://serpapi.com/amazon-autocomplete-api); [Changelog Jul 27-Aug 02](https://serpapi.com/blog/serpapi-weekly-changelog-july-27-august-02-2026/)
- `walmart` (organic_results; query, walmart_domain, sort, cat_id, min_price/max_price, store_id, page), `walmart_product` (product_result, reviews_results), `walmart_product_reviews`, `walmart_product_sellers` — [walmart](https://serpapi.com/walmart-search-api); [sellers](https://serpapi.com/walmart-product-sellers-api)
- `ebay` (organic_results, inline_results, categories; _nkw, ebay_domain, _udlo/_udhi price, _sop sort, _pgn page, show_only, buying_format), `ebay_product` (product_results, seller_results, related_products; review highlights added Jan 2026), `ebay_seller` (new Sep 2026; seller_results, product_results; seller_id, type=store/user) — [ebay](https://serpapi.com/ebay-search-api); [seller](https://serpapi.com/ebay-seller-api); [Changelog Sep 21-27](https://serpapi.com/blog/llms.txt)
- `home_depot` (products, filters, taxonomy; q, country, delivery_zip, store_id, lowerbound/upperbound, page), `home_depot_product`, `home_depot_product_reviews` — [docs](https://serpapi.com/home-depot-search-api)
- Apple: `apple_app_store` (organic_results; term, country, lang, num), `apple_product` (app page: rating, price, version_history, reviews, privacy), `apple_reviews` (reviews; page, sort) — [app store](https://serpapi.com/apple-app-store); [product](https://serpapi.com/apple-product)

#### Travel, local and dining (non-Google)
- `tripadvisor`: places, serpapi_pagination | q, lat, lon, tripadvisor_domain, `ssrc` (a all, r restaurants, A things to do, h hotels, g destinations, f forums; vacation rentals discontinued), offset, limit — [docs](https://serpapi.com/tripadvisor-search-api)
- `tripadvisor_place` (place_result; place_id) and `tripadvisor_reviews` (new Mar 2026; reviews; language, sort_by, rating, type_of_visit, offset, limit) — [place](https://serpapi.com/tripadvisor-place-api); [reviews](https://serpapi.com/tripadvisor-reviews-api)
- `yelp` (organic_results, ads_results, filters; find_desc, find_loc, cflt, sortby, start), `yelp_place` (place_results, full_menu), `yelp_reviews` — [yelp](https://serpapi.com/yelp-search-api)
- `open_table_reviews`: reviews_summary, reviews | rid (restaurant slug), page — [docs](https://serpapi.com/open-table-reviews-api)
- `apple_maps` (new Apr/May 2026): local_results, guide_results, refinement | query, center, span, location, sort, open_at, locale. `apple_maps_places` (new May 2026) returns place_results from a muid. — [apple maps](https://serpapi.com/apple-maps-api); [places](https://serpapi.com/apple-maps-places-api); [Changelog May 11-17](https://serpapi.com/blog/serpapi-weekly-changelog-may-11-17-2026/)
- `zillow` (new Aug 2026, US real estate): organic_results | region_id, map_bounds, price, beds, baths, home_type, …, page — [docs](https://serpapi.com/zillow-search-api); [Changelog Aug 17-23](https://serpapi.com/blog/serpapi-weekly-changelog-august-17-23-2026/)

#### Social
- `facebook_profile` (profile_results; profile_id) and `instagram_profile` (new May 2026; profile_results; profile_id, next_page_token) — [fb](https://serpapi.com/facebook-profile-api); [ig](https://serpapi.com/instagram-profile-api)

#### Non-engine utility APIs (sidebar)
- Account API, Locations API (`/locations.json` for the `location` param), Search Archive API (fetch async results by id), Pixel Position (GA Jun 2026), and Markdown Output (`output=md`, `/search.md` or `Accept: text/markdown`; "roughly half the tokens… Works with every API", Aug 2026) — [search-api sidebar](https://serpapi.com/search-api); [markdown-output](https://serpapi.com/markdown-output); [Changelog Aug 10-16](https://serpapi.com/blog/serpapi-weekly-changelog-august-10-16-2026/)

### Inferences
- Many items that look like separate "APIs" in the docs sidebar (for example "Google Lens Products API", "Bing Copilot Answer API", "Naver Images API", "DuckDuckGo Search Assist API", "Yandex Reverse Image API", "Google Flight Result API") are result blocks or `type`/`where` modes of a parent engine, not separate `engine=` values. The HTML pages for these show the parent engine id (for example `engine=google_lens`, `engine=naver`, `engine=yandex_images`).
- Treat the 2025-2026 "AI answer" engines as one sub-family for agent use cases: `google_ai_mode`, `google_ai_overview`, `bing_copilot`, `brave_ai_mode`, `naver_ai_overview`, the DuckDuckGo search_assist block, the Baidu AI overview block, and the `search_index` preview.

### Gaps
- No single official machine-readable list of every `engine=` value was found. The list above is assembled from llms.txt plus the sidebar, so a few rarely used engines could be missing.
- The sample responses for `google_ai_overview`, `google_hotels_photos`, `google_maps_photos`, `google_scholar_author`, `google_sports`, `youtube_video_transcript`, `baidu_news` and `google_play_movies` had no sample JSON in the .md docs, so their top-level keys were not verified. From memory (unverified), they are likely `ai_overview`, `photos`, `photos`/`categories`, `author`/`articles`/`cited_by`, `sports_results`, `transcript`, `organic_results` and `organic_results` respectively.
- Whether Google Events is fully shut down conflicts between sources. The Aug 2026 changelog says it is deprecated, while the docs page and llms.txt still list it.

## What does each return, and which engines support pagination or follow-up tokens?

### Takeaway
Pagination comes in three styles: (1) an offset or page number (`start`, `first`, `page`, `_pgn`, `b`, `p`, `offset`, `ijn`), (2) an opaque `next_page_token` exposed under `serpapi_pagination` (Jobs, Hotels, Maps reviews/photos/posts, Play, Ads Transparency, DDG Light, Bing reverse image, YouTube, Instagram), and (3) chaining tokens that drive a multi-step flow: departure_token/booking_token (Flights), property_token (Hotels), immersive_product_page_token/page_token (Shopping to Immersive Product), subsequent_request_token (AI Mode, Brave AI multi-turn), ai_overview.page_token (Search to AI Overview, valid about 1 min), and topic/publication/section/story tokens (News).

### Cited Findings
- Flights chain: run `google_flights` to get best_flights/other_flights, each with a `departure_token`. Re-calling with that token returns return-leg options; a `booking_token` returns booking options. "It cannot be used together with `departure_token`." — [google-flights-api](https://serpapi.com/google-flights-api)
- Hotels chain: `google_hotels` returns properties with a `property_token`. Passing `property_token` returns details, which then feed `google_hotels_reviews` and `google_hotels_photos`. Lists page with `next_page_token`. — [google-hotels-api](https://serpapi.com/google-hotels-api); [reviews](https://serpapi.com/google-hotels-reviews-api)
- Shopping chain: `google_shopping` results carry an `immersive_product_page_token`, which goes into `google_immersive_product` (page_token, more_stores, stores_next_page_token). Shopping itself has no offset pagination at present (about 40 items). — [google-shopping-api](https://serpapi.com/google-shopping-api); [immersive](https://serpapi.com/google-immersive-product-api)
- Maps chain: `google_maps` local_results give a data_id / place_id. These feed `google_maps_reviews` (next_page_token), `google_maps_photos`, `google_maps_posts` and `google_maps_directions` (start_data_id/end_data_id). Search results page with `start` in steps of 20. — [google-maps-api](https://serpapi.com/google-maps-api); [reviews](https://serpapi.com/google-maps-reviews-api)
- Jobs: `next_page_token` with 10 per page; `start` is discontinued. — [google-jobs-api](https://serpapi.com/google-jobs-api)
- AI Mode: send `continuable=true`, then pass `subsequent_request_token` with a new `q` for multi-turn. — [google-ai-mode-api](https://serpapi.com/google-ai-mode-api)
- AI Overview: the `ai_overview.page_token` from Search "expires within 1 minute". — [google-ai-overview-api](https://serpapi.com/google-ai-overview-api)
- Engines exposing `serpapi_pagination` in their samples include google, google_light, google_images(_light), google_videos(_light), google_short_videos, google_forums, google_news_light, google_scholar, google_patents, google_maps, google_jobs, google_hotels, google_shopping_light, google_play(_product), bing_images/videos/shopping, duckduckgo(_light/_news), yahoo*, yandex*, baidu, naver, amazon, walmart, ebay, home_depot, yelp, tripadvisor, open_table_reviews, apple_reviews, youtube, youtube_channel, instagram_profile, zillow and search_index. — per-engine docs linked above
- YouTube video: `comments_next_page_token`, `related_videos_next_page_token` and `replies_next_page_token`, all passed back as `next_page_token`. — [youtube-video-api](https://serpapi.com/youtube-video-api)
- `json_restrictor` trims output fields, and `output=md` gives LLM-friendly markdown. — [google-ai-overview-api params](https://serpapi.com/google-ai-overview-api); [markdown-output](https://serpapi.com/markdown-output)

### Inferences
- For agent tool-calling, the token chains (Flights, Hotels, Shopping→Immersive, Maps→Reviews) map naturally onto a "search then drill down" pair of tools. AI Mode multi-turn gives a ready-made research loop. Use the AI Overview token immediately inside the same request handler.

### Gaps
- Max pages and depth limits per engine (for example how many `start` pages Maps returns) are not documented consistently.

## Which engines work well for India, and are any unavailable for India?

### Takeaway
Every Google engine supports India through `google_domain=google.co.in`, `gl=in`, `hl=en` or `hl=hi` and Indian Indic locales, and `location` names from the Locations API. Flights, Hotels, Travel Explore and Flights Deals accept `currency=INR`. Amazon (`amazon.in`), Tripadvisor (`www.tripadvisor.in`), Apple App Store and Apple products (`country=in`) and Brave AI Mode (India is listed) also work. eBay, Yelp, Walmart, Home Depot (US/CA only), Zillow (US), Scholar case law (US courts) and the Flights `exclude_basic` filter do not serve India.

### Cited Findings
- `google.co.in` is in SerpApi's Google domains list (country_code `in`, country_name India) — [google-domains.json](https://serpapi.com/google-domains.json)
- INR (Indian Rupee) is in the Google Travel currencies list used by `currency` on Flights and Hotels; the default is USD — [google-travel-currencies](https://serpapi.com/google-travel-currencies); [google-flights-api](https://serpapi.com/google-flights-api)
- `amazon.in` (India) is a supported `amazon_domain` — [amazon-domains](https://serpapi.com/amazon-domains)
- `www.tripadvisor.in` (India) is a supported `tripadvisor_domain` — [tripadvisor-domains](https://serpapi.com/tripadvisor-domains)
- India is in Apple Regions (the `country` param for App Store engines) — [apple-regions](https://serpapi.com/apple-regions)
- India appears in Brave AI Mode's supported countries — [brave-countries.json](https://serpapi.com/brave-countries.json)
- The eBay domains list contains no Indian domain (eBay.in closed) — [ebay-domains](https://serpapi.com/ebay-domains)
- The Yelp domains list contains no Indian domain — [yelp-domains](https://serpapi.com/yelp-domains)
- Home Depot: "Only United States(`us`), and Canada(`ca`) are supported." — [home-depot-search-api](https://serpapi.com/home-depot-search-api)
- Walmart `walmart_domain` defaults to walmart.com, and the store list (4,743 stores) has US postal codes and addresses — [walmart-stores](https://serpapi.com/walmart-stores)
- Flights `exclude_basic` "only works for domestic flights in the US" — [google-flights-api](https://serpapi.com/google-flights-api)
- Scholar `as_sdt=4` case law selects "US courts only" — [google-scholar-api](https://serpapi.com/google-scholar-api)
- Zillow is a US real-estate site — [zillow-search-api](https://serpapi.com/zillow-search-api)
- SerpApi itself is running an India Hackathon (deadline Oct 10, 2026 11:59 PM IST; ₹3 lakh+ prizes; 6 tracks: AI Agents, Open-Source Integrations, Travel & Local Discovery, Commerce & Market Intelligence, Knowledge & Public Interest, Open Innovation). The free plan gives 250 searches per month. It recommends `serpapi-search-tools` (Python) or SerpApi MCP for agents. — [Introducing the SerpApi India Hackathon 2026](https://serpapi.com/blog/introducing-the-serpapi-india-hackathon-2026/)
- The hackathon's own track examples: compare flights, hotels near the venue and places to eat (Travel); track the same product's price across sellers (Commerce); use Google Jobs to find first developer roles filtered by location and experience (Knowledge); a local-event finder combining event search with Maps (Open Innovation). — [same post](https://serpapi.com/blog/introducing-the-serpapi-india-hackathon-2026/)

### Inferences
- **Recommended India stack by track:**
  - *AI Agents:* google_ai_mode (multi-turn, image_url), google (with ai_overview, then google_ai_overview), google_light (fast and cheap grounding), google_news, youtube_video_transcript, search_index (preview), brave_ai_mode, bing_copilot. Use `output=md` to save tokens, plus SerpApi MCP.
  - *Travel & local discovery (India):* google_flights (`currency=INR`, `gl=in`, IATA codes such as BLR, DEL, BOM, MAA), google_flights_deals and google_travel_explore (`departure_id=DEL`), google_hotels (with property_token, reviews, photos), google_maps (with `ll=@12.97,77.59,14z`, then reviews, photos, directions), google_local, tripadvisor (`tripadvisor_domain=www.tripadvisor.in`, ssrc=r/A/h, then place and reviews). Avoid Yelp (no India domain) and OpenTable (India coverage unverified).
  - *Commerce & price comparison:* google_shopping (`gl=in`, `google_domain=google.co.in`), google_shopping_filters, google_immersive_product (multi-seller prices), amazon and amazon_product (`amazon_domain=amazon.in`, delivery_zip with an Indian PIN code is unverified), google_lens (visual product search), google_play and apple_app_store for app comparison. Walmart, eBay and Home Depot are US-centric.
  - *Knowledge / education / jobs / news:* google_jobs (`location="Bengaluru, Karnataka, India"`, `gl=in`), google_news (gl=in, hl=en/hi, topic tokens), google_scholar (and author/cite), google_patents (`country=IN`), google_trends (`geo=IN`) and trending_now, google_finance (`NSE:`/`BOM:` tickers), youtube (and transcript).
- Google Events is deprecated, so a hackathon event-finder should use `google` with q like "events in Bengaluru" and read `events_results`.

### Gaps
- Not verified: whether `google_local_services` (Local Services Ads) is available in India; OpenTable India coverage; Amazon `delivery_zip` support for Indian PIN codes; whether `google_jobs` returns full India results for every city (Google Jobs is generally available in India, but no SerpApi doc states this).

## Which engines are new in 2025-2026?

### Takeaway
2026 brought many AI-answer and vertical engines, plus Markdown output for LLMs.
- New engines: Brave AI Mode, Google Ads, Google Scholar Case Law, Tripadvisor Reviews, Apple Maps and Apple Maps Places, Instagram Profile, Google Hotels Photos, Google Flights Deals, Google Sports, Amazon Autocomplete, Zillow, YouTube Channel, eBay Seller.
- New blocks inside existing engines: Bing Copilot answer, Baidu AI overview, DuckDuckGo Search Assist, Naver dictionary, Google flight result, Transport Options, Bing events.
- Features: AI Mode `reconstructed_markdown` and `image_url`, Lens image upload, Markdown output, Pixel Position GA.
- Deprecations: Google Events (Aug 2026), Google Product (replaced by Immersive Product), Yahoo Shopping, most Jobs Listing fields, the News Light `site:` operator.

### Cited Findings
- 2026 timeline from the weekly changelogs:
  - Jan: eBay review highlights
  - Feb: DuckDuckGo Search Assist, Google Hotels Photos API, AI Mode `reconstructed_markdown`
  - Mar: Google Search lat/lon, Naver Dictionary, Tripadvisor Reviews API, Brave AI Mode API
  - Apr: Postman collection with 113 endpoints, Google Maps vacation rentals/hotels/neighborhoods, Google Scholar Case Law API, AI Mode `image_url`, Baidu AI Overview, Google Flight Result
  - Apr/May: Apple Maps API
  - May: Bing Copilot Answer, Apple Maps Places API, Instagram Profile API, Google Ads API, ISO 27001
  - Jun: Google AI Flight Deals, Pixel Position GA, Java/Swift/C++ libraries, UULE converter
  - Jul: flight-number booking pinning, Google Sports API, Transport Options answer box, Amazon Autocomplete API
  - Aug: Lens `image_id` upload, Markdown Output, .NET library, Zillow Search API, Google Events deprecated
  - Sep: Bing Events Results, YouTube Channel API, News Light `site:` dropped, KG products/booking options, eBay Seller API
  - Sources: [Jan 19-Feb 01](https://serpapi.com/blog/serpapi-weekly-changelog-january-19-february-01-2026/), [Feb 02-08](https://serpapi.com/blog/serpapi-weekly-changelog-february-02-08-2026/), [Feb 09-15](https://serpapi.com/blog/serpapi-weekly-changelog-february-09-15-2026/), [Mar 23-29](https://serpapi.com/blog/serpapi-weekly-changelog-march-23-29-2026/), [Mar 30-Apr 05](https://serpapi.com/blog/serpapi-weekly-changelog-march-30-april-05-2026/), [Apr 13-19](https://serpapi.com/blog/serpapi-weekly-changelog-april-13-19-2026/), [Apr 27-May 03](https://serpapi.com/blog/serpapi-weekly-changelog-april-27-may-03-2026/), [May 04-10](https://serpapi.com/blog/serpapi-weekly-changelog-may-04-10-2026/), [May 18-24](https://serpapi.com/blog/serpapi-weekly-changelog-may-18-24-2026/), [May 25-31](https://serpapi.com/blog/serpapi-weekly-changelog-may-25-31-2026/), [Jul 06-12](https://serpapi.com/blog/serpapi-weekly-changelog-july-06-12-2026/), [Aug 17-23](https://serpapi.com/blog/serpapi-weekly-changelog-august-17-23-2026/), [Aug 24-30](https://serpapi.com/blog/serpapi-weekly-changelog-august-24-30-2026/), [Sep 21-27](https://serpapi.com/blog/serpapi-weekly-changelog-sep-21-27-2026.md)
- Google `/goto` redirect links (Aug 2026) briefly affected `link` fields. SerpApi says direct URLs were restored by early Sep 2026. — [Changelog Aug 31-Sep 06](https://serpapi.com/blog/serpapi-weekly-changelog-aug-31-sep-06-2026/)
- Official libraries now cover Ruby, Python, JavaScript, Golang, PHP, Java, Rust, .NET, Swift, C++ and a CLI, plus MCP support — [llms.txt](https://serpapi.com/llms.txt)

### Inferences
- Google AI Overview, AI Mode and Google Lens predate 2026, since 2026 changelogs only add features to them. Their exact 2025 launch dates were not checked.

### Gaps
- 2025 changelogs were not reviewed, so 2025 launch dates (for example AI Mode, Immersive Product, Light engines) are unconfirmed.
