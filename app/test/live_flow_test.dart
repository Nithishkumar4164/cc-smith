// Real HTTP against a running backend. Skipped unless CC_SMITH_API is set:
//   CC_SMITH_API=http://127.0.0.1:8000 flutter test test/live_flow_test.dart
import 'dart:io';

import 'package:app/api.dart';
import 'package:app/models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final base = Platform.environment['CC_SMITH_API'];

  test('create user → holdings → spends → finder → pay → confirm (idempotent)', () async {
    var api = Api(base!);
    final cards = await api.cards();
    final scored = cards.where((c) => c.assessable).map((c) => c.id).toList();
    expect(scored.length, greaterThanOrEqualTo(2));

    api = api.withUser(await api.createUser());
    await api.putProfile(const Profile(flags: ['amazon_prime']));
    final me = await api.putHoldings([Holding(cardId: scored[0]), Holding(cardId: scored[1], statementDay: 5)]);
    expect(me.holdings, hasLength(2));
    await api.putSpends({'amazon': 800000, 'swiggy': 400000, 'grocery': 600000, 'fuel': 300000, 'rent': 2500000});

    final f = await api.finder(maxNew: 2);
    expect(f.baseCards, isNotEmpty);
    for (final p in f.portfolios) {
      expect(p.newCards.length, inInclusiveRange(1, 2));
      for (final c in p.cards) {
        expect(c.feeIncludesGst, isTrue);
        expect(c.netPaise, c.rewardPaise + c.milestonePaise - (c.feeWaived ? 0 : c.feePaise));
      }
    }

    final pay = await api.pay(merchant: 'Swiggy', amountPaise: 120000, channel: 'online');
    expect(pay.merchant.key, 'swiggy');
    expect(pay.ranked, hasLength(2));
    expect(pay.best, isNotNull);
    expect(pay.best!.notes, isNotEmpty);

    final key = newIdempotencyKey();
    final r1 = await api.confirm(cardId: pay.best!.cardId, merchant: 'Swiggy', amountPaise: 120000, channel: 'online', idempotencyKey: key);
    final r2 = await api.confirm(cardId: pay.best!.cardId, merchant: 'Swiggy', amountPaise: 120000, channel: 'online', idempotencyKey: key);
    expect(r1, pay.best!.rewardPaise);
    expect(r2, r1);
    expect(await api.transactions(), hasLength(1));

    // Scanned-QR style request: unknown shop + MCC over UPI.
    final qr = await api.pay(merchant: 'Sharma Kirana Store', amountPaise: 50000, channel: 'upi', mcc: '5411');
    expect(qr.merchant.category, 'grocery');
    expect(qr.merchant.isGuess, isTrue);

    await expectLater(api.pay(merchant: 'Swiggy', amountPaise: 0), throwsA(isA<ApiException>().having((e) => e.status, 'status', 422)));
    await expectLater(Api(base).withUser('nope').me(), throwsA(isA<ApiException>().having((e) => e.unknownUser, 'unknownUser', true)));
    // Bank offers (DR-12 facts) sit beside the ranking and never reorder it.
    final ids = cards.map((c) => c.id).toSet();
    if (ids.containsAll({'hdfc_millennia', 'hsbc_live_plus'})) {
      await api.putHoldings(const [Holding(cardId: 'hdfc_millennia'), Holding(cardId: 'hsbc_live_plus')]);
      final o = await api.pay(merchant: 'myntra.com', amountPaise: 800000);
      expect(o.offers, isNotEmpty);
      expect(o.offers.first.cardIds, contains('hdfc_millennia'));
      final sorted = [...o.ranked]..sort((a, b) => b.rewardPaise.compareTo(a.rewardPaise));
      expect(o.ranked.map((x) => x.cardId), sorted.map((x) => x.cardId));
    }

    final launches = await api.launches();
    expect(launches, isNotEmpty);
    expect(launches.map((l) => l.status).toSet().difference({'profiled', 'speculative', 'known', 'rejected'}), isEmpty);
    for (final l in launches.where((l) => l.speculative)) {
      expect(l.gainPaise, isNull, reason: 'speculation is never scored (DR-12)');
    }
  }, skip: base == null ? 'set CC_SMITH_API to run against a live backend' : false);
}
