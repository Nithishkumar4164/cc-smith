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
  late Map<String, Object?> sent; // last JSON body per 'METHOD /path'
  var meFixture = 'me';
  var putMeFixture = 'me';

  http.Client backend() => MockClient((req) async {
        calls.add('${req.method} ${req.url.path}');
        if (req.bodyBytes.isNotEmpty) sent['${req.method} ${req.url.path}'] = jsonDecode(utf8.decode(req.bodyBytes));
        final body = switch ((req.method, req.url.path)) {
          ('GET', '/meta') => fx('meta'),
          ('GET', '/cards') => fx('cards'),
          ('GET', '/me') => fx(meFixture),
          ('GET', '/me/notices') => fx('notices'),
          ('GET', '/me/credit') => fx('credit'),
          ('PUT', '/me/pools') => fx(meFixture),
          ('POST', final p) when p.endsWith('/bill-paid') => fx('credit'),
          ('GET', '/me/transactions') => fx('transactions'),
          ('GET', '/launches') => fx('launches'),
          ('GET', '/ops/changes') => '[]',
          ('POST', '/users') => '{"user_id":"048460289250402db2f1775e98fcfee5"}',
          ('PUT', '/me/holdings' || '/me/spends' || '/me/profile') => fx(putMeFixture),
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

  Future<AppState> pumpApp(WidgetTester tester, {bool fresh = false, String me = 'me', String? putMe}) async {
    calls = [];
    sent = {};
    meFixture = me;
    putMeFixture = putMe ?? me;
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

    await tester.tap(find.byTooltip('Profile').first);
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

  testWidgets('Notices tab: badge, severity, why / what to do, ₹ at stake, due date, source', (tester) async {
    final app = await pumpApp(tester);
    expect(app.attentionCount, 6);
    expect(find.descendant(of: find.byType(NavigationBar), matching: find.text('6')), findsOneWidget);
    await tester.tap(find.text('Notices'));
    await tester.pumpAndSettle();
    expect(find.text('6 to keep an eye on'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Free year on HSBC Live+ Credit Card ends 15 Nov 2026'), 300,
        scrollable: find.byType(Scrollable).hitTestable().first);
    expect(find.text('By 15 Nov 2026'), findsWidgets);
    expect(find.text('₹1,179 at stake'), findsOneWidget);
    expect(find.textContaining('After that the renewal fee is'), findsOneWidget);
    expect(find.text('Keep an eye'), findsWidgets);
    expect(find.text('What to do  '), findsNothing); // label and text are one rich text
    expect(find.textContaining('Check whether your spend will reach the waiver', findRichText: true), findsOneWidget);
    final fyfCard = find.ancestor(of: find.text('Free year on HSBC Live+ Credit Card ends 15 Nov 2026'), matching: find.byType(Card));
    final src = find.descendant(of: fyfCard, matching: find.textContaining('Source · hsbc.bank.in'));
    await tester.ensureVisible(src);
    await tester.pumpAndSettle();
    await tester.tap(src);
    await tester.pumpAndSettle();
    expect(find.textContaining('Annual fee (waived if you spend'), findsWidgets);
  });

  testWidgets('credit editor: create a shared limit, set outstanding and first-year-free; saved pools before holdings',
      (tester) async {
    await pumpApp(tester, me: 'me_credit');
    await tester.tap(find.byTooltip('Profile').first);
    await tester.pumpAndSettle();
    expect(find.text('₹1,30,000 available'), findsOneWidget);
    expect(find.text('35% used'), findsOneWidget);
    expect(find.textContaining('shared limit: HDFC shared'), findsOneWidget);

    await tester.tap(find.text('Edit cards you hold'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Shares HDFC shared (₹2,00,000)'), findsOneWidget);
    await tester.enterText(find.widgetWithText(TextField, 'Search cards or banks'), 'Live+');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Limit, balance and fee').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Shares a limit'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('New shared limit'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Shared limit name'), 'HSBC family');
    await tester.enterText(find.widgetWithText(TextField, 'Shared limit'), '300000');
    await tester.tap(find.text('Create'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Outstanding today'), '25000');
    await tester.ensureVisible(find.text('Done'));
    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Shares HSBC family (₹3,00,000) · owes ₹25,000 · Free until 15 Nov 2026'), findsOneWidget);
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();

    final pools = sent['PUT /me/pools'] as List;
    expect(pools.map((p) => p['id']), containsAll(['hdfc', 'hsbc_family']));
    expect(pools.firstWhere((p) => p['id'] == 'hsbc_family')['limit_paise'], 30000000);
    expect(calls.indexOf('PUT /me/pools'), lessThan(calls.lastIndexOf('PUT /me/holdings')));
    final live = (sent['PUT /me/holdings'] as List).firstWhere((h) => h['card_id'] == 'hsbc_live_plus');
    expect(live['pool_id'], 'hsbc_family');
    expect(live.containsKey('credit_limit_paise'), isFalse);
    expect(live['balance_paise'], 2500000);
    expect(live['fee_status'], 'fyf');
    expect(live['fyf_until'], '2026-11-15');
  });

  testWidgets('bill paid in full posts without an amount', (tester) async {
    await pumpApp(tester, me: 'me_credit');
    await tester.tap(find.byTooltip('Profile').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Bill paid').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Record payment'));
    await tester.pumpAndSettle();
    expect(calls, contains('POST /me/cards/hdfc_millennia/bill-paid'));
    expect(sent['POST /me/cards/hdfc_millennia/bill-paid'], <String, dynamic>{});
    expect(find.text('Recorded: paid in full'), findsOneWidget);
  });

  testWidgets('spends: category total with merchants inside it and the "other" remainder', (tester) async {
    await pumpApp(tester, me: 'me_credit');
    await tester.tap(find.text('Finder'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Spends'));
    await tester.pumpAndSettle();
    // me_credit: dining ₹9,000 of which Swiggy ₹6,000 and Zomato ₹2,000 (merchants expanded because they have values).
    expect(find.text('₹1,000 other dining and food delivery'), findsOneWidget);
    final dining = find.ancestor(of: find.text('Dining and food delivery'), matching: find.byType(Card)).first;
    final swiggyRow = find.ancestor(of: find.descendant(of: dining, matching: find.text('Swiggy')), matching: find.byType(Row)).first;
    await tester.enterText(find.descendant(of: swiggyRow, matching: find.byType(TextField)), '8000');
    await tester.pumpAndSettle();
    expect(find.text('Merchants add up to ₹10,000, so that is the dining and food delivery total'), findsOneWidget);
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    final body = sent['PUT /me/spends'] as Map;
    expect(body['dining'], 900000);
    expect(body['swiggy'], 800000);
    expect(body['zomato'], 200000);
  });

  testWidgets('memberships: asked next to the card that uses them, saved as profile flags', (tester) async {
    await pumpApp(tester, fresh: true, me: 'me_empty', putMe: 'me');
    await tester.tap(find.text('Get started'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Search cards or banks'), 'Amazon Pay');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Amazon Pay ICICI Bank Credit Card'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('I have Amazon Prime'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    expect((sent['PUT /me/profile'] as Map)['flags'], ['amazon_prime']);
    // Preferences lists only memberships relevant to held cards, with the why.
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    expect(find.text('Amazon Prime member'), findsOneWidget);
    expect(find.textContaining('pays 5% on Amazon to Prime members'), findsOneWidget);
    expect(find.text('Tata NeuPass member'), findsNothing);
  });
}
