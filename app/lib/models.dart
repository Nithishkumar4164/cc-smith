/// JSON models mirroring the Pydantic contract in backend/src/cc_smith/api/main.py.
/// All money is integer paise. Pure Dart.
library;

typedef Json = Map<String, dynamic>;

int _int(Object? v) => v is int ? v : (v is num ? v.toInt() : 0);
int? _intN(Object? v) => v is num ? v.toInt() : null;
String? _strN(Object? v) => v?.toString();
List<T> _list<T>(Object? v, T Function(Json) f) =>
    v is List ? v.whereType<Map>().map((e) => f(Map<String, dynamic>.from(e))).toList() : <T>[];
List<String> _strs(Object? v) => v is List ? v.map((e) => e.toString()).toList() : <String>[];

class MerchantMeta {
  final String key, name, category, channel;
  const MerchantMeta({required this.key, required this.name, required this.category, required this.channel});
  factory MerchantMeta.fromJson(Json j) => MerchantMeta(
    key: j['key'] as String,
    name: j['name'] as String,
    category: '${j['category']}',
    channel: '${j['channel']}',
  );
}

class Meta {
  /// category key -> human label, in server order.
  final Map<String, String> categories;
  final List<MerchantMeta> merchants;
  const Meta({required this.categories, required this.merchants});
  factory Meta.fromJson(Json j) => Meta(
    categories: Map<String, dynamic>.from(j['categories'] as Map).map((k, v) => MapEntry(k, '$v')),
    merchants: _list(j['merchants'], MerchantMeta.fromJson),
  );

  MerchantMeta? merchant(String key) {
    for (final m in merchants) {
      if (m.key == key) return m;
    }
    return null;
  }

  /// Label for a spend key that may be a category or a merchant.
  String label(String key) => categories[key] ?? merchant(key)?.name ?? _titleCase(key);

  /// Short label (first clause of the category label).
  String shortLabel(String key) {
    final l = label(key);
    final cut = l.indexOf(' (');
    return cut > 0 ? l.substring(0, cut) : l;
  }
}

String _titleCase(String key) =>
    key.split('_').map((w) => w.isEmpty ? w : w[0].toUpperCase() + w.substring(1)).join(' ');

class Ref {
  final String url;
  final String? quote;
  final bool? official;
  final String? fetchedAt;
  final String? match;
  final String? title; // launch refs: page title
  final String? kind; // launch refs: ad | official_page | news ...
  const Ref({required this.url, this.quote, this.official, this.fetchedAt, this.match, this.title, this.kind});
  factory Ref.fromJson(Json j) => Ref(
    url: '${j['url'] ?? ''}',
    quote: _strN(j['quote']),
    official: j['official'] as bool?,
    fetchedAt: _strN(j['fetched_at']),
    match: _strN(j['match']),
    title: _strN(j['title']),
    kind: _strN(j['kind']),
  );
}

class CardSummary {
  final String id, name, issuer, status;
  final bool assessable;
  final int? annualFeePaise;
  final String? currencyKind, currencyName, asOf;
  final int speculationCount;
  const CardSummary({
    required this.id,
    required this.name,
    required this.issuer,
    required this.status,
    required this.assessable,
    this.annualFeePaise,
    this.currencyKind,
    this.currencyName,
    this.asOf,
    this.speculationCount = 0,
  });
  factory CardSummary.fromJson(Json j) => CardSummary(
    id: j['id'] as String,
    name: j['name'] as String,
    issuer: '${j['issuer']}',
    status: '${j['status']}',
    assessable: j['assessable'] == true,
    annualFeePaise: _intN(j['annual_fee_paise']),
    currencyKind: _strN(j['currency_kind']),
    currencyName: _strN(j['currency_name']),
    asOf: _strN(j['as_of']),
    speculationCount: _int(j['speculation_count']),
  );
}

class FieldView {
  final Object? value;
  final List<Ref> refs;
  final String asOf;
  final int version;
  const FieldView({this.value, required this.refs, required this.asOf, required this.version});
  factory FieldView.fromJson(Json j) => FieldView(
    value: j['value'],
    refs: _list(j['refs'], Ref.fromJson),
    asOf: '${j['as_of']}',
    version: _int(j['version']),
  );
}

class Speculation {
  final int id;
  final String field, origin;
  final Object? value;
  final String? reason;
  final List<Ref> refs;
  final String openedAt, expiresAt;
  const Speculation({
    required this.id,
    required this.field,
    required this.origin,
    this.value,
    this.reason,
    required this.refs,
    required this.openedAt,
    required this.expiresAt,
  });
  factory Speculation.fromJson(Json j) => Speculation(
    id: _int(j['id']),
    field: '${j['field']}',
    origin: '${j['origin']}',
    value: j['value'],
    reason: _strN(j['reason']),
    refs: _list(j['refs'], Ref.fromJson),
    openedAt: '${j['opened_at']}',
    expiresAt: '${j['expires_at']}',
  );
}

class ChangeEvent {
  final int id;
  final String cardId, eventType;
  final String? field, tier;
  final Object? oldValue, newValue;
  final bool largeChange;
  final String at;
  const ChangeEvent({
    required this.id,
    required this.cardId,
    required this.eventType,
    this.field,
    this.tier,
    this.oldValue,
    this.newValue,
    required this.largeChange,
    required this.at,
  });
  factory ChangeEvent.fromJson(Json j) => ChangeEvent(
    id: _int(j['id']),
    cardId: '${j['card_id']}',
    eventType: '${j['event_type']}',
    field: _strN(j['field']),
    tier: _strN(j['tier']),
    oldValue: j['old'],
    newValue: j['new'],
    largeChange: j['large_change'] == true,
    at: '${j['at']}',
  );
}

class CardDetail {
  final CardSummary summary;
  final Map<String, FieldView> fields;
  final List<Speculation> speculation;
  final List<ChangeEvent> changelog;
  const CardDetail({required this.summary, required this.fields, required this.speculation, required this.changelog});
  factory CardDetail.fromJson(Json j) => CardDetail(
    summary: CardSummary.fromJson(j),
    fields: (j['fields'] as Map? ?? {}).map(
      (k, v) => MapEntry('$k', FieldView.fromJson(Map<String, dynamic>.from(v as Map))),
    ),
    speculation: _list(j['speculation'], Speculation.fromJson),
    changelog: _list(j['changelog'], ChangeEvent.fromJson),
  );
}

class Holding {
  final String cardId;
  final String? last4;
  final int? statementDay;
  final int? renewalMonth;
  const Holding({required this.cardId, this.last4, this.statementDay, this.renewalMonth});
  factory Holding.fromJson(Json j) => Holding(
    cardId: '${j['card_id']}',
    last4: _strN(j['last4']),
    statementDay: _intN(j['statement_day']),
    renewalMonth: _intN(j['renewal_month']),
  );
  Json toJson() => {
    'card_id': cardId,
    if (last4 != null) 'last4': last4,
    if (statementDay != null) 'statement_day': statementDay,
    if (renewalMonth != null) 'renewal_month': renewalMonth,
  };
  Holding copyWith({int? statementDay, bool clearStatementDay = false}) => Holding(
    cardId: cardId,
    last4: last4,
    statementDay: clearStatementDay ? null : (statementDay ?? this.statementDay),
    renewalMonth: renewalMonth,
  );
}

class Profile {
  final List<String> flags;
  final String? scoreBand, incomeBand;
  final String rewardPreference; // any | cashback | points
  final int? maxAnnualFeePaise;
  const Profile({
    this.flags = const [],
    this.scoreBand,
    this.incomeBand,
    this.rewardPreference = 'any',
    this.maxAnnualFeePaise,
  });
  factory Profile.fromJson(Json j) => Profile(
    flags: _strs(j['flags']),
    scoreBand: _strN(j['score_band']),
    incomeBand: _strN(j['income_band']),
    rewardPreference: _strN(j['reward_preference']) ?? 'any',
    maxAnnualFeePaise: _intN(j['max_annual_fee_paise']),
  );
  Json toJson() => {
    'flags': flags,
    'score_band': scoreBand,
    'income_band': incomeBand,
    'reward_preference': rewardPreference,
    'max_annual_fee_paise': maxAnnualFeePaise,
  };
}

class Me {
  final String userId;
  final Profile profile;
  final List<Holding> holdings;
  final Map<String, int> spends; // monthly paise
  const Me({required this.userId, required this.profile, required this.holdings, required this.spends});
  factory Me.fromJson(Json j) => Me(
    userId: '${j['user_id']}',
    profile: Profile.fromJson(Map<String, dynamic>.from(j['profile'] as Map? ?? {})),
    holdings: _list(j['holdings'], Holding.fromJson),
    spends: (j['spends'] as Map? ?? {}).map((k, v) => MapEntry('$k', _int(v))),
  );
}

class CardLine {
  final String spendKey;
  final int spendPaise, rewardPaise;
  final bool capped;
  const CardLine({required this.spendKey, required this.spendPaise, required this.rewardPaise, required this.capped});
  factory CardLine.fromJson(Json j) => CardLine(
    spendKey: '${j['spend_key']}',
    spendPaise: _int(j['spend_paise']),
    rewardPaise: _int(j['reward_paise']),
    capped: j['capped'] == true,
  );
}

/// One card's annual result inside a simulation. Amounts are per year.
class CardResult {
  final String cardId, name;
  final int spendPaise, rewardPaise, milestonePaise, feePaise, netPaise;
  final bool feeWaived;
  final bool feeIncludesGst;
  final List<String> milestonesHit;
  final List<CardLine> lines;
  const CardResult({
    this.feeIncludesGst = false,
    this.milestonesHit = const [],
    required this.cardId,
    required this.name,
    required this.spendPaise,
    required this.rewardPaise,
    required this.milestonePaise,
    required this.feePaise,
    required this.feeWaived,
    required this.netPaise,
    required this.lines,
  });
  factory CardResult.fromJson(Json j) => CardResult(
    cardId: '${j['card_id']}',
    name: '${j['name']}',
    spendPaise: _int(j['spend_paise']),
    rewardPaise: _int(j['reward_paise']),
    milestonePaise: _int(j['milestone_paise']),
    feePaise: _int(j['fee_paise']),
    feeWaived: j['fee_waived'] == true,
    feeIncludesGst: j['fee_includes_gst'] == true,
    milestonesHit: _strs(j['milestones_hit']),
    netPaise: _int(j['net_paise']),
    lines: _list(j['lines'], CardLine.fromJson),
  );
}

class Portfolio {
  final List<String> newCards;
  final int gainPaise;
  final List<CardResult> cards;
  const Portfolio({required this.newCards, required this.gainPaise, required this.cards});
  factory Portfolio.fromJson(Json j) => Portfolio(
    newCards: _strs(j['new_cards']),
    gainPaise: _int(j['gain_paise']),
    cards: _list(j['cards'], CardResult.fromJson),
  );
}

class FinderReport {
  final int baseNetPaise;
  final List<CardResult> baseCards;
  final List<Portfolio> portfolios;
  final Map<String, int> keepOrClose; // card -> annual loss if closed (negative = closing saves)
  final Map<String, int> unearned; // spend key -> annual spend earning nothing
  final List<String> notAssessable;
  const FinderReport({
    required this.baseNetPaise,
    required this.baseCards,
    required this.portfolios,
    required this.keepOrClose,
    required this.unearned,
    required this.notAssessable,
  });
  factory FinderReport.fromJson(Json j) => FinderReport(
    baseNetPaise: _int(j['base_net_paise']),
    baseCards: _list(j['base_cards'], CardResult.fromJson),
    portfolios: _list(j['portfolios'], Portfolio.fromJson),
    keepOrClose: (j['keep_or_close'] as Map? ?? {}).map((k, v) => MapEntry('$k', _int(v))),
    unearned: (j['unearned'] as Map? ?? {}).map((k, v) => MapEntry('$k', _int(v))),
    notAssessable: _strs(j['not_assessable']),
  );
}

class MerchantView {
  final String? key;
  final String name, category, channel, confidence;
  const MerchantView({
    this.key,
    required this.name,
    required this.category,
    required this.channel,
    required this.confidence,
  });
  factory MerchantView.fromJson(Json j) => MerchantView(
    key: _strN(j['key']),
    name: '${j['name']}',
    category: '${j['category']}',
    channel: '${j['channel']}',
    confidence: '${j['confidence']}',
  );
  bool get isGuess => confidence != 'high';
}

class PayOption {
  final String cardId, name;
  final int rewardPaise;
  final List<String> reasonCodes, rules;

  /// Plain-language lines from the server ("5% on Amazon", "Fuel is excluded").
  final List<String> notes;
  const PayOption({
    required this.cardId,
    required this.name,
    required this.rewardPaise,
    required this.reasonCodes,
    required this.rules,
    this.notes = const [],
  });
  factory PayOption.fromJson(Json j) => PayOption(
    cardId: '${j['card_id']}',
    name: '${j['name']}',
    rewardPaise: _int(j['reward_paise']),
    reasonCodes: _strs(j['reason_codes']),
    rules: _strs(j['rules']),
    notes: _strs(j['notes']),
  );
}

/// A bank offer at this merchant (issuer offer pages). Shown beside the advice;
/// never changes the card ranking.
class Offer {
  final String id, title, tier;
  final String? issuer, validTo, url, quote;
  final List<String> cardIds;
  final int? minTxnPaise, estSavingPaise;
  const Offer({
    required this.id,
    required this.title,
    required this.tier,
    this.issuer,
    this.validTo,
    this.url,
    this.quote,
    this.cardIds = const [],
    this.minTxnPaise,
    this.estSavingPaise,
  });
  factory Offer.fromJson(Json j) => Offer(
    id: '${j['id']}',
    title: '${j['title']}',
    tier: '${j['tier'] ?? 'speculation'}',
    issuer: _strN(j['issuer']),
    validTo: _strN(j['valid_to']),
    url: _strN(j['url']),
    quote: _strN(j['quote']),
    cardIds: _strs(j['card_ids']),
    minTxnPaise: _intN(j['min_txn_paise']),
    estSavingPaise: _intN(j['est_saving_paise']),
  );
  bool get isFact => tier == 'fact';
  Ref? get source => url == null ? null : Ref(url: url!, quote: quote, official: isFact);
}

class PayResult {
  final MerchantView merchant;
  final String channel;
  final PayOption? best;
  final int marginPaise;
  final String text;
  final List<PayOption> ranked;
  final List<Offer> offers;
  const PayResult({
    this.offers = const [],
    required this.merchant,
    required this.channel,
    this.best,
    required this.marginPaise,
    required this.text,
    required this.ranked,
  });
  factory PayResult.fromJson(Json j) => PayResult(
    merchant: MerchantView.fromJson(Map<String, dynamic>.from(j['merchant'] as Map)),
    channel: '${j['channel']}',
    best: j['best'] is Map ? PayOption.fromJson(Map<String, dynamic>.from(j['best'] as Map)) : null,
    marginPaise: _int(j['margin_paise']),
    text: '${j['text'] ?? ''}',
    ranked: _list(j['ranked'], PayOption.fromJson),
    offers: _list(j['offers'], Offer.fromJson),
  );

  /// Next eligible card after the best, if any (for "more than X" copy).
  PayOption? get runnerUp {
    if (best == null) return null;
    for (final o in ranked) {
      if (o.cardId != best!.cardId && !o.reasonCodes.contains('no_upi') && !o.reasonCodes.contains('not_assessable')) {
        return o;
      }
    }
    return null;
  }
}

class Transaction {
  final int id;
  final String cardId;
  final int amountPaise, rewardPaise;
  final String? merchantName, category, channel;
  final String ts;
  const Transaction({
    required this.id,
    required this.cardId,
    required this.amountPaise,
    required this.rewardPaise,
    this.merchantName,
    this.category,
    this.channel,
    required this.ts,
  });
  factory Transaction.fromJson(Json j) => Transaction(
    id: _int(j['id']),
    cardId: '${j['card_id']}',
    amountPaise: _int(j['amount_paise']),
    rewardPaise: _int(j['reward_paise']),
    merchantName: _strN(j['merchant_name']),
    category: _strN(j['category']),
    channel: _strN(j['channel']),
    ts: '${j['ts']}',
  );
}

class Launch {
  final int id;
  final String name, status, firstSeen;
  final String? issuer, cardId, summary;
  final List<Ref> refs;
  final int? gainPaise;
  const Launch({
    required this.id,
    required this.name,
    required this.status,
    required this.firstSeen,
    this.issuer,
    this.cardId,
    this.summary,
    required this.refs,
    this.gainPaise,
  });
  factory Launch.fromJson(Json j) => Launch(
    id: _int(j['id']),
    name: '${j['name']}',
    status: '${j['status']}',
    firstSeen: '${j['first_seen']}',
    issuer: _strN(j['issuer']),
    cardId: _strN(j['card_id']),
    summary: _strN(j['summary']),
    refs: _list(j['refs'], Ref.fromJson),
    gainPaise: _intN(j['gain_paise']),
  );

  /// profiled = profiled from the bank's own pages and scored (DR-12);
  /// speculative = reported, not confirmed; known = already in the catalogue;
  /// rejected = not a card launch (hidden).
  bool get confirmed => status == 'profiled';
  bool get speculative => status == 'speculative';
  bool get known => status == 'known';
  bool get rejected => status == 'rejected';
}

/// POST /finder/assess: what adding one card is worth on top of current holdings.
class AssessResult {
  final String cardId;
  final int gainPaise;
  final bool assessable;
  final List<CardResult> cards;
  const AssessResult({required this.cardId, required this.gainPaise, required this.assessable, required this.cards});
  factory AssessResult.fromJson(Json j) => AssessResult(
    cardId: '${j['card_id']}',
    gainPaise: _int(j['gain_paise']),
    assessable: j['assessable'] == true,
    cards: _list(j['cards'], CardResult.fromJson),
  );
}
