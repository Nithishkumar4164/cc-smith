// Drives the real widget tree against recorded backend responses (fixtures).
import 'dart:convert';
import 'dart:io';

import 'package:app/main.dart';
import 'package:app/state.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

String fx(String n) => File('test/fixtures/$n.json').readAsStringSync();

void main() {
  late List<String> calls;

  http.Client backend() => MockClient((req) async {
        calls.add('${req.method} ${req.url.path}');
        final body = switch ((req.method, req.url.path)) {
          ('GET', '/meta') => fx('meta'),
          ('GET', '/cards') => fx('cards'),
          ('GET', '/me') => fx('me'),
          ('GET', '/me/transactions') => fx('transactions'),
          ('GET', '/launches') => fx('launches'),
          ('GET', '/ops/changes') => '[]',
          ('POST', '/users') => '{"user_id":"048460289250402db2f1775e98fcfee5"}',
          ('PUT', '/me/holdings' || '/me/spends' || '/me/profile') => fx('me'),
          ('POST', '/finder') => fx('finder'),
          ('POST', '/finder/assess') => '{"card_id":"x","gain_paise":0,"cards":[],"assessable":false}',
          ('POST', '/pay') => jsonDecode(utf8.decode(req.bodyBytes))['merchant'] == 'myntra.com' ? fx('pay_offer') : fx('pay'),
          ('POST', '/pay/confirm') => '{"txn_id":1,"reward_paise":6000}',
          ('GET', final p) when p.startsWith('/cards/') => fx('card_detail'),
          _ => null,
        };
        if (body == null) return http.Response('{"detail":"no fixture"}', 404);
        return http.Response.bytes(utf8.encode(body), 200, headers: {'content-type': 'application/json'});
      });

  Future<AppState> pumpApp(WidgetTester tester, {bool fresh = false}) async {
    calls = [];
    SharedPreferences.setMockInitialValues(fresh
        ? {}
        : {
            'user_id': '048460289250402db2f1775e98fcfee5',
            'onboarded_user': '048460289250402db2f1775e98fcfee5',
          });
    final state = AppState(await SharedPreferences.getInstance(), client: backend());
    await tester.binding.setSurfaceSize(const Size(412, 915));
    await tester.pumpWidget(AppScope(state: state, child: const CcSmithApp()));
    await state.boot();
    await tester.pumpAndSettle();
    return state;
  }

  testWidgets('Pay: ask, see best card in rupees, confirm', (tester) async {
    await pumpApp(tester);
    expect(find.text('Checkout Advisor'), findsOneWidget);

    await tester.enterText(find.widgetWithText(TextField, 'Merchant'), 'Swiggy');
    await tester.enterText(find.widgetWithText(TextField, 'Amount'), '1200');
    await tester.tap(find.text('Find best card'));
    await tester.pumpAndSettle();

    expect(find.text('HDFC Bank Millennia Credit Card'), findsWidgets);
    expect(find.text('₹60'), findsWidgets);
    expect(find.text('5% on Amazon, Bookmyshow, Cultfit, Flipkart and more'), findsWidgets);
    expect(find.textContaining('₹48 more than Amazon Pay ICICI'), findsWidgets);
    expect(calls, contains('POST /pay'));

    await tester.drag(find.byType(ListView).first, const Offset(0, -500));
    await tester.pumpAndSettle();
    await tester.tap(find.text('I paid with this'));
    await tester.pumpAndSettle();
    expect(calls, contains('POST /pay/confirm'));
    expect(find.text('Logged'), findsOneWidget);
  });

  testWidgets('Finder, Cards detail with sources, Market empty state render', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.text('Finder'));
    await tester.pumpAndSettle();
    expect(find.text('₹12,760/yr net'), findsOneWidget);
    expect(find.textContaining('HSBC Live+'), findsWidgets);
    expect(find.textContaining('incl. GST'), findsWidgets);

    await tester.tap(find.text('Cards'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Search cards or banks'), 'amazon');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Amazon Pay ICICI Bank Credit Card'));
    await tester.pumpAndSettle();
    expect(find.text('5% at Amazon, Amazon Prime members only'), findsOneWidget);
    await tester.tap(find.textContaining('Source · icici.bank.in').first);
    await tester.pumpAndSettle();
    expect(find.textContaining('Prime Membership, earn rate'), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.tap(find.text('Market'));
    await tester.pumpAndSettle();
    expect(find.text('Axis Bank ACE Credit Card'), findsOneWidget);
    expect(find.text('Confirmed by bank'), findsWidgets);
    expect(find.text('Reported, not confirmed by the bank'), findsWidgets);

    await tester.tap(find.text('Profile'));
    await tester.pumpAndSettle();
    expect(find.text('YOUR CARDS'), findsOneWidget);
  });

  testWidgets('dark mode renders the Pay screen', (tester) async {
    tester.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
    addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);
    await pumpApp(tester);
    expect(Theme.of(tester.element(find.text('Checkout Advisor'))).brightness, Brightness.dark);
  });

  testWidgets('first run: onboarding creates user, saves cards, spends, preferences, then lands on Pay', (tester) async {
    await pumpApp(tester, fresh: true);
    await tester.tap(find.text('Get started'));
    await tester.pumpAndSettle();
    expect(find.text('Cards you hold'), findsOneWidget);
    await tester.enterText(find.widgetWithText(TextField, 'Search cards or banks'), 'millennia');
    await tester.pumpAndSettle();
    await tester.tap(find.text('HDFC Bank Millennia Credit Card'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    expect(find.text('What you spend each month'), findsOneWidget);
    await tester.enterText(find.byType(TextField).first, '8000');
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    expect(find.text('Your preferences'), findsOneWidget);
    await tester.tap(find.text('Finish'));
    await tester.pumpAndSettle();
    expect(find.text('Checkout Advisor'), findsOneWidget);
    expect(calls, containsAllInOrder(['POST /users', 'PUT /me/holdings', 'PUT /me/spends', 'PUT /me/profile']));
  });

  testWidgets('Pay shows bank offers with card, saving, min, date and official source', (tester) async {
    await pumpApp(tester);
    await tester.enterText(find.widgetWithText(TextField, 'Merchant'), 'myntra.com');
    await tester.enterText(find.widgetWithText(TextField, 'Amount'), '8000');
    await tester.tap(find.text('Find best card'));
    await tester.pumpAndSettle();
    expect(find.text('HSBC Live+ Credit Card'), findsWidgets);
    await tester.drag(find.byType(ListView).first, const Offset(0, -600));
    await tester.pumpAndSettle();
    expect(find.text('BANK OFFERS HERE'), findsOneWidget);
    expect(find.text('10% up to ₹1,000 on min ₹5,000 (credit cards, except co-branded)'), findsOneWidget);
    expect(find.text('With your HDFC Bank Millennia Credit Card'), findsWidgets);
    expect(find.text('₹800 off this payment (about)'), findsWidgets);
    expect(find.text('min ₹5,000 · till 25 Oct 2026'), findsWidgets);
    expect(find.text('Reported, not confirmed by the bank'), findsNothing);
    await tester.tap(find.textContaining('Source · hdfc.bank.in').first);
    await tester.pumpAndSettle();
    expect(find.textContaining('Minimum Spend - Rs. 5,000'), findsWidgets);
  });
}
