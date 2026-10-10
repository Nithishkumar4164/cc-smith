// Parses JSON captured from the running backend (test/fixtures/*.json).
import 'dart:convert';
import 'dart:io';

import 'package:app/api.dart';
import 'package:app/describe.dart';
import 'package:app/models.dart';
import 'package:flutter_test/flutter_test.dart';

dynamic fixture(String name) => jsonDecode(File('test/fixtures/$name.json').readAsStringSync());

void main() {
  late Meta meta;
  setUpAll(() => meta = Meta.fromJson(fixture('meta')));

  test('meta', () {
    expect(meta.categories['dining'], 'Dining and food delivery');
    expect(meta.merchant('swiggy')!.category, 'dining');
    expect(meta.label('amazon'), 'Amazon');
    expect(meta.shortLabel('travel'), 'Travel');
  });

  test('card list', () {
    final cards = (fixture('cards') as List).map((e) => CardSummary.fromJson(e)).toList();
    expect(cards, isNotEmpty);
    final amazon = cards.firstWhere((c) => c.id == 'icici_amazon_pay');
    expect(amazon.annualFeePaise, 0);
    expect(amazon.assessable, isTrue);
    expect(amazon.asOf, isNotNull);
  });

  test('card detail with refs, and readable field text', () {
    final d = CardDetail.fromJson(fixture('card_detail'));
    expect(d.summary.name, 'Amazon Pay ICICI Bank Credit Card');
    final earn = d.fields['earn_rules']!;
    expect(earn.refs.first.official, isTrue);
    expect(earn.refs.first.quote, contains('Prime'));
    expect(earn.refs.first.fetchedAt, isNotNull);
    expect(d.changelog, isNotEmpty);

    final desc = Describer(d.fields, meta: meta);
    final rules = desc.lines('earn_rules');
    expect(rules.first.text, '5% at Amazon, Amazon Prime members only');
    expect(rules.first.sources.single.official, isTrue);
    expect(rules.last.text, startsWith('1% on all other spends'));
    expect(desc.lines('exclusions')[1].text, 'No rewards on Utilities and telecom (except at Amazon)');
    expect(desc.lines('fees').single.text, 'Joining free · Annual free');
  });

  test('card detail: caps, per-spend points, milestones, min txn (Regalia Gold)', () {
    final d = CardDetail.fromJson(fixture('card_detail_regalia'));
    final desc = Describer(d.fields, meta: meta);
    final grocery = desc.lines('earn_rules').firstWhere((l) => l.text.contains('Groceries'));
    expect(grocery.text, contains('per ₹200'));
    expect(grocery.text, contains('capped at 2,000'));
    expect(desc.lines('min_txn').single.text, 'Rewards only on transactions of ₹150 or more');
    expect(desc.lines('milestones').first.detail, contains('₹5,00,000'));
  });

  test('me', () {
    final me = Me.fromJson(fixture('me'));
    expect(me.profile.flags, ['amazon_prime']);
    expect(me.holdings.map((h) => h.cardId), containsAll(['icici_amazon_pay', 'hdfc_millennia']));
    expect(me.holdings.firstWhere((h) => h.cardId == 'hdfc_millennia').statementDay, 5);
    expect(me.spends['rent'], 2500000);
  });

  test('finder', () {
    final f = FinderReport.fromJson(fixture('finder'));
    expect(f.baseNetPaise, 1276000);
    expect(f.portfolios.first.newCards, ['hsbc_live_plus']);
    expect(f.portfolios.first.gainPaise, 918000);
    final millennia = f.baseCards.firstWhere((c) => c.cardId == 'hdfc_millennia');
    expect(millennia.feeWaived, isTrue);
    expect(millennia.feeIncludesGst, isTrue);
    expect(millennia.milestonePaise, 400000);
    expect(millennia.milestonesHit, ['₹1,000 gift voucher at ₹1 lakh a quarter']);
    for (final c in [...f.baseCards, ...f.portfolios.expand((p) => p.cards)]) {
      expect(c.netPaise, c.rewardPaise + c.milestonePaise - (c.feeWaived ? 0 : c.feePaise), reason: c.cardId);
    }
    expect(f.unearned['rent'], 30000000);
    expect(f.keepOrClose, {'icici_amazon_pay': 0, 'hdfc_millennia': 616000});
  });

  test('pay (high confidence) and pay (guessed category, UPI)', () {
    final p = PayResult.fromJson(fixture('pay'));
    expect(p.best!.cardId, 'hdfc_millennia');
    expect(p.best!.rewardPaise, 6000);
    expect(p.marginPaise, 4800);
    expect(p.merchant.isGuess, isFalse);
    expect(p.runnerUp!.cardId, 'icici_amazon_pay');
    expect(p.text, contains('₹60'));
    expect(p.best!.notes, ['5% on Amazon, Bookmyshow, Cultfit, Flipkart and more']);
    expect(p.ranked.last.notes, ['1% on everything else']);

    final g = PayResult.fromJson(fixture('pay_lowconf'));
    expect(g.best, isNull);
    expect(g.merchant.key, isNull);
    expect(g.merchant.isGuess, isTrue);
    expect(g.ranked.first.reasonCodes, ['no_upi']);
    expect(g.text, startsWith('None of your cards can be used here'));
    expect(reasonLabel('no_upi'), 'Not usable on UPI');
    expect(reasonLabel('excluded:fuel', meta: meta), 'Fuel excluded');
    expect(reasonLabel('below_min_txn'), 'Below minimum spend');
    expect(reasonLabel('capped:online_10'), 'Capped');
  });

  test('launches: profiled / speculative / known, with ad and official refs', () {
    final ls = (fixture('launches_v3') as List).map((e) => Launch.fromJson(e)).toList();
    final ace = ls.firstWhere((l) => l.cardId == 'axis_ace');
    expect(ace.confirmed, isTrue);
    expect(ace.refs.first.kind, 'ad');
    expect(ace.refs.where((r) => r.official == true).first.title, contains('ACE'));
    expect(ls.where((l) => l.speculative).every((l) => l.cardId == null && l.gainPaise == null), isTrue);
    expect(ls.firstWhere((l) => l.known).cardId, 'scapia_federal');
  });

  test('pay with bank offers (facts) does not reorder the ranking', () {
    final p = PayResult.fromJson(fixture('pay_offer'));
    final byReward = [...p.ranked]..sort((a, b) => b.rewardPaise.compareTo(a.rewardPaise));
    expect(p.ranked.map((o) => o.cardId), byReward.map((o) => o.cardId));
    expect(p.offers, hasLength(2));
    final o = p.offers.first;
    expect(o.isFact, isTrue);
    expect(o.cardIds, ['hdfc_millennia']);
    expect(o.estSavingPaise, 80000);
    expect(o.minTxnPaise, 500000);
    expect(o.validTo, '2026-10-25');
    expect(o.source!.official, isTrue);
    expect(o.source!.quote, contains('Minimum Spend'));
    expect(p.text, contains('Bank offer'));
    expect(PayResult.fromJson(fixture('pay')).offers, isEmpty);
  });

  test('notice board: sorted act > watch > info, refs, due, rupees', () {
    final ns = (fixture('notices') as List).map((e) => Notice.fromJson(e)).toList();
    expect(ns, isNotEmpty);
    const rank = {'act': 0, 'watch': 1, 'info': 2};
    for (var i = 1; i < ns.length; i++) {
      expect(rank[ns[i - 1].severity]! <= rank[ns[i].severity]!, isTrue);
    }
    final fyf = ns.firstWhere((n) => n.id == 'fyf:hsbc_live_plus');
    expect(fyf.kind, 'fee');
    expect(fyf.due, '2026-11-15');
    expect(fyf.rupeesPaise, 117882);
    expect(fyf.refs.single.official, isTrue);
    final util = ns.firstWhere((n) => n.kind == 'credit');
    expect(util.isGuidance, isTrue);
    expect(util.refs, isEmpty);
    final ornge = ns.firstWhere((n) => n.id == 'feeoffer:hdfc_swiggy_ornge_ltf_corporate');
    expect(ornge.eligibility, 'unknown');
    expect(ornge.requires.single.key, 'select_corporate_employee');
    expect(eligibilityFor(ornge.requires, {'select_corporate_employee': false}, ornge.eligibility), 'no');
    expect(eligibilityFor(ornge.requires, {'select_corporate_employee': true}, ornge.eligibility), 'yes');
    expect(eligibilityFor(ornge.requires, {}, ornge.eligibility), 'unknown');
    expect(ns.where((n) => n.needsAttention).length, ns.where((n) => n.severity != 'info').length);
  });

  test('credit, pools and category totals', () {
    final cr = (fixture('credit') as List).map((e) => Credit.fromJson(e)).toList();
    final hdfc = cr.firstWhere((c) => c.cardId == 'hdfc_millennia');
    expect(hdfc.poolName, 'HDFC shared');
    expect(hdfc.availablePaise, 13000000);
    expect(hdfc.utilisationBp, 3500);
    final me = Me.fromJson(fixture('me_credit'));
    expect(me.pools.single.limitPaise, 20000000);
    final live = me.holdings.firstWhere((h) => h.cardId == 'hsbc_live_plus');
    expect(live.feeStatus, 'fyf');
    expect(live.fyfUntil, '2026-11-15');
    expect(live.creditLimitPaise, 15000000);
    expect(live.toJson()['fyf_until'], '2026-11-15');
    final pooled = me.holdings.firstWhere((h) => h.cardId == 'hdfc_millennia');
    expect(pooled.toJson()['pool_id'], 'hdfc');
    expect(pooled.toJson().containsKey('credit_limit_paise'), isFalse);
    expect(me.categoryTotals['dining'], 900000);
  });

  test('meta groups and memberships; card memberships and fee offers', () {
    expect(meta.groups.firstWhere((g) => g.category == 'dining').merchants.map((m) => m.key), contains('swiggy'));
    expect(meta.membership('amazon_prime')!.why, contains('Prime'));
    final cards = (fixture('cards') as List).map((e) => CardSummary.fromJson(e)).toList();
    expect(cards.firstWhere((c) => c.id == 'icici_amazon_pay').memberships.single.key, 'amazon_prime');
    final blck = cards.firstWhere((c) => c.id == 'hdfc_swiggy_blck').feeOffers.single;
    expect(blck.kind, 'joining_waiver');
    expect(blck.kindLabel, 'Joining fee waiver');
    expect(blck.spendConditionPaise, 7500000);
    expect(blck.source!.official, isTrue);
    final flip = cards.firstWhere((c) => c.id == 'axis_flipkart').feeOffers;
    expect(flip.map((o) => o.tier), containsAll(['fact', 'speculation']));
  });

  test('pay skips cards without enough credit', () {
    final p = PayResult.fromJson(fixture('pay_credit'));
    expect(p.best, isNull);
    final live = p.ranked.firstWhere((o) => o.cardId == 'hsbc_live_plus');
    expect(live.reasonCodes, contains('insufficient_credit:11900000'));
    expect(live.notes, contains('Only ₹1,19,000 of credit available'));
    expect(reasonLabel('insufficient_credit:11900000'), 'Only ₹1,19,000 credit left');
  });

  test('conditions, if-answered rewards, up-to offers, launch variants (live recordings)', () {
    expect(meta.condition('amazon_prime')!.kind, 'membership');
    expect(meta.condition('axis_burgundy_salary')!.kind, 'eligibility');
    final pay = PayResult.fromJson(fixture('pay_amazon_ifans'));
    final ap = pay.ranked.firstWhere((o) => o.cardId == 'icici_amazon_pay');
    expect(ap.ifAnswered.single.key, 'amazon_prime');
    expect(ap.ifAnswered.single.rewardPaise, 25000);
    final upto = PayResult.fromJson(fixture('pay_upto'));
    expect(upto.offers.every((o) => o.estSavingPaise == null && o.upToPaise != null), isTrue);
    final ls = (fixture('launches') as List).map((e) => Launch.fromJson(e)).toList();
    final scapia = ls.firstWhere((l) => l.name.startsWith('Scapia'));
    expect(scapia.variantOf(['scapia_federal']), 'scapia_federal');
    expect(scapia.variantOf(const []), isNull);
    final magnus = (fixture('cards') as List).map((e) => CardSummary.fromJson(e)).firstWhere((c) => c.id == 'axis_magnus');
    expect(magnus.feeOffers.single.requires.single.key, 'axis_burgundy_salary');
    expect(magnus.feeOffers.single.eligibility, 'unknown');
    expect(Me.fromJson(fixture('me_v4')).answers, isEmpty);
  });

  test('transactions', () {
    final t = (fixture('transactions') as List).map((e) => Transaction.fromJson(e)).toList();
    expect(t.single.rewardPaise, 6000);
    expect(t.single.merchantName, 'Swiggy');
  });

  test('FastAPI errors become readable sentences', () {
    expect(describeError(422, '{"detail":"unknown spend key bogus"}'), 'unknown spend key bogus');
    expect(
      describeError(422,
          '{"detail":[{"type":"greater_than","loc":["body","amount_paise"],"msg":"Input should be greater than 0"}]}'),
      'Amount: Input should be greater than 0',
    );
    expect(describeError(500, 'Internal Server Error'), contains('server hit an error'));
  });
}
