# Transaction data sources for cc-smith — legal/policy viability (read 2026-10-07)

Scope: ways a **non-bank, non-RBI-regulated** startup (Flutter iOS + Android, Python backend) can pull a user's credit-card transactions in India. Every claim below is tagged with the source URL and the date it was read (all read 2026-10-07 unless stated). Anything not confirmed from a primary source is marked **UNCONFIRMED**. Secondary sources (vendor blogs, community forums) are marked **(secondary)**.

Method note: WebSearch + WebFetch only. Several primary pages are JavaScript-rendered and returned only a title to the fetcher (Apple FinanceKit / FinanceStore docs, Apple Message Filter docs, Sahamati's FIP activation table, Android `NotificationListenerService` class overview). Those are listed under "Things to verify by hand".

---

## Summary verdict table

| # | Source | Android | iOS | Verdict | Prerequisite | Effort / cost | Key citation |
|---|---|---|---|---|---|---|---|
| 1a | Account Aggregator — cc-smith as direct FIU | n/a | n/a | **NO-GO** | Must be "registered with and regulated by" RBI/SEBI/IRDAI/PFRDA/DoR | Would require getting a financial-sector licence | RBI MD NBFC-AA §3(1) FIU definition; Sahamati FAQ: "No, you cannot be an FIU or FIP if you are not a regulated entity." |
| 1b | AA via a TSP (Finvu/Setu/Perfios/MoneyOne) | n/a | n/a | **NO-GO on its own** | TSP only builds/runs the FIU module *for a regulated entity*; "Only regulated FIUs can receive consented encrypted information from the AA" | — | Sahamati FAQ; Sahamati TSP page |
| 1c | AA via a partnered regulated FIU (bank/NBFC/RIA acts as FIU, cc-smith is its vendor) | n/a | n/a | **CONDITIONAL, and useless for card spends today** | A regulated partner that owns the use case and consent; FIU→unregulated-partner data sharing not addressed in Sahamati FAQ (legal grey) | Partner negotiation; Sahamati RE fee ₹25k–₹5L/yr (paid by the RE); TSP per-fetch pricing (secondary: ~₹2.5–6) ; first-year ₹5–25L (secondary vendor estimate) | Sahamati FI-types page (Dec 15, 2024): **no Credit Card FI type**; Fold & Mojek help docs: "Credit card data is not part of the Account Aggregator framework" |
| 2a | Android `NotificationListenerService` (issuer-app + SMS-app notifications) | Yes | No | **CONDITIONAL GO** | User enables in Settings "Notification access"; prominent in-app disclosure + consent; Data safety declaration; on-device parsing, minimal retention | Low engineering; no Play declaration form found for this API (as of 2026-10-07) | Play "Permissions and APIs that Access Sensitive Information" policy does not list notification access; Play "User Data" policy governs |
| 2b | Android `READ_SMS` / `RECEIVE_SMS` (non-default SMS app) | Yes | No | **CONDITIONAL / LOW PROBABILITY** | Not default handler → only via "temporary exception"; table does list "SMS-based money management — e.g., apps that track and manage budget" and "SMS-based financial transactions"; Permissions Declaration Form + video; Google may refuse | Review cycle per release; risk of removal | Play "Use of SMS or Call Log permission groups" (answer/9047303) |
| 3a | Gmail API `gmail.readonly` (transaction alert + statement emails) | Yes | Yes | **CONDITIONAL GO (recommended primary)** | Restricted scope → OAuth app verification (~6 weeks est.) + annual CASA security assessment (AL1/AL2, LOV); Limited Use compliance; 100-lifetime-user cap until verified | Google charges nothing; assessor fees: TAC Security Tier 2 $540–$1,800/app (secondary), other labs $800–$1,500+ (secondary); 1–4 weeks assessment | Gmail scopes page (2026-09-10); Google OAuth verification FAQ; Google User Data Policy (2024-02-15) |
| 3b | `gmail.metadata` / Gmail Add-on scopes | Yes | Yes | **NO-GO (not fit for purpose)** | `gmail.metadata` is also *restricted* and excludes the body; add-on scopes are "sensitive" but only work while the add-on is open in Gmail | — | Gmail scopes page (2026-09-10) |
| 3c | Microsoft Graph `Mail.Read` (Outlook.com / M365) | Yes | Yes | **GO (secondary channel)** | Delegated `Mail.Read`: AdminConsentRequired = No, personal MSA supported; publisher verification is free (Partner Center ID + verified domain); no security assessment | Low | MS Graph permissions reference (updated 2026-06-15); Publisher verification overview (2026-06-15) |
| 4a | iOS FinanceKit | No | Yes (US only) | **NO-GO for India** | Exposes Apple Card / Apple Cash / Savings only; Apple Card is US-only; entitlement request page is behind Apple ID sign-in | — | MacStories (2024-03-06) + Apple Newsroom; Apple docs page not machine-readable (UNCONFIRMED verbatim) |
| 4b | iOS SMS / notifications / Mail app | — | No | **NO-GO** | No public API; Message Filter extension only classifies SMS from unknown senders (Apple docs not fetchable — UNCONFIRMED verbatim) | — | — |
| 4c | iOS: email OAuth (3a/3c), PDF upload (5), IMAP app-password | — | Yes | **GO** (OAuth, PDF); IMAP app-password **CONDITIONAL** | Same as 3a/3c; App Store 5.1.1(ix) says regulated-field / sensitive-data apps must be submitted by a legal entity; 3.2.1(viii) money-management clause is a review risk | — | App Store Review Guidelines (read 2026-10-07) |
| 5 | Statement PDF upload (share sheet / file picker) | Yes | Yes | **GO** | Password-protected PDFs are the norm (bank-specific formats); never persist full PAN; store last-4 + issuer only; DPDP consent/notice | Parser per issuer; moderate ongoing maintenance | RBI CoFT circular 2021-09-07 (last-4 + issuer name permitted); PCI SSC FAQ on truncated PAN; Cleartax/Adobe password formats (secondary) |
| 6 | Bank/issuer partnership (co-brand or API) | Yes | Yes | **NOT AVAILABLE to a startup at v1** | Issuer agreement; RBI Credit Card MD para 21(b)/28 constrain what partners may see/store | High | RBI MD Credit/Debit Card 2022 (updated 2024-03-07) |

---

## 1. Account Aggregator (AA) framework

### 1.1 Can a non-regulated fintech be an FIU? — NO

Primary: RBI, *Master Direction – Non-Banking Financial Company – Account Aggregator (Reserve Bank) Directions, 2016* (issued 2016-09-02, last updated 2024-09-06), https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=10598 (read 2026-10-07):

> "Financial Information User" means "an entity registered with and regulated by any financial sector regulator".
> "Financial Sector Regulator" means "the Reserve Bank of India, Securities and Exchange Board of India, Insurance Regulatory and Development Authority, Pension Fund Regulatory and Development Authority and Department of Revenue".

Sahamati FAQ, https://sahamati.org.in/faq/ (read 2026-10-07):

> Q: "We are a Fintech startup not regulated by any of the regulators, but we have an excellent Use Case for our consumers which require the usage of AA. Can we be an FIU?"
> A: "No, you cannot be an FIU or FIP if you are not a regulated entity."
> "Only regulated FIUs can receive consented encrypted information from the AA. The information will be decrypted at the FIU's end."

Sahamati "How to join", https://sahamati.org.in/how-to-join-the-account-aggregator-network-to-share-and-access-financial-data/ (read 2026-10-07): "Currently, only players who are registered and regulated by either of the four Financial Service Regulators (FSR)– RBI, SEBI, IRDAI, PFRDA, are allowed to be FIPs and FIUs."

Sahamati FIU page, https://sahamati.org.in/financial-information-user-fiu (read 2026-10-07): step 1 of onboarding is "Get registered and regulated by at least one of the Financial Service Regulators (FSR), namely — RBI, SEBI, IRDAI, PFRDA." It also states: "As per the RBI directive, every entity needs to be a FIP first and then an FIU to ensure the sustainability of the ecosystem." (data reciprocity).

2024–2026 changes checked:
- The 2024-09-06 MD amendment did **not** change the FIU definition; it concerned NBFC-AA base-layer classification, ombudsman scheme, director experience, risk committee, disclosures (secondary summary: https://lexplosion.in/rbi-amends-master-direction-non-banking-financial-company-account-aggregator-effective-immediately, read 2026-10-07).
- RBI recognised Sahamati as the SRO for the AA ecosystem on 2026-06-05 (Sahamati media article https://sahamati.org.in/media-article/rbi-sro-recognition-account-aggregator-ecosystem/, read 2026-10-07 via search snippet; **UNCONFIRMED from the article body**). No relaxation of the regulated-entity rule was found.
- The "FIU must be regulated by a financial sector regulator" rule is therefore not a 2024–26 novelty; it has been in the MD since 2016 and is actively enforced via Sahamati onboarding.

### 1.2 TSP route — NO on its own

Sahamati TSP page, https://sahamati.org.in/tsp/fip-fiu-tsp/ (read 2026-10-07, via search summary): TSPs "operate as the sole unregulated entity in the AA-enabled data sharing process" and "a TSP is not required to have an NBFC-AA license", but they build/operate the FIU or FIP module *on behalf of a regulated entity*; the regulated entity remains the licensed participant. Combined with the FAQ line that "Only regulated FIUs can receive consented encrypted information", a TSP cannot lend cc-smith its own access.

Setu go-live docs, https://docs.setu.co/data/account-aggregator/licenses-and-go-live/go-live (read 2026-10-07): requires a "regulated and licensed entity to become an FIU in the AA ecosystem"; licence proof is "To be shared with Sahamati to establish eligibility to become an FIU."

### 1.3 Partner with a regulated FIU — CONDITIONAL (legal grey)

Secondary sources describe the pattern "partner with a regulated entity that acts as the FIU on your behalf" (CASParser, March 2026, https://casparser.in/blog/state-of-account-aggregator-2026/; ecorpit, 2026-07-17, https://ecorpit.com/account-aggregator-integration-fintech-builders-2026/). The Sahamati FAQ has **no** Q&A permitting an FIU to pass decrypted AA data to an unregulated partner; the FIU is the "data fiduciary" and consent is tied to its use case. Treat this as requiring: (a) the partner to own the consent purpose, (b) cc-smith to act as the partner's outsourced service provider under its data-use terms, (c) legal review. **UNCONFIRMED** that Sahamati/RBI would accept cc-smith's advisory use case as the partner's "use case aligned with your license charter" (Sahamati RE membership criterion).

### 1.4 Does AA cover credit-card transactions? — NO (today)

Sahamati "Data (FI) types available on AA", https://sahamati.org.in/data-fi-types-available-on-aa/ (page last updated 2024-12-15; read 2026-10-07): 17 live FI types — Deposit, Recurring Deposit, Term Deposit, SIP, Equity Shares, Mutual Fund Units, ETF, IDR, CIS, AIF, InvIT, REIT, GSTR, General Insurance, Life Insurance, Insurance Policies, NPS. Proposed: Commercial Paper, Certificates of Deposit, Government Securities, Bonds, Debentures, EPF, PPF. **"Credit Card" does not appear** in either list.

RBI MD §3(1)(ix) "financial information" list (read 2026-10-07): bank deposits, NBFC deposits, SIP, CP, CD, G-Sec, equity, bonds, debentures, MF units, ETF, IDR, CIS, AIF, insurance policies, NPS balances, InvIT/REIT units, GSTR-1/3B, "Any other information as may be specified by the Bank". No credit-card category.

Operators confirm it:
- Fold help, https://help.fold.money/hc/en-us/articles/17257827045138-How-do-you-fetch-my-credit-card-related-data (read 2026-10-07): "Credit card data is not part of the Account Aggregator framework", hence their Gmail-based solution.
- Mojek help, https://mojekmoney.help.center/article/1079-how-do-you-fetch-my-credit-card-related-data (read 2026-10-07): same sentence verbatim.

The Sahamati "Account types activated by banks on AAs" table (https://sahamati.org.in/account-types-activated-by-banks-on-aas/) is JS-rendered and could not be read; the page text says banks are live on "Savings Accounts held by a single person, and some of the Banks are also live on Sole Proprietor Current Accounts". No bank is documented as serving a credit-card FI type. Searches for a "CREDIT_CARD" ReBIT schema found none.

What AA *could* give cc-smith via a regulated partner: savings/current-account deposit data (useful for detecting credit-card bill payments and cash-flow, not for card-level spends).

### 1.5 Costs (published)

- Sahamati RE membership (paid by the regulated member), https://sahamati.org.in/benefits-fees-of-re-members/ (read 2026-10-07): Category A ₹5 lakh/yr, B ₹1.25 lakh/yr, C ₹25,000/yr, by entity size; "All NBFC-AAs shall be classified under Fee Category B."
- TSP/AA pricing **(secondary)**: Finvu "₹3–₹6 per account and ~₹2.50 per fetch" (productgrowth.in via search, read 2026-10-07); Setu support says FIP data-fetch charges "have not yet been determined by Sahamati" while FIUs are charged per statement pulled (read 2026-10-07 via search summary).
- CASParser **(secondary, vendor)**: "total first-year cost at ₹5-25 lakhs or more, depending on scope", "5 to 10 months".

**Verdict:** Direct FIU — NO-GO. TSP — NO-GO. Regulated partner — CONDITIONAL, and in any case does not yield credit-card transactions because no credit-card FI type exists as of the latest Sahamati list (Dec 2024) or any 2025–26 announcement found.

---

## 2. Android: notification listener and SMS

### 2.1 `NotificationListenerService` — CONDITIONAL GO

How it works (Android reference, https://developer.android.com/reference/android/service/notification/NotificationListenerService, read 2026-10-07; class overview is in a 337k-char page and only the manifest requirement was extractable): the service must be declared with `android.permission.BIND_NOTIFICATION_LISTENER_SERVICE` and the `SERVICE_INTERFACE` intent filter; the user turns it on in Settings > Notification access (special-access screen with a system warning). It receives the text of every posted notification, including issuer-app pushes ("Rs 1,234 spent on HDFC Card ending 1234 at …") and the SMS app's own notifications of bank SMS.

Google Play policy status (all read 2026-10-07):
- "Permissions and APIs that Access Sensitive Information", https://support.google.com/googleplay/android-developer/answer/9888170 — covers SMS/Call Log, location, Accessibility, VPN, QUERY_ALL_PACKAGES, etc. **It does not mention notification access / NotificationListenerService**, and no Play Console declaration form for it was found. Its general rule still applies: "You may only request permissions and APIs that access sensitive information that are necessary to implement current features or services in your app that are promoted in your Google Play listing"; such data "may never be sold nor shared for a purpose facilitating sale".
- The two "preview" versions (answer/16558241, answer/16909972, effective 2027-01-27) add Location and Contacts rules; still no notification-listener rule.
- "User Data" policy, https://support.google.com/googleplay/android-developer/answer/10144311 — personal and sensitive user data explicitly includes "financial and payment information … SMS and call-related data"; background/unexpected collection requires **prominent in-app disclosure** ("displayed in the normal usage of the app and not require the user to navigate into a menu or settings") and affirmative consent before collection; Data safety section must be accurate.

Risks to document in the design:
1. Reading the SMS app's notifications is functionally SMS reading without `READ_SMS`. Play has not written a rule against it as of this reading, but it could be treated as circumventing the SMS policy; keep the feature honestly described ("reads transaction alert notifications") and keep parsing on-device.
2. OEM battery managers kill listener services; coverage is best-effort.
3. Android 13+ "restricted settings" block some special-access settings for apps not installed from an app store; Google's help page (https://support.google.com/android/answer/12623953, read 2026-10-07) names only accessibility as an example — whether notification access is included is **UNCONFIRMED**. Irrelevant for Play-installed builds.
4. Issuer pushes vary per bank and are only present if the user has the issuer app installed with notifications on.

**Verdict:** CONDITIONAL GO — ship with prominent disclosure + consent, on-device extraction, store only derived fields (amount, merchant, last-4, timestamp), declare "Financial info" in Data safety, and keep a kill switch in case Play policy changes.

### 2.2 `READ_SMS` / `RECEIVE_SMS` for a non-default SMS app — CONDITIONAL, low probability

"Use of SMS or Call Log permission groups", https://support.google.com/googleplay/android-developer/answer/9047303 (read 2026-10-07):

> Apps "must be actively registered as the default SMS, Phone, or Assistant handler before prompting users to accept any of SMS or Call Log permissions."
> "Google Play may provide a temporary exception to apps that aren't Default SMS, Phone, or Assistant handlers when: Use of the permission enables the core app functionality listed in the following table and there's currently no alternative method to provide the core functionality."

Rows in the exception table relevant to cc-smith (verbatim):
- **SMS-based financial transactions** — `READ_SMS, RECEIVE_MMS, RECEIVE_SMS, RECEIVE_WAP_PUSH, SEND_SMS` — "For example, Unified Payments Interface (UPI), verifications for financial transactions".
- **SMS-based money management** — `READ_SMS, RECEIVE_MMS, RECEIVE_SMS, RECEIVE_WAP_PUSH` — "For example, apps that track and manage budget".

Process: "you must declare any Call Log or SMS permissions directly through Google Play Console"; declaration requires a written core-feature justification and video; "Apps that fail to meet policy requirements or lack a Permissions Declaration Form may be removed from Google Play." Upcoming (effective 2027-01-27): `READ_CALL_LOG` for account verification is being removed (Digital Credentials API / SMS Retriever instead); the updated policy wording says apps must be "actively registered as the default SMS or Assistant handler" — the Phone handler drops out (read from answer/16909972 preview).

Realism: the "SMS-based money management" row means a budgeting app *can* apply, but it is a discretionary "temporary exception", re-reviewed on each release, and Google's position is that an alternative (notification listener, email, AA, manual) usually exists. Indian history: the Jan-2019 policy forced many fintech apps off SMS (secondary: https://inc42.com/buzz/google-play-policy-change-applications/, https://www.moneylife.in/article/google-restricts-apps-from-using-access-permission-via-sms-calls/56168.html, read 2026-10-07). Walnut continued SMS parsing (secondary: cardtrail.in, read 2026-10-07) — whether it held an approved exception is **UNCONFIRMED**.

**Verdict:** CONDITIONAL — only attempt after the product is live with a documented, prominent "SMS-based money management" core feature; expect refusal or revocation; never make it the sole data path.

---

## 3. Gmail API (and Outlook)

### 3.1 Scope classification (primary)

Gmail API scopes page, https://developers.google.com/workspace/gmail/api/auth/scopes (last updated 2026-09-10; read 2026-10-07):
- **Restricted:** `gmail.readonly`, `gmail.metadata` ("View your email message metadata such as labels and headers, but not the email body"), `gmail.modify`, `https://mail.google.com/`.
- **Sensitive:** `gmail.send`, `gmail.addons.current.message.readonly`, `gmail.addons.current.message.metadata`.
- **Non-sensitive:** `gmail.labels`, `gmail.addons.current.action.compose`, `gmail.addons.current.message.action`.
- Restricted scopes "require restricted scope OAuth App Verification" and a "security assessment" if such data is stored or transmitted on servers.

So there is **no narrower Gmail scope** that returns transaction-email bodies in the background: `gmail.metadata` is still restricted and omits the body; add-on scopes only run inside a Gmail add-on while the user has the message open (not a sync path). A "label-filtered" grant does not exist in Gmail OAuth.

### 3.2 Verification + CASA (primary)

- Restricted scope verification, https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification (updated 2026-08-19; read 2026-10-07): apps accessing restricted data "from or through a third-party server" must undergo assessment; "apps must be reverified for compliance and complete a security assessment at least every 12 months after your assessor's Letter of Assessment (LOA) approval date"; assessors are "Google-empanelled"; process "can potentially take several weeks".
- Security assessment page, https://support.google.com/cloud/answer/13465431 (read 2026-10-07): "applications requesting access to restricted scopes must undergo an annual security assessment"; CASA (App Defense Alliance, OWASP ASVS-based); "Applications are assigned to either the AL1 or AL2 assurance level" based on "user count, requested scopes, and other application-specific signals"; "All applications must be revalidated every year"; outcome is a "Letter of Validation (LOV)".
- OAuth verification FAQ, https://support.google.com/cloud/answer/13463817 (read 2026-10-07): "Google does not charge the developer any fees for security assessment" (assessors set their own fees); estimated durations — Brand 2–3 business days, Sensitive 10 business days, **Restricted "6 weeks"** ("not guaranteed"); "Unverified apps that are accessing restricted or sensitive scopes have a 100 new-user cap restriction" over the project's lifetime; training AI/ML on Google user data is prohibited.
- "When verification is not needed", https://support.google.com/cloud/answer/13464323 (read 2026-10-07): apps in testing are "subject to the unverified app screen and the 100-user cap … removed only after an app has been successfully verified."
- API Services User Data Policy, https://developers.google.com/terms/api-services-user-data-policy (updated 2024-02-15; read 2026-10-07) — Limited Use: "Limit your use of data to providing or improving user-facing features that are prominent in the requesting application's user interface"; transfers only for user-facing features with consent, security, legal, or M&A; human access only with user agreement/security/legal/aggregated ops; prohibited: transferring to advertisers or data brokers, **credit decisions**, serving ads. Applications "may require annual security assessments and Letters of Assessment".

Assessor pricing **(secondary; lab/vendor-published)**: TAC Security (Google-preferred lab) Tier 2 "$540 per App, with premium options up to $1,800", Tier 3 "$4,500 per app"; others Tier 2 $800–$1,500+; turnaround 1–4 weeks (https://www.switchlabs.dev/post/casa-tier-2-tier-3-security-review-providers-pricing-and-the-cheapest-option, dated 2024; TAC FAQ via search snippet; read 2026-10-07). Older Google guidance quoting $15k–$75k predates CASA and is obsolete (secondary).

Gmail "appropriate access" (which application types may use restricted scopes): Google's pages read today only say apps "can request access to sensitive or restricted scopes data only for appropriate use cases" and that "Approved app types often use APIs for productivity purposes" (https://support.google.com/cloud/answer/13464321). The specific Gmail allowed-app-type list could not be located verbatim — **UNCONFIRMED**; see "verify by hand". Precedent: CRED, Jupiter, Fold, Mojek all use Gmail for credit-card statement/alert parsing in India (section 6), so personal-finance tracking has been approved for restricted Gmail scopes in practice.

Can a startup get verified? Yes, by evidence: Jupiter's community post says users "will receive a verification prompt directly from Google when linking your email" (verified app); Mojek and Fold are small companies on Gmail restricted scopes (section 6). Requirements in practice: verified domain + homepage, privacy policy naming the scope use, demo video, per-scope justification, then CASA.

Design option that lowers assessment burden: Mojek states "only your transaction emails for the credit cards are processed locally on-device … Our servers don't get a whiff of any other emails" (read 2026-10-07). Whether on-device-only processing avoids the CASA requirement is **UNCONFIRMED** (Google's wording: assessment applies when restricted data is accessed "from or through a third-party server"). Even if it does, the backend will hold derived transactions, so plan for CASA anyway.

**Verdict:** CONDITIONAL GO, and the strongest cross-platform option. Budget: ~6 weeks verification + 1–4 weeks CASA, ~$540–$1,800/yr lab fee (secondary), annual re-validation, 100-user cap until done.

### 3.3 Microsoft Graph (Outlook.com / M365) — GO

- Permissions reference, https://learn.microsoft.com/en-us/graph/permissions-reference (updated 2026-06-15; read 2026-10-07): `Mail.Read` delegated — "Allows the app to read the signed-in user's mailbox", **AdminConsentRequired: No**, "available for consent in personal Microsoft accounts". `Mail.ReadBasic` delegated excludes body/attachments (not useful).
- Publisher verification, https://learn.microsoft.com/en-us/entra/identity-platform/publisher-verification-overview (ms.date 2024-08-13, updated 2026-06-15; read 2026-10-07): needs a verified Microsoft AI Cloud Partner Program (CPP) account with Partner One ID, app registered in a work/school tenant with a publisher domain; "Microsoft doesn't charge developers for publisher verification"; without it, since Nov 2020 users in tenants with risk-based step-up consent "can't consent to most newly registered multitenant apps that aren't publisher verified" (personal accounts still can). No CASA-style security assessment for Mail.Read.
- Caveat: Indian card-alert emails overwhelmingly land in Gmail; Outlook is a minority channel. Fold documents "Only Gmail is supported" (https://docs.fold.money/known-issues-with-credit-cards, read 2026-10-07).

---

## 4. iOS

What is **not** possible (platform facts; Apple pages are JS-rendered so verbatim quotes could not be fetched — see verify list):
- No notification-listener equivalent; no SMS read API. The Message Filter extension (IdentityLookup) classifies SMS from unknown senders and is sandboxed without general network access — it cannot forward message text to cc-smith (**UNCONFIRMED verbatim**).
- No Mail.app API. Apple Wallet exposes no third-party transaction API for bank cards.
- **FinanceKit**: exposes "Apple Card, Apple Cash, and Savings with Apple" transactions and balances (MacStories, 2024-03-06, https://www.macstories.net/linked/financekit-opens-real-time-apple-card-apple-cash-and-apple-savings-transaction-data-to-third-party-apps/, read 2026-10-07; launched iOS 17.4 with YNAB/Monarch/Copilot). Apple Card, Apple Cash and Savings are US-only (Apple Newsroom 2023-04-17 https://www.apple.com/newsroom/2023/04/apple-cards-new-high-yield-savings-account-is-now-available-offering-a-4-point-15-percent-apy/; MacRumors 2023-12-13 list of US-only features; read 2026-10-07). Entitlement request page https://developer.apple.com/contact/request/financekit/ redirects to Apple ID sign-in (read 2026-10-07). Apple Card India launch remains unannounced (2023 reports only). **Verdict: NO-GO for India; it would not expose HDFC/SBI/Axis cards even in the US.**

What **is** possible on iOS:
- Gmail / Outlook OAuth (sections 3.1–3.3) — identical backend; this is the primary iOS path.
- Statement PDF upload via share sheet / Files picker (section 5).
- IMAP with a Google "App password": requires the user to have 2-Step Verification and to generate a per-app password; it bypasses OAuth scopes. Google's FAQ (read 2026-10-07) states IMAP/SMTP access to Gmail "requires restricted scope verification" for OAuth clients; whether Google tolerates third-party apps collecting app-passwords at scale is **UNCONFIRMED** and a credential-handling liability. Treat as NO-GO for a consumer product.
- Manual entry / quick-add.

App Store Review Guidelines (https://developer.apple.com/app-store/review/guidelines/, read 2026-10-07):
- 5.1.1(ix): "Apps that provide services in highly regulated fields (such as banking and financial services …) or that require sensitive user information should be submitted by a legal entity that provides the services, and not by an individual developer." → submit from the company account.
- 3.2.1(viii): "Apps used for financial trading, investing, or money management should be submitted by the financial institution performing such services and must have necessary licensing and permissions in the locations where you make them available." → review risk for an advisor/tracker; CRED, CheQ, Fold etc. are listed, so advisory/tracking apps do pass, but have a licensing-position note ready ("no money movement, no lending; data aggregation with user consent").
- 5.1.1(ii)/(iii)/(iv): consent for data collection, data minimisation, no gating features on unrelated permissions. 5.1.2(i): no use/transfer of personal data without permission; ATT if tracking.

**Verdict:** iOS = email OAuth + PDF upload + manual. FinanceKit, SMS, notification capture: NO-GO.

---

## 5. Statement PDF upload

### 5.1 Are password-protected issuer PDFs the norm? — Yes (secondary sources)
- Adobe India guide (https://www.adobe.com/in/acrobat/roc/blog/credit-card-statement-password-guide, read 2026-10-07): ICICI, Axis, SBI and HDFC statements "always arrive password-protected"; each bank uses a format based on name / DOB / card digits.
- Cleartax (read 2026-10-07): HDFC = first 4 letters of name (caps) + last 4 digits of card (e.g., RAJE3456); Axis = first 4 letters of name + DDMM of DOB (alt: + 9-digit customer ID); SBI varies (DOB / mobile / card digits).
- Design consequence: ask the user for the password (or derive from profile fields with their permission), decrypt on-device, parse, and discard the original. Formats change; keep a per-issuer table and a fallback prompt.

### 5.2 Legal issues with parsing user-uploaded statements
- No RBI rule prohibits a user from sharing their own statement with an app of their choice. The RBI Credit Card MD (https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12300, updated 2024-03-07; read 2026-10-07) binds **card-issuers**: para 28 "Card-issuers shall not share card data (including transaction data) of the cardholders with the outsourcing partners unless sharing of such data is essential…explicit consent from the cardholder shall be obtained"; para 21(b) co-branding partners "shall not have access to information relating to transactions". These restrict issuer→partner flows, not cardholder→app flows. They matter only if cc-smith later becomes an issuer's outsourcing/co-brand partner.
- DPDP Act 2023 + DPDP Rules 2025: notified 2025-11-13/14; substantive obligations (consent notice, purpose limitation, erasure, breach reporting) take effect in phases — 2025-11-14, 2026-11-14 (consent-manager registration), **2027-05-14** (substantive provisions) (secondary law-firm summaries: Hogan Lovells, AZB, Shardul Amarchand; read 2026-10-07). Build consent-notice, purpose-bound processing and deletion from day one.
- If cc-smith ever acts as a lending service provider, the RBI Digital Lending Directions 2025 (2025-05-08) restrict apps from accessing phone resources (contacts, call logs, files) and allow one-time camera/mic/location for KYC only (secondary summaries; verbatim **UNCONFIRMED**). Not applicable to a pure advisor.

### 5.3 Storing card numbers — never store full PAN
- RBI, "Tokenisation – Card Transactions: Permitting Card-on-File Tokenisation (CoFT) Services", 2021-09-07, https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12159 (read 2026-10-07): "with effect from January 1, 2022, no entity in the card transaction / payment chain, other than the card issuers and / or card networks, shall store the actual card data"; for tracking/reconciliation entities may store "last four digits of actual card number and card issuer's name – in compliance with the applicable standards". Extension to 2022-06-30 and purge requirement: https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12211 (2021-12-23; read 2026-10-07). Addressed to "All Payment System Providers and Payment System Participants" — cc-smith is not in the payment chain, but adopting the same last-4 + issuer standard is the defensible position and matches what issuer statements already print (masked PAN).
- PCI DSS: PCI SSC FAQ (https://www.pcisecuritystandards.org/faqs/1117/ and the "Are truncated PANs required to be protected" FAQ; read 2026-10-07 via search summary): systems that only store/process truncated PANs (e.g., last 4 only, per FAQ 1091 formats) "may be considered out of scope for PCI DSS" if segmented and not otherwise handling cardholder data; the system performing truncation is in scope. cc-smith never sees full PAN if statements are masked; if an issuer statement prints a full PAN, redact at parse time and never persist the raw file.
- RBI Card MD para 21(b) shows the regulator's model for third-party display: data "visible only to the cardholder and shall neither be accessed nor be stored by the CBP" — a useful benchmark if a bank partnership is ever negotiated.

**Verdict:** GO. Store: issuer, network, last-4, statement period, transactions (date, merchant, amount, MCC if printed), rewards summary. Do not store: full PAN, CVV, expiry, raw PDF beyond processing.

---

## 6. Indian players and their routes (publicly documented only)

| Player | Route(s) documented | Source (read 2026-10-07) |
|---|---|---|
| CRED | Gmail statement fetch ("CRED Protect" reads only statement emails for cards the user adds; opens the statement PDF) + SMS (bill reminders, payment-credit SMS). CRED Money (bank accounts) is built on the AA framework. | jagoinvestor review 2019 (https://www.jagoinvestor.com/2019/10/cred-review.html): "the app also asks me to give GMAIL permissions for it to automatically get the credit statement"; cardtrail.in (2026-03-21): "link your cards via email statement fetch"; TechCrunch 2024-07-24 (https://techcrunch.com/2024/07/24/cred-launches-personal-finance-manager-for-indias-affluent/): CRED Money "leverages India's account aggregator framework". Which CRED group entity is the FIU is **UNCONFIRMED**. |
| CheQ | SMS + email permissions (community reports; CheQ's own site only says "We don't peek, track, or sell your information") | Jupiter community / Technofino threads (secondary, read 2026-10-07); https://cheq.one/ |
| Fold | Gmail (transaction alert emails; "Only Gmail is supported for real-time transaction tracking"); AA for bank accounts; states credit cards are not on AA | https://help.fold.money/hc/en-us/articles/17257827045138-How-do-you-fetch-my-credit-card-related-data ; https://docs.fold.money/known-issues-with-credit-cards |
| Mojek | Gmail, processed on-device, derived fields to server | https://mojekmoney.help.center/article/1079-how-do-you-fetch-my-credit-card-related-data |
| Jupiter | Gmail ("requires access to look into ONLY credit card statement emails"); HDFC/SBI/ICICI/Axis/Kotak at launch (Nov 2024) | https://community.jupiter.money/t/new-lab-test-15-credit-card-tracking/53872 |
| Fi Money | Own neobank account data; external credit-card tracking route **UNCONFIRMED** (App Store page returned 404 to the fetcher) | cardtrail.in table lists "Neobank account" |
| Kiwi | Issues RuPay credit cards on UPI with partner banks (issuer-side data); no documented third-party card tracking found — **UNCONFIRMED** | gokiwi.in rewards pages (read 2026-10-07) |
| OneCard | Issuer (FPL Technologies with partner banks) — first-party data; not a tracker of other cards | general knowledge; not verified today |
| Walnut (now Axio), Money View | SMS parsing ("reads your transaction SMS messages and auto-categorises spends") | cardtrail.in (2026-03-21); getfinny.app (secondary) |

Pattern: every third-party tracker of *other issuers'* cards uses **Gmail** (statements and/or alerts) as the primary path, with SMS as an Android-only supplement; none uses AA for card data.

---

## Recommended input ladder for cc-smith

1. **v1 — ship (both platforms)**
   1. **Gmail OAuth, `gmail.readonly`** — start restricted-scope verification and CASA on day one (100-user cap until done). Query only issuer sender domains (`docs/research/official-domains.yaml`) and parse transaction alerts + monthly statement emails; do extraction on-device where feasible; persist derived fields only; Limited-Use-compliant privacy policy; no use of email data for ads or credit decisions.
   2. **Statement PDF upload** (share sheet / file picker; password prompt; on-device decrypt + parse; store last-4 + issuer + transactions; delete source).
   3. **Manual quick-add** and CSV import as the universal fallback.
2. **v2 — Android real-time layer and second mailbox**
   1. **`NotificationListenerService`** (Android) for real-time capture of issuer-app and SMS-app notifications, behind an explicit opt-in screen with prominent disclosure; on-device parsing; feature-flagged for fast disablement.
   2. **Microsoft Graph `Mail.Read`** for Outlook/Hotmail users (publisher verification; no CASA).
3. **v3 — only if coverage gaps justify the policy risk / partnerships exist**
   1. Apply for the Play SMS "SMS-based money management" exception only if notification capture proves insufficient and the feature is demonstrably core; expect refusal.
   2. **AA via a regulated partner FIU** for savings/current-account data (bill-payment detection, cash flow), not card spends; revisit if RBI/Sahamati add a credit-card FI type.
   3. Issuer/bank data partnerships (co-brand or API) once there is distribution leverage; design to RBI Card MD para 21(b) (display-only, no storage by partner).
   - Never: FinanceKit (US-only, Apple products only), IMAP app-passwords at consumer scale, storing full PAN.

---

## Things to verify by hand

1. **Gmail "appropriate access" app types for restricted scopes** — find the current Gmail-specific allowed application-type list in the OAuth verification help centre (it was not in the FAQ/requirements pages fetched today) and confirm "personal finance / expense tracking" is an accepted use case; then confirm with Google's verification team during submission.
2. **Does on-device-only processing exempt the app from CASA?** Google's wording ("from or through a third-party server") suggests yes for the Gmail data itself; ask the assessor/Google before relying on it.
3. **Sahamati FIP activation table** (https://sahamati.org.in/account-types-activated-by-banks-on-aas/) — open in a browser and confirm no bank serves a credit-card account type; also check Sahamati's 2025–26 roadmap/SamvAAd material and the Oct-2025 whitepaper (PDF saved by the fetcher; text extraction failed) for any credit-card FI-type plan.
4. **FIU → unregulated-partner data sharing** — get a written legal view (or ask Sahamati) on whether a regulated FIU may share AA-derived data with cc-smith as its outsourced service provider for the user's own advisory use case.
5. **Apple docs**: read FinanceKit / FinanceStore and IdentityLookup (Message Filter) pages in a browser to quote region and entitlement text verbatim; confirm FinanceKit is still Apple Card/Cash/Savings-only in iOS 26.
6. **Android 13+ restricted settings** — confirm whether "Notification access" is among the settings blocked for sideloaded apps (affects only non-Play builds).
7. **Play policy drift** — re-read answer/9888170 and the 2027-01-27 preview before launch; check whether Google has added a notification-listener declaration since 2026-10-07.
8. **CASA lab pricing** — get current quotes from TAC Security and one other ADA-authorised lab; the figures above are from 2024–2026 vendor/blog posts.
9. **Issuer statement password formats** — verify the per-issuer formats against real statements (Cleartax/Adobe are secondary and may be stale); confirm which issuers print a full PAN vs masked PAN on statements.
10. **Player routes** — confirm Fi Money's and Kiwi's card-tracking mechanisms from their own help centres; identify the CRED group entity acting as FIU for CRED Money; confirm CheQ's SMS/email usage from its privacy policy.
11. **Apple review stance on 3.2.1(viii)** for a non-FI advisor — prepare a licensing-position note; optionally pre-check via App Review's contact form.
12. **DPDP Rules effective dates** (2025-11-14 / 2026-11-14 / 2027-05-14) — confirm from the Gazette notifications rather than law-firm summaries.
