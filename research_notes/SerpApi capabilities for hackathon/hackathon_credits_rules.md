# SerpApi India Hackathon 2026: credits during the event, and key rules

Researched 2026-10-05. Primary sources: the live hackathon site (index, rules.html, terms.html, submit.html, plus its `hackathon-config.js` and `submission-app.js`, downloaded and grepped in full), the SerpApi blog announcement (updated 2026-09-27), the SerpApi pricing page and community partner event pages. The GitHub repo `serpapi/serpapi-india-hackathon-2026` could not be cloned (it asked for auth, so it is private or not at that path). The deployed JS was inspected instead. `faq.html` and `resources.html` return 404. The FAQ and Resources are sections on the index page.

## Q1: Do the site's rules, terms, FAQ or submit pages offer extra or free credits during the hackathon (boosts, coupon codes, someone to contact)?

### Takeaway
No. Across every page of the hackathon site and its config/JS, the only credit available while you build is the standard free SerpApi account (250 searches/month). Every hackathon credit (1,000 per valid submission, plus award credits) is awarded after submission or judging. There is no coupon code, no credit boost and no "email X for more credits" instruction anywhere. adarsh@serpapi.com is listed only for hackathon/rules/website/submission questions.

### Cited Findings
- Getting-started step on the index page: "Create a free SerpApi account to get 250 search credits each month for building and testing your project." — [Hackathon site](https://serpapi.github.io/serpapi-india-hackathon-2026/)
- Blog: "Entry is free. You can create a free SerpApi account for 250 search credits each month to build and test your project." — [SerpApi blog announcement](https://serpapi.com/blog/introducing-the-serpapi-india-hackathon-2026/)
- Contact section, exact wording: "Hackathon support — For questions about the hackathon or rules, or to report issues with the hackathon website or submissions, contact: adarsh@serpapi.com". "SerpApi support — For general SerpApi questions, help with APIs, or unexpected API errors, contact: contact@serpapi.com". Neither mentions credit requests. — [Hackathon site](https://serpapi.github.io/serpapi-india-hackathon-2026/)
- Terms §10: "Questions about these Terms & Conditions may be sent to support@serpapi.com. Submission-specific support channels may be announced before the Hackathon begins." — [Terms](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html)
- The site's `hackathon-config.js` defines credits only for the award tiers (15,000 / 10,000 / 10,000 / 10,000 track / 5,000 community / 1,000 "Submission Credits") with `creditsPerUsd: 100`. It has no coupon or promo field. `submission-app.js` has no credit/coupon/promo strings. — [hackathon-config.js](https://serpapi.github.io/serpapi-india-hackathon-2026/hackathon-config.js), [submission-app.js](https://serpapi.github.io/serpapi-india-hackathon-2026/submission-app.js)
- The submit form collects no SerpApi account ID or API key. Its only optional opt-in is "Email me about future SerpApi hackathons and competitions." — [Submit page](https://serpapi.github.io/serpapi-india-hackathon-2026/submit.html)
- Pricing page: free plan = 250 searches/month, 50 throughput/hour. There is no mention of student, hackathon or open-source credits, or of how to request extra free searches. — [SerpApi pricing](https://serpapi.com/pricing)
- Community partners have no credit-distribution role. Terms §2: "Community partners are not responsible for administering the Hackathon, judging projects, paying awards, or making eligibility decisions unless SerpApi expressly states otherwise in writing." — [Terms](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html)

### Inferences
- Officially, there are no extra in-hackathon credits. A participant who runs out of the 250 free searches could politely email adarsh@serpapi.com to ask. That is an unadvertised ask with no documented entitlement. Practical alternatives: cache responses, test against saved JSON or the Playground, or use teammates' separate free accounts (each person's own account. Do not abuse this: "abuse of SerpApi services" is a disqualification reason).

### Gaps
- No public statement says SerpApi will or will not top up credits on request. Private repo source and any Discord/WhatsApp channels were not accessible.

## Q2: Has SerpApi or a community partner said anything elsewhere (blog, social media, Luma/Meetup) about extra credits for participants?

### Takeaway
No. The blog post, the HydPy Meetup event and the search results all repeat the same structure: 250 free searches/month to build, 1,000 credits per valid submission, plus award credits. The only "free SerpApi credits" giveaway found online is unrelated: a third-party (Apives) code from April 2026, limited to the first 30 people.

### Cited Findings
- The SerpApi blog has one hackathon-tagged post, the announcement (published 2026-09-22, updated 2026-09-27, author Adarsh Divakaran). It has no extra-credit or coupon mention. — [Blog hackathon tag](https://serpapi.com/blog/tag/hackathon/), [Blog .md](https://serpapi.com/blog/introducing-the-serpapi-india-hackathon-2026.md)
- HydPy Meetup event: "HydPy × SerpApi India Hackathon 2026 - Community Collaboration" (Tue, Sep 22, 7:00 PM IST). It says: "The best community submission receives ₹10,000 in cash plus additional SerpApi credits"; all valid submissions get "1,000 SerpApi credits"; "Sign up for free; no credit card required." It lists the deadline as "Submit before October 5, 2026", which is stale (see Q4). — [HydPy Meetup](https://www.meetup.com/hydpygroup/)
- BangPypers' import_bengaluru (Sep 6, 2026, Luma) does not mention SerpApi, the hackathon or credits. — [Luma event](https://luma.com/5v2wfu9f)
- Unrelated giveaway: Apives.com (Sumit Raghuwanshi, April 12, 2026) offered 500 free credits to the first 30 people who email contact@serpapi.com with code "Apives500". It is not a SerpApi or hackathon offer, and the first-30 limit makes it almost certainly exhausted. — [Indie Hackers post](https://www.indiehackers.com/post/giveaway-500-free-serpapi-credits-for-the-first-30-builders-a5a74b4ba4)
- A web-search snippet mentioned "SerpApi credits valued up to USD 75 as redeemable perks during the hackathon". That is from other SerpApi-sponsored events (AI Tinkerers Paris hackathons), not the India hackathon. — [AI Tinkerers Paris](https://paris.aitinkerers.org/p/ai-hackathon-real-time-search-powered-by-serpapi-hybrid)

### Inferences
- SerpApi has given upfront credits at other (in-person, sponsored) hackathons, but chose not to do so for this online India event. The only participation credits are the post-submission 1,000.

### Gaps
- I could not search X/Twitter or LinkedIn post contents directly. The LinkedIn company page appeared in results but its post content was not retrievable. The PyDelhi, TriPy and AI Geeks Chennai event pages did not surface in search.

## Q3: When and how are prize and participation credits delivered?

### Takeaway
After judging. Delivery depends on winner/eligibility verification, and SerpApi may adjust the timing. The judging and winner-announcement date is still "To be announced" as of Oct 5. The site does not describe the delivery mechanism. Presumably the credits are added to the participant's SerpApi account, since credits are "subject to SerpApi account and service terms".

### Cited Findings
- Timeline: "Judging and winner-announcement dates will appear here when announced." Card: "DATE TO BE ANNOUNCED — Judging and winners — Eligible submissions are reviewed against the published criteria. Winner-announcement details will follow." In config, `resultsAt: null`. — [Hackathon site](https://serpapi.github.io/serpapi-india-hackathon-2026/), [hackathon-config.js](https://serpapi.github.io/serpapi-india-hackathon-2026/hackathon-config.js)
- Terms §2: "Judging and winner-announcement dates will be announced on the Hackathon website." — [Terms](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html)
- Terms §6: "Before fulfillment, a potential winner must provide requested identity, residency, age, banking, tax, account, and compliance information within the time specified by SerpApi. Failure to respond or complete verification may result in forfeiture or reassignment." — [Terms](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html)
- Terms §6: "Search credits have no cash value, are non-transferable unless SerpApi approves otherwise, may expire, and remain subject to SerpApi account and service terms." SerpApi may "adjust fulfillment timing". — [Terms](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html)
- Terms §6: "For team submissions, award fulfillment arrangements will be confirmed during winner verification." — [Terms](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html)
- Rules §7: "Credit values use 100 credits per US dollar of usage and are not cash equivalents." 1,000 credits = US$10 usage value. "The 1,000 valid-submission credits are a participation benefit and may be received in addition to a competitive award." — [Rules](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html)
- Prize table (Rules §7): 1st ₹1,00,000 + 15,000 credits; 2nd ₹40,000 + 10,000; 3rd ₹20,000 + 10,000; best in each of 6 tracks 10,000; best from each of 5 partner communities ₹10,000 + 5,000; each valid submission 1,000. The pool is ₹2,10,000 cash + 120,000 credits, plus participation credits. — [Rules](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html)

### Inferences
- Credits are tied to the account and "non-transferable". Use the same email for your SerpApi account and the submission's lead-participant email to avoid matching problems. This is advice, not a stated rule.
- Participation credits arrive only after the submission is judged "valid", which is after Oct 10. They cannot help you build during the hackathon.

### Gaps
- No stated mechanism (automatic top-up vs. a form), no delivery date and no expiry period for the credits.

## Q4: Key rules a participant must not miss

### Takeaway
Deadline: **Oct 10, 2026, 23:59 IST**. Drafts are never auto-submitted, so you must click "Submit project". You need a public GitHub repo, a demo of the project running locally that is under 3 minutes and opens in incognito, and meaningful (not cosmetic) SerpApi usage. You must disclose pre-existing projects and AI tools. Never put API keys in the public repo. One competitive award per project. A team can have at most 5 members, all resident in India and 18+.

### Cited Findings
- **Dates:** "September 1, 2026 at 00:00 IST through October 10, 2026 at 23:59 IST." — [Rules](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html). Conflict: the HydPy Meetup page and some search snippets of an earlier blog version say "October 5, 2026". The current blog (updated Sep 27) and site both say Oct 10. — [HydPy Meetup](https://www.meetup.com/hydpygroup/); [Blog](https://serpapi.com/blog/introducing-the-serpapi-india-hackathon-2026/)
- **Eligibility:** "open only to individuals who reside in India. Each participant must be at least 18 years old"; "team of no more than five people"; "Every listed team member must satisfy the eligibility requirements and must have contributed to the project." SerpApi employees, contractors, affiliates and their family/household are not eligible. ID, age, residency, tax and payment information may be requested. — [Rules §2](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html). The blog's table says "Indian citizens aged 18 or older", but its body text and the Rules say "reside in India". The Rules/Terms control. — [Blog](https://serpapi.com/blog/introducing-the-serpapi-india-hackathon-2026.md)
- **Meaningful usage:** "Adding an isolated or cosmetic API call solely to meet eligibility requirements is insufficient," decided "in its sole discretion." — [Rules §3](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html)
- **Existing projects:** allowed "when the submitted version demonstrates meaningful SerpApi usage and the relevant work can be identified and reviewed. Participants must disclose that the project existed before the hackathon." — [Rules §3](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html)
- **Tracks:** pick one (AI Agents, Open-Source Integrations, Travel & Local Discovery, Commerce & Market Intelligence, Knowledge & Public Interest, Open Innovation). SerpApi may move a project to another track. — [Rules §3](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html)
- **IP:** "the participant retains ownership of the participant's original project materials". The participant grants SerpApi a "worldwide, non-exclusive, royalty-free" licence that is "perpetual, irrevocable, and sublicensable" for judging/promotion, covering name, likeness and voice in the demo. An open-source licence is "encouraged but not required". SerpApi may build similar features with no obligation. — [Terms §4](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html)
- **Submission contents:** GitHub sign-in; public repo with docs and setup instructions; an explanation of which SerpApi products are used and why; lead's name, email, mobile, occupation and years of experience; teammates' names and emails (max 4 additional); track; whether the project pre-existed; how you heard about the event (community source); demo link; AI tools; acceptance of Rules and T&C. — [Rules §4](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html)
- **Drafts and limits:** up to 3 active projects per account. "Drafts are not submitted automatically". "SerpApi will not review, judge, or award a project that remains in draft status when submissions close." Editing after submitting keeps the original timestamp. — [Rules §4](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html), [Terms §4](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html)
- **Video:** "screen recording under three minutes that shows the project running locally and its core functionality working. The link must open in an incognito or private window." Narration is optional, and the video may be sped up. Production quality does not affect judging. — [Rules §4](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html)
- **Valid submission:** "timely, complete, accessible, eligible, non-deceptive, and demonstrates meaningful SerpApi usage. Unfinished, spam, copied, inaccessible, or materially non-functional entries may be rejected." — [Rules §4](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html)
- **AI disclosure:** allowed. "Participants must briefly name any AI tools used and describe how they contributed". "AI use does not affect judging." The participant stays responsible for licensing, originality and secrets. — [Rules §5](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html)
- **Judging:** unweighted: idea strength, originality, technical complexity, usefulness, meaningful SerpApi usage. Judges may review repo history and request a functionality check. Decisions are "final and not subject to appeal". Automated pre-screening may be followed by manual review (Terms §5). Judges: Adarsh Divakaran, Tomas Murua, Josef Strzibny, Pranav Kafle. — [Rules §6](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html), [Site](https://serpapi.github.io/serpapi-india-hackathon-2026/)
- **One award:** "A project may receive only one competitive award. Overall first, second, and third places are assigned first. Best-in-track awards and then community awards are assigned to the next highest-ranked eligible projects." — [Rules §7](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html)
- **Disqualification:** false eligibility/authorship/team/community/functionality claims; plagiarism or infringement; "Manipulating submission, repository, community, or judging signals"; harassment; malware or "abuse of SerpApi services"; "Exposure of API keys, personal data, or other secrets in public materials." — [Rules §8](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html). Also: failure to cooperate with verification, security risks. — [Terms §10](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html)
- **Legal:** Texas law, individual arbitration after 30 days of informal resolution, class-action waiver. Liability is capped at the value of the award received. Indemnification applies. The Terms override the Rules in case of conflict. — [Terms §9–10](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html)
- **Changes:** SerpApi may modify, extend or cancel the hackathon. "Continued participation after an update constitutes acceptance of the updated terms." Rules/terms version is "2026-09-01". — [Terms §7](https://serpapi.github.io/serpapi-india-hackathon-2026/terms.html), [hackathon-config.js](https://serpapi.github.io/serpapi-india-hackathon-2026/hackathon-config.js)

### Inferences
- Must-not-miss checklist: (1) submit, don't leave it as a draft, by Oct 10 23:59 IST; (2) check the video and repo links in incognito; (3) keep `SERPAPI_API_KEY` in env/.env and out of git history (judges read repo history); (4) tick "existed before hackathon" if it applies; (5) make SerpApi central to the core feature; (6) pick the correct community source, since that decides eligibility for the community award; (7) list AI tools honestly.

### Gaps
- Judging/announcement date is unpublished. The repo source code is not publicly accessible.
