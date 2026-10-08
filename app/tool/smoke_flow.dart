// ignore_for_file: avoid_print
// End-to-end smoke run of the app's API layer against a live backend:
//   dart run tool/smoke_flow.dart http://127.0.0.1:8000
// create user -> holdings -> spends -> finder -> pay -> confirm -> transactions.
import 'dart:io';

import 'package:app/api.dart';
import 'package:app/format.dart';
import 'package:app/models.dart';

Future<void> main(List<String> args) async {
  final base = args.isNotEmpty ? args.first : 'http://127.0.0.1:8000';
  var api = Api(base);
  final meta = await api.meta();
  final cards = await api.cards();
  print('meta: ${meta.categories.length} categories, ${meta.merchants.length} merchants; catalogue: ${cards.length} cards');

  final uid = await api.createUser();
  api = api.withUser(uid);
  print('user: $uid');

  await api.putProfile(const Profile(flags: ['amazon_prime']));
  final held = cards.where((c) => c.assessable).take(2).map((c) => Holding(cardId: c.id)).toList();
  var me = await api.putHoldings(held);
  print('holdings: ${me.holdings.map((h) => h.cardId).join(', ')}');

  me = await api.putSpends({
    'amazon': 800000,
    'swiggy': 400000,
    'grocery': 600000,
    'fuel': 300000,
    'utilities': 200000,
    'rent': 2500000,
    'other': 500000,
  });
  print('spends/month: ${me.spends.map((k, v) => MapEntry(k, rupees(v)))}');

  final f = await api.finder();
  print('finder: today ${rupees(f.baseNetPaise)}/yr net; ${f.portfolios.length} portfolios');
  for (final p in f.portfolios.take(3)) {
    print('  + ${p.newCards.join(' + ')}: ${rupees(p.gainPaise, signed: true)}/yr');
  }
  print('  keep_or_close: ${f.keepOrClose.map((k, v) => MapEntry(k, rupees(v)))}');
  print('  unearned: ${f.unearned.map((k, v) => MapEntry(k, rupees(v)))}');

  final pay = await api.pay(merchant: 'Swiggy', amountPaise: 120000);
  print('pay Swiggy ₹1,200 -> ${pay.best?.name} earns ${rupees(pay.best?.rewardPaise ?? 0)}, '
      'margin ${rupees(pay.marginPaise)}, category ${pay.merchant.category} (${pay.merchant.confidence})');
  print('  text: ${pay.text}');
  for (final o in pay.ranked) {
    print('  ${o.name}: ${rupees(o.rewardPaise)} ${o.reasonCodes}');
  }

  final key = newIdempotencyKey();
  final r1 = await api.confirm(cardId: pay.best!.cardId, merchant: 'Swiggy', amountPaise: 120000, idempotencyKey: key);
  final r2 = await api.confirm(cardId: pay.best!.cardId, merchant: 'Swiggy', amountPaise: 120000, idempotencyKey: key);
  final txns = await api.transactions();
  print('confirm: ${rupees(r1)} (retry with same key: ${rupees(r2)}); ledger has ${txns.length} txn(s)');

  try {
    await api.pay(merchant: 'Swiggy', amountPaise: 0);
  } on ApiException catch (e) {
    print('422 surfaced as: "${e.message}"');
  }
  final launches = await api.launches();
  print('launches: ${launches.length}');
  exit(0);
}
