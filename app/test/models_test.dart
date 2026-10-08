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
    final ls = (fixture('launches') as List).map((e) => Launch.fromJson(e)).toList();
    final ace = ls.firstWhere((l) => l.cardId == 'axis_ace');
    expect(ace.confirmed, isTrue);
    expect(ace.refs.first.kind, 'ad');
    expect(ace.refs.where((r) => r.official == true).first.title, contains('ACE'));
    expect(ls.where((l) => l.speculative).every((l) => l.cardId == null && l.gainPaise == null), isTrue);
    expect(ls.firstWhere((l) => l.known).cardId, 'scapia_federal');
  });

  test('pay with bank offers (facts) does not reorder the ranking', () {
    final p = PayResult.fromJson(fixture('pay_offer'));
    expect(p.best!.cardId, 'hsbc_live_plus');
    expect(p.ranked.map((o) => o.cardId), ['hsbc_live_plus', 'hdfc_millennia']);
    expect(p.offers, hasLength(2));
    final o = p.offers.first;
    expect(o.isFact, isTrue);
    expect(o.cardIds, ['hdfc_millennia']);
    expect(o.estSavingPaise, 80000);
    expect(o.minTxnPaise, 500000);
    expect(o.validTo, '2026-10-25');
    expect(o.source!.official, isTrue);
    expect(o.source!.quote, contains('Minimum Spend'));
    expect(p.text, contains('has a bank offer here'));
    expect(PayResult.fromJson(fixture('pay')).offers, isEmpty);
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
