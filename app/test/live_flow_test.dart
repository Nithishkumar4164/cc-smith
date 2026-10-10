// Real HTTP against a running backend. Skipped unless CC_SMITH_API is set:
//   CC_SMITH_API=http://127.0.0.1:8000 flutter test test/live_flow_test.dart
import 'dart:io';

import 'package:app/api.dart';
import 'package:app/capture.dart';
import 'package:app/notifications.dart';
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

    // Credit: a shared HDFC limit and an own limit with a free first year.
    if (ids.containsAll({'hdfc_millennia', 'hsbc_live_plus'})) {
      await api.putPools(const [Pool(id: 'hdfc', name: 'HDFC shared', limitPaise: 20000000)]);
      final me2 = await api.putHoldings(const [
        Holding(cardId: 'hdfc_millennia', poolId: 'hdfc', balancePaise: 7000000),
        Holding(cardId: 'hsbc_live_plus', creditLimitPaise: 15000000, balancePaise: 2000000, feeStatus: 'fyf', fyfUntil: '2026-11-15'),
      ]);
      expect(me2.pools.single.id, 'hdfc');
      final credit = {for (final c in await api.credit()) c.cardId: c};
      expect(credit['hdfc_millennia']!.availablePaise, 13000000);
      expect(credit['hdfc_millennia']!.poolName, 'HDFC shared');
      expect(credit['hsbc_live_plus']!.utilisationBp, 1333);
      final notices = await api.notices();
      expect(notices.any((n) => n.id == 'fyf:hsbc_live_plus' && n.due == '2026-11-15'), isTrue);
      final big = await api.pay(merchant: 'MakeMyTrip', amountPaise: 14000000);
      expect(big.ranked.first.reasonCodes.any((r) => r.startsWith('insufficient_credit:')), isTrue);
      final after = {for (final c in await api.billPaid('hdfc_millennia')) c.cardId: c};
      expect(after['hdfc_millennia']!.outstandingPaise, 0);
    }

    // Conditions: answers merge, null clears.
    var me3 = await api.putAnswers({'amazon_prime': true, 'axis_burgundy_salary': false});
    expect(me3.answers, {'amazon_prime': true, 'axis_burgundy_salary': false});
    me3 = await api.putAnswers({'axis_burgundy_salary': null});
    expect(me3.answers, {'amazon_prime': true});

    // Capture: a password-protected synthetic statement (made by backend/tests/capture_docs.py).
    if (ids.contains('hdfc_millennia')) {
      final pdf = File('test/fixtures/capture/statement_pw.pdf').readAsBytesSync();
      await expectLater(api.uploadStatement(pdf, 's.pdf', cardId: 'hdfc_millennia'),
          throwsA(isA<ApiException>().having((e) => e.code, 'code', 'password_required')));
      final st = StatementResult.fromJson(await api.uploadStatement(pdf, 's.pdf', password: 'TEST1234', cardId: 'hdfc_millennia'));
      expect(st.matched, isTrue);
      expect(st.totalDuePaise, 3678600);
      final cr = CreditReportResult.fromJson(await api.uploadCreditReport(File('test/fixtures/capture/credit_report.pdf').readAsBytesSync(), 'r.pdf'));
      expect(cr.score, isNotNull);
      final ev = eventFromNotification({
        'key': 'k1', 'package': 'com.snapwork.hdfc', 'postTime': DateTime.now().millisecondsSinceEpoch,
        'text': 'Spent Rs.499 On HDFC Bank Card 4321 At SWIGGY On 2026-10-10:10:00:00.',
      })!;
      final out = await api.postEvents([ev]);
      expect((out['outcomes'] as List).single['outcome'], isIn(['recorded', 'duplicate', 'unmatched_card']));
    }

    // Demo bureau discovery, demo budget import + pin/unpin, market offers.
    final start = await api.bureauStart('9876543210');
    expect(start['mock'], isTrue);
    final found = CreditReportResult.fromJson(await api.bureauVerify('${start['request_id']}', '${start['demo_otp']}'));
    expect(found.accounts, isNotEmpty);
    final (n, b) = await api.importBudgetDemo();
    expect(n, greaterThan(0));
    expect(b.lines, isNotEmpty);
    final line = b.lines.first;
    final pinned = await api.putBudget({line.key: line.budgetPaise + 100000});
    expect(pinned.lines.firstWhere((l) => l.key == line.key).pinned, isTrue);
    final unpinned = await api.putBudget({line.key: null});
    expect(unpinned.lines.firstWhere((l) => l.key == line.key).pinned, isFalse);
    final offers = await api.marketOffers();
    expect(offers.every((o) => o.kind == 'fee_offer'), isTrue);
    expect((await api.notices()).any((x) => x.kind == 'fee_offer'), isFalse);

    final launches = await api.launches();
    expect(launches, isNotEmpty);
    expect(launches.map((l) => l.status).toSet().difference({'profiled', 'speculative', 'known', 'rejected'}), isEmpty);
    for (final l in launches.where((l) => l.speculative)) {
      expect(l.gainPaise, isNull, reason: 'speculation is never scored (DR-12)');
    }
  }, skip: base == null ? 'set CC_SMITH_API to run against a live backend' : false);
}
