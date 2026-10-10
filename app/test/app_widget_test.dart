// Drives the real widget tree against recorded backend responses (fixtures).
import 'dart:convert';
import 'dart:io';

import 'package:app/main.dart';
import 'package:app/screens/capture.dart';
import 'package:app/widgets.dart';
import 'package:app/state.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

String fx(String n) => File('test/fixtures/$n.json').readAsStringSync();

final vScroll = find.byWidgetPredicate((w) => w is Scrollable && w.axisDirection == AxisDirection.down).hitTestable().first;

Future<void> tapIn(WidgetTester tester, Finder f) async {
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
  await tester.tap(f);
  await tester.pumpAndSettle();
}

void main() {
  late List<String> calls;
  late Map<String, Object?> sent; // last JSON body per 'METHOD /path'
  var meFixture = 'me';
  var putMeFixture = 'me';
  var answers = <String, bool>{};
  var payFixture = '';
  var budgetFixture = '{"month":"2026-10","adapted_from":null,"lines":[],"total_paise":0}';
  String meJson(String name) => jsonEncode({...jsonDecode(fx(name)) as Map, 'answers': answers});

  http.Client backend() => MockClient((req) async {
        calls.add('${req.method} ${req.url.path}');
        if (req.bodyBytes.isNotEmpty && (req.headers['content-type'] ?? '').contains('json')) sent['${req.method} ${req.url.path}'] = jsonDecode(utf8.decode(req.bodyBytes));
        final body = switch ((req.method, req.url.path)) {
          ('GET', '/meta') => fx('meta'),
          ('GET', '/cards') => fx('cards'),
          ('GET', '/me') => meJson(meFixture),
          ('PUT', '/me/answers') => () {
              (jsonDecode(utf8.decode(req.bodyBytes)) as Map).forEach((k, v) => v == null ? answers.remove(k) : answers[k as String] = v as bool);
              return meJson(putMeFixture);
            }(),
          ('GET', '/me/notices') => fx('contract/notices'),
          ('GET', '/me/market/offers') => fx('contract/market_offers'),
          ('POST', '/me/discovery/bureau/start') => fx('contract/bureau_start'),
          ('POST', '/me/discovery/bureau/verify') => fx('contract/bureau_verify'),
          ('GET', '/me/budget') => budgetFixture,
          ('POST', '/me/budget/import-demo') => () {
              budgetFixture = fx('contract/budget');
              return fx('contract/budget_import');
            }(),
          ('PUT', '/me/budget') => () {
              final body = jsonDecode(utf8.decode(req.bodyBytes)) as Map;
              budgetFixture = body.values.first == null ? fx('contract/budget') : fx('contract/budget_pinned');
              return budgetFixture;
            }(),
          ('GET', '/me/credit') => fx('credit'),
          ('PUT', '/me/pools') => fx(meFixture),
          ('POST', final p) when p.endsWith('/bill-paid') => fx('credit'),
          ('GET', '/me/transactions') => fx('transactions'),
          ('GET', '/launches') => fx('launches'),
          ('GET', '/ops/changes') => '[]',
          ('POST', '/users') => '{"user_id":"048460289250402db2f1775e98fcfee5"}',
          ('PUT', '/me/holdings' || '/me/spends' || '/me/profile') => meJson(putMeFixture),
          ('POST', '/finder') => fx('finder'),
          ('POST', '/me/capture/statement') => fx('capture/statement'),
          ('POST', '/me/capture/credit-report') => fx('capture/credit_report'),
          ('GET', '/me/capture/status') => fx('capture/status'),
          ('POST', '/finder/assess') => '{"card_id":"x","gain_paise":0,"cards":[],"assessable":false}',
          ('POST', '/pay') => payFixture.isNotEmpty
              ? fx(payFixture)
              : (jsonDecode(utf8.decode(req.bodyBytes))['merchant'] == 'myntra.com' ? fx('pay_offer') : fx('pay')),
          ('POST', '/pay/confirm') => '{"txn_id":1,"reward_paise":6000}',
          ('GET', final p) when p.startsWith('/cards/') => fx('card_detail'),
          _ => null,
        };
        if (req.url.path == '/me/capture/statement' && !utf8.decode(req.bodyBytes, allowMalformed: true).contains('name="password"')) {
          return http.Response('{"detail":{"code":"password_required","message":"this PDF is password-protected; send the password"}}', 422);
        }
        if (req.url.path == '/me/capture/gmail/auth-url') {
          return http.Response(File('test/fixtures/capture/gmail_auth_url.txt').readAsStringSync().split(' 503').first, 503);
        }
        if (body == null) return http.Response('{"detail":"no fixture"}', 404);
        return http.Response.bytes(utf8.encode(body), 200, headers: {'content-type': 'application/json'});
      });

  Future<AppState> pumpApp(WidgetTester tester, {bool fresh = false, String me = 'me', String? putMe, bool finderPrefs = true}) async {
    calls = [];
    sent = {};
    meFixture = me;
    answers = {};
    payFixture = '';
    budgetFixture = '{"month":"2026-10","adapted_from":null,"lines":[],"total_paise":0}';
    putMeFixture = putMe ?? me;
    SharedPreferences.setMockInitialValues(fresh
        ? {}
        : {
            'user_id': '048460289250402db2f1775e98fcfee5',
            'onboarded_user': '048460289250402db2f1775e98fcfee5',
            if (finderPrefs) 'finder_prefs_user': '048460289250402db2f1775e98fcfee5',
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
    await tester.tap(find.text('Launch Radar'));
    await tester.pumpAndSettle();
    expect(find.text('Reported, not confirmed by the bank'), findsWidgets);
    await tester.scrollUntilVisible(find.text('New variant of Scapia Federal Bank Credit Card'), 300,
        scrollable: vScroll);
    expect(find.text('New variant of Scapia Federal Bank Credit Card'), findsOneWidget);

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
    await tester.tap(find.text('Read my SMS & email'));
    await tester.pumpAndSettle();
    // Two steps only: reward type and fee ceiling are asked later, in Card Finder.
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    expect(find.text('Checkout Advisor'), findsOneWidget);
    expect(calls, containsAllInOrder(['POST /users', 'PUT /me/holdings', 'POST /me/budget/import-demo']));
    expect(calls, isNot(contains('PUT /me/profile')));
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
    expect(app.attentionCount, 3);
    expect(find.descendant(of: find.byType(NavigationBar), matching: find.text('3')), findsOneWidget);
    await tester.tap(find.text('Notices'));
    await tester.pumpAndSettle();
    expect(find.text('3 to keep an eye on'), findsOneWidget);
    // Notices are only about the user's own cards (+ launches worth it for them); fee offers moved to Market.
    expect(find.textContaining('Swiggy ORNGE'), findsNothing);
    expect(find.text('New in the market: Axis Bank ACE Credit Card would earn you about ₹3,400 a year'), findsOneWidget);
    expect(find.text('₹3,400 at stake'), findsOneWidget);
    // Utilisation is general guidance: grey tag, no source expander.
    await tester.scrollUntilVisible(find.textContaining('35% of the HDFC shared limit'), 300, scrollable: vScroll);
    final util = find.ancestor(of: find.textContaining('35% of the HDFC shared limit'), matching: find.byType(Card));
    expect(find.descendant(of: util, matching: find.text('General guidance')), findsOneWidget);
    expect(find.descendant(of: util, matching: find.textContaining('Source')), findsNothing);
    await tester.scrollUntilVisible(find.text('Free year on HSBC Live+ Credit Card ends 15 Nov 2026'), 300,
        scrollable: vScroll);
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
    await tester.tap(find.text('Enter manually'));
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

  testWidgets('memberships: asked next to the card that uses them, saved as answers', (tester) async {
    await pumpApp(tester, fresh: true, me: 'me_empty', putMe: 'me');
    await tester.tap(find.text('Get started'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Search cards or banks'), 'Amazon Pay');
    await tester.pumpAndSettle();
    await tapIn(tester, find.text('Amazon Pay ICICI Bank Credit Card'));
    expect(find.text('Do you have Amazon Prime?'), findsOneWidget);
    await tester.tap(find.text('Yes'));
    await tester.pumpAndSettle();
    expect(sent['PUT /me/answers'], {'amazon_prime': true});
    expect(find.text('You said Yes'), findsOneWidget);
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Read my SMS & email'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    // Profile › Memberships: only memberships relevant to held cards, with the answer shown.
    await tester.tap(find.byTooltip('Profile').first);
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.byIcon(Icons.card_membership), 300, scrollable: vScroll);
    await tapIn(tester, find.byIcon(Icons.card_membership));
    expect(find.text('Do you have Amazon Prime?'), findsOneWidget);
    expect(find.text('You said Yes'), findsOneWidget);
    expect(find.textContaining('NeuPass'), findsNothing);
  });

  testWidgets('Market › Offers for you: answering No moves an offer into "Not for you"; unanswered stay visible', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.text('Market'));
    await tester.pumpAndSettle();
    expect(find.text('Offers for you'), findsOneWidget);
    final q = find.text("Does your employer appear on HDFC Bank's list of select corporates?");
    await tester.scrollUntilVisible(q, 300, scrollable: vScroll);
    final ask = find.ancestor(of: q, matching: find.byType(ConditionAsk));
    await tapIn(tester, find.descendant(of: ask, matching: find.text('No')));
    expect(sent['PUT /me/answers'], {'select_corporate_employee': false});
    await tester.scrollUntilVisible(find.text('Not for you (1)'), 300, scrollable: vScroll);
    expect(find.text('Not for you (1)'), findsOneWidget);
    // The Magnus offer is still unanswered, so it stays in the main list with its question.
    expect(find.textContaining('Axis Bank Magnus Credit Card: Lifetime free'), findsOneWidget);
  });

  testWidgets('pay: "₹250 if yes" asks Prime inline and re-runs Pay; up-to offers say "at most"', (tester) async {
    await pumpApp(tester);
    payFixture = 'pay_amazon_ifans';
    await tester.enterText(find.widgetWithText(TextField, 'Merchant'), 'Amazon');
    await tester.enterText(find.widgetWithText(TextField, 'Amount'), '5000');
    await tester.tap(find.text('Find best card'));
    await tester.pumpAndSettle();
    final lead = find.text('₹250 on Amazon Pay ICICI Bank Credit Card if yes');
    await tester.scrollUntilVisible(lead, 300, scrollable: vScroll);
    final pays = calls.where((c) => c == 'POST /pay').length;
    await tapIn(tester, find.descendant(of: find.ancestor(of: lead, matching: find.byType(ConditionAsk)), matching: find.text('Yes')));
    expect(sent['PUT /me/answers'], {'amazon_prime': true});
    expect(calls.where((c) => c == 'POST /pay').length, pays + 1);

    payFixture = 'pay_upto';
    await tester.drag(vScroll, const Offset(0, 3000));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Merchant'), 'MakeMyTrip');
    await tester.enterText(find.widgetWithText(TextField, 'Amount'), '30000');
    await tester.tap(find.text('Find best card'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('₹4,500 off at most'), 300, scrollable: vScroll);
    expect(find.textContaining('(about)'), findsNothing);
    expect(find.textContaining('the actual discount depends on the offer terms'), findsWidgets);
  });

  testWidgets('statement upload: asks for the PDF password, then shows what we read and the new credit', (tester) async {
    await pumpApp(tester, me: 'me_credit');
    await tester.tap(find.byTooltip('Profile').first);
    await tester.pumpAndSettle();
    await tester.pumpWidget(AppScope(
      state: AppScope.read(tester.element(find.byType(Scaffold).first)),
      child: MaterialApp(home: DataSourcesScreen(picker: () async => (utf8.encode('%PDF-1.4 test'), 'statement.pdf'))),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Upload a statement'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('HDFC Bank Millennia Credit Card'));
    await tester.pumpAndSettle();
    expect(find.text('Statement password'), findsOneWidget);
    await tester.enterText(find.byType(TextField).last, 'TEST1234');
    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();
    expect(find.text('Confirm what we read'), findsOneWidget);
    expect(find.text('Applied to HDFC Bank Millennia Credit Card'), findsOneWidget);
    expect(find.text('₹36,786'), findsWidgets);
    expect(find.text('₹2,00,000'), findsWidgets);
    expect(find.text('15 Sep 2026'), findsOneWidget);
    expect(calls.where((c) => c == 'POST /me/capture/statement').length, 2);
    expect(calls, contains('GET /me/credit'));
  });

  testWidgets('credit report: consent first, then score, accounts to add, enquiries', (tester) async {
    await pumpApp(tester, me: 'me_credit');
    await tester.pumpWidget(AppScope(
      state: AppScope.read(tester.element(find.byType(Scaffold).first)),
      child: MaterialApp(home: DataSourcesScreen(picker: () async => (utf8.encode('%PDF-1.4 test'), 'cibil.pdf'))),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Upload a credit report'));
    await tester.pumpAndSettle();
    expect(find.text('Choose the PDF'), findsOneWidget);
    expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Choose the PDF')).onPressed, isNull);
    await tapIn(tester, find.byType(Checkbox));
    await tapIn(tester, find.text('Choose the PDF'));
    expect(find.text('782'), findsOneWidget);
    expect(find.text('CIBIL SCORE'), findsOneWidget);
    expect(find.text('In your cards: HDFC Bank Millennia Credit Card'), findsOneWidget);
    expect(find.text('Which card is this?'), findsWidgets);
    expect(find.text('Add these cards'), findsOneWidget);
    expect(find.text('Use these limits'), findsOneWidget);
  });

  testWidgets('Gmail not configured shows the server message plainly', (tester) async {
    await pumpApp(tester, me: 'me_credit');
    await tester.pumpWidget(AppScope(
      state: AppScope.read(tester.element(find.byType(Scaffold).first)),
      child: const MaterialApp(home: DataSourcesScreen()),
    ));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Connect Gmail'), 300, scrollable: vScroll);
    await tapIn(tester, find.text('Connect Gmail'));
    expect(find.textContaining('Gmail is not available yet: Google OAuth client JSON not found'), findsOneWidget);
  });

  testWidgets('onboarding: find my cards with the demo bureau (code shown and prefilled)', (tester) async {
    await pumpApp(tester, fresh: true, me: 'me_empty', putMe: 'me_credit');
    await tester.tap(find.text('Get started'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Find my cards'));
    await tester.pumpAndSettle();
    expect(find.textContaining('demo', findRichText: true), findsNothing);
    await tester.enterText(find.widgetWithText(TextField, 'Mobile number'), '9876543210');
    await tester.tap(find.byType(Checkbox));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    expect(sent['POST /me/discovery/bureau/start'], {'phone': '9876543210', 'consent': true});
    expect(find.text('Code sent to +91 9876543210. Filled in automatically from the SMS.'), findsOneWidget);
    expect(tester.widget<TextField>(find.widgetWithText(TextField, 'One-time code')).controller!.text, '123456');
    await tester.tap(find.text('Verify and find my cards'));
    await tester.pumpAndSettle();
    expect(sent['POST /me/discovery/bureau/verify'], {'request_id': 'req_demo_1', 'otp': '123456'});
    expect(find.text('Your cards'), findsOneWidget);
    expect(find.textContaining(RegExp('demo|simulated', caseSensitive: false)), findsNothing);
    expect(find.text('782'), findsOneWidget);
    // The bureau names each product, when it was opened and the catalogue's fee: nothing to pick.
    expect(find.text('Which card is this?'), findsNothing);
    expect(find.text('HDFC Bank Millennia Credit Card'), findsOneWidget);
    expect(find.text('HDFC BANK ••4321 · since Mar 2019 · ₹1,180/yr fee'), findsOneWidget);
    expect(find.text('ICICI BANK ••8765 · since Jul 2021 · no annual fee'), findsOneWidget);
    await tapIn(tester, find.text('Add these cards'));
    final put = (sent['PUT /me/holdings'] as List).cast<Map>();
    // The closed SBI account is not added; the fee month follows the open date.
    expect(put.map((h) => h['card_id']), ['hdfc_millennia', 'icici_amazon_pay']);
    expect(put.map((h) => h['renewal_month']), [3, 7]);
    expect(put.map((h) => h['fee_status']), ['standard', 'standard']);
    expect(put.map((h) => h['balance_paise']), [3678600, 1200000]);
  });

  testWidgets('budget: demo import fills it, edit pins a line, reset unpins', (tester) async {
    await pumpApp(tester, fresh: true, me: 'me_empty', putMe: 'me_credit');
    await tester.tap(find.text('Get started'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Search cards or banks'), 'Millennia');
    await tester.pumpAndSettle();
    await tester.tap(find.text('HDFC Bank Millennia Credit Card'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    expect(find.text('Read my SMS & email'), findsOneWidget);
    expect(find.text('Enter manually'), findsOneWidget);
    await tester.tap(find.text('Read my SMS & email'));
    await tester.pumpAndSettle();
    expect(sent['POST /me/budget/import-demo'], {'sources': ['sms', 'email']});
    expect(find.text('Read 148 card transactions from last month\'s SMS and email.'), findsOneWidget);
    expect(find.textContaining(RegExp('demo|simulated', caseSensitive: false)), findsNothing);
    expect(find.text('BUDGET FOR OCTOBER 2026 · ₹59,000'), findsOneWidget);
    expect(find.textContaining('September 2026'), findsOneWidget);
    expect(find.text('Auto'), findsWidgets);
    expect(find.text('Edited'), findsOneWidget); // online is pinned in the fixture
    await tapIn(tester, find.text('Dining and food delivery'));
    await tester.enterText(find.widgetWithText(TextField, 'Monthly budget'), '10000');
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    expect(sent['PUT /me/budget'], {'dining': 1000000});
    expect(find.text('Edited'), findsNWidgets(2));
    await tapIn(tester, find.byTooltip('Reset to auto').first);
    expect(sent['PUT /me/budget'], {'dining': null});
    expect(find.text('Edited'), findsOneWidget);
  });

  testWidgets('finder: first visit asks reward type and fee, saves the profile, then shows results; tune icon edits later', (tester) async {
    await pumpApp(tester, finderPrefs: false);
    await tester.tap(find.text('Finder'));
    await tester.pumpAndSettle();
    expect(find.text('Find my best cards'), findsOneWidget);
    expect(find.text('Do you have Amazon Prime?'), findsNothing);
    expect(calls, isNot(contains('GET /me/finder')));
    await tester.tap(find.text('Cashback'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Find my best cards'));
    await tester.pumpAndSettle();
    expect((sent['PUT /me/profile'] as Map)['reward_preference'], 'cashback');
    expect(find.text('₹12,760/yr net'), findsOneWidget);
    await tester.tap(find.byTooltip('Finder preferences'));
    await tester.pumpAndSettle();
    expect(find.text('Finder preferences'), findsOneWidget);
    expect(find.text('Reward type you prefer'.toUpperCase()).evaluate().isNotEmpty || find.text('Reward type you prefer').evaluate().isNotEmpty, isTrue);
  });

  testWidgets('card fee: shows the bank fee from the catalogue; Custom saves the amount the user pays', (tester) async {
    await pumpApp(tester, me: 'me_credit');
    await tester.tap(find.byTooltip('Profile').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Edit cards you hold'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Search cards or banks'), 'Millennia');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Limit, balance and fee').first);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Custom'));
    await tester.tap(find.text('Standard'));
    await tester.pumpAndSettle();
    expect(find.text("The bank's fee: ₹1,180 a year including GST."), findsOneWidget);
    await tester.tap(find.text('Custom'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Annual fee you pay'), '500');
    await tester.ensureVisible(find.text('Done'));
    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Fee ₹500/yr'), findsWidgets);
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    final m = (sent['PUT /me/holdings'] as List).firstWhere((h) => h['card_id'] == 'hdfc_millennia');
    expect(m['fee_status'], 'custom');
    expect(m['annual_fee_paise'], 50000);
  });
}
