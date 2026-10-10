// The phone's alert parser must map every shared vector exactly like the backend's.
import 'dart:convert';
import 'dart:io';

import 'package:app/alerts.dart';
import 'package:app/notifications.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final v = jsonDecode(File('test/fixtures/alert_vectors.json').readAsStringSync()) as Map;
  final receivedAt = DateTime.parse(v['received_at'] as String);
  for (final c in (v['cases'] as List).cast<Map>()) {
    test('vector ${c['id']}', () {
      final got = parseAlert(c['text'] as String, sender: c['sender'] as String?, receivedAt: receivedAt);
      expect(got?.toJson(), c['expected'], reason: c['text'] as String);
    });
  }

  test('long digit runs never survive normalisation', () {
    expect(normalise('Card 4111 1111 1111 1111 used'), isNot(contains('4111 1111')));
    expect(hasLongDigitRun('ref 123456789012'), isTrue);
    expect(hasLongDigitRun('x1234 21-03-2026 05:49'), isFalse);
  });

  test('notification -> event: parsed fields only, no raw text, no card numbers, digit-free id', () {
    final e = eventFromNotification({
      'key': '0|com.snapwork.hdfc|1234|null|10123',
      'package': 'com.snapwork.hdfc',
      'title': 'HDFC Bank',
      'text': 'Spent Rs.1,250 On HDFC Bank Card 4321 At SWIGGY On 2026-10-09:20:15:00. Card 4111 1111 1111 1111',
      'postTime': 1791561300000,
    })!;
    expect(e.keys, unorderedEquals(['id', 'amount_paise', 'currency', 'last4', 'merchant_text', 'ts', 'kind', 'issuer_hint', 'instrument']));
    expect(e['amount_paise'], 125000);
    expect(e['last4'], '4321');
    expect(e['merchant_text'], 'SWIGGY');
    expect(e['issuer_hint'], 'hdfc_bank');
    expect(e.values.whereType<String>().any(hasLongDigitRun), isFalse);
    expect(e.values.whereType<String>().any((v) => v.contains('Spent')), isFalse);
    expect(RegExp(r'\d{4,}').hasMatch(e['id'] as String), isFalse);
    expect(eventFromNotification({'package': 'com.phonepe.app', 'text': 'Your OTP is 123456', 'postTime': 1}), isNull);
  });
}
