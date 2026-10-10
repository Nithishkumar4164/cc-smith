// Renders each step of the user flows to PNG for the walkthrough page, against
// responses recorded from the real backend (test/storybook/fixtures).
// Run: flutter test --update-goldens test/storybook
import 'dart:convert';
import 'dart:io';

import 'package:app/main.dart';
import 'package:app/state.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

const dir = 'test/storybook/fixtures';
String fx(String n) => File('$dir/$n.json').readAsStringSync();
final uid = File('$dir/user_id.txt').readAsStringSync().trim();

Future<void> loadFonts() async {
  final flutterRoot = Platform.environment['FLUTTER_ROOT']!;
  final fonts = '$flutterRoot/bin/cache/artifacts/material_fonts';
  Future<void> load(String family, List<String> files) async {
    final loader = FontLoader(family);
    for (final f in files) {
      loader.addFont(Future.value(ByteData.view(File('$fonts/$f').readAsBytesSync().buffer)));
    }
    await loader.load();
  }

  await load('Roboto', ['Roboto-Regular.ttf', 'Roboto-Medium.ttf', 'Roboto-Bold.ttf', 'Roboto-Light.ttf', 'Roboto-Italic.ttf']);
  await load('MaterialIcons', ['MaterialIcons-Regular.otf']);
}

http.Client backend() => MockClient((req) async {
      final body = switch ((req.method, req.url.path)) {
        ('GET', '/meta') => fx('meta'),
        ('GET', '/cards') => fx('cards'),
        ('GET', '/me') => freshMe ? jsonEncode({...jsonDecode(fx('me')) as Map, 'holdings': [], 'pools': [], 'spends': {}, 'category_totals': {}}) : fx('me'),
        ('GET', '/me/transactions') => fx('transactions'),
        ('GET', '/me/notices') => fx('notices'),
        ('GET', '/me/credit') => fx('credit'),
        ('PUT', '/me/pools') => fx('me'),
        ('POST', final p) when p.endsWith('/bill-paid') => fx('credit'),
        ('GET', '/launches') => fx('launches'),
        ('GET', '/ops/changes') => fx('changes'),
        ('POST', '/users') => '{"user_id":"$uid"}',
        ('PUT', '/me/holdings' || '/me/spends' || '/me/profile') => fx('me'),
        ('POST', '/finder') => fx('finder'),
        ('POST', '/finder/assess') => '{"card_id":"x","gain_paise":0,"cards":[],"assessable":false}',
        ('POST', '/pay') => switch (jsonDecode(utf8.decode(req.bodyBytes))['merchant']) {
            'myntra.com' => fx('pay_offer'),
            'BPCL' => fx('pay_fuel'),
            'MakeMyTrip' => fx('pay_big'),
            _ => fx('pay_swiggy'),
          },
        ('POST', '/pay/confirm') => '{"txn_id":1,"reward_paise":12000}',
        ('GET', final p) when p.startsWith('/cards/') => fx('card_detail'),
        _ => null,
      };
      if (body == null) return http.Response('{"detail":"no fixture"}', 404);
      return http.Response.bytes(utf8.encode(body), 200, headers: {'content-type': 'application/json'});
    });

var freshMe = false;

Future<void> pumpApp(WidgetTester tester, {bool fresh = false}) async {
  freshMe = fresh;
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 2.625;
  addTearDown(tester.view.reset);
  SharedPreferences.setMockInitialValues(fresh ? {} : {'user_id': uid, 'onboarded_user': uid});
  final state = AppState(await SharedPreferences.getInstance(), client: backend());
  await tester.pumpWidget(AppScope(state: state, child: const CcSmithApp()));
  await state.boot();
  await tester.pumpAndSettle();
}

Future<void> shot(String name) =>
    expectLater(find.byType(CcSmithApp), matchesGoldenFile('shots/$name.png'));

// The page's vertical list, not a text field's own horizontal scrollable.
// Only the list on the visible route; pushed routes keep earlier pages in the tree.
final pageScroll = find.byWidgetPredicate((w) => w is Scrollable && w.axisDirection == AxisDirection.down).hitTestable();

Future<void> scroll(WidgetTester tester, double dy) async {
  await tester.drag(pageScroll.first, Offset(0, -dy));
  await tester.pumpAndSettle();
}

Future<void> reveal(WidgetTester tester, Finder f) async {
  for (var i = 0; i < 60 && f.hitTestable().evaluate().isEmpty; i++) {
    await tester.drag(pageScroll.first, const Offset(0, -150));
    await tester.pumpAndSettle();
  }
}

Future<void> setAmount(WidgetTester tester, String label, String value) async {
  await reveal(tester, find.text(label));
  await tester.pumpAndSettle();
  // Nearest Row around the visible label holds the label column and the amount field.
  final row = find.ancestor(of: find.text(label).hitTestable(), matching: find.byType(Row)).first;
  final field = find.descendant(of: row, matching: find.byType(TextField));
  if (field.evaluate().isNotEmpty) {
    await tester.enterText(field.first, value);
    return;
  }
  throw StateError('no amount field next to $label');
}

Future<void> ask(WidgetTester tester, String merchant, String amount) async {
  await tester.enterText(find.widgetWithText(TextField, 'Merchant'), merchant);
  await tester.enterText(find.widgetWithText(TextField, 'Amount'), amount);
  FocusManager.instance.primaryFocus?.unfocus();
  await tester.pumpAndSettle();
  await tester.tap(find.text('Find best card'));
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(loadFonts);

  testWidgets('onboarding', (tester) async {
    await pumpApp(tester, fresh: true);
    await shot('01_welcome');
    await tester.tap(find.text('Get started'));
    await tester.pumpAndSettle();
    for (final card in ['HDFC Bank Millennia Credit Card', 'HSBC Live+ Credit Card']) {
      await tester.enterText(find.widgetWithText(TextField, 'Search cards or banks'), card.split(' ')[card.startsWith('HSBC') ? 0 : 2]);
      await tester.pumpAndSettle();
      tester.widget<CheckboxListTile>(find.widgetWithText(CheckboxListTile, card)).onChanged!(true);
      await tester.pumpAndSettle();
    }
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pumpAndSettle();
    // HDFC Millennia shares an HDFC limit; Live+ has its own limit and a free first year.
    await tester.enterText(find.widgetWithText(TextField, 'Search cards or banks'), 'Millennia');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Limit, balance and fee').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Shares a limit'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('New shared limit'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Shared limit'), '200000');
    await tester.tap(find.text('Create'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Outstanding today'), '70000');
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pumpAndSettle();
    await shot('02b_credit_editor');
    await tester.ensureVisible(find.text('Done'));
    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Search cards or banks'), '');
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pumpAndSettle();
    await shot('02_cards_you_hold');
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    // Category totals; merchants are part of their category (Dining ₹9,000 of which Swiggy ₹6,000…).
    const amounts = {
      'Dining and food delivery': '9000', 'Groceries': '10000', 'Online shopping': '15000',
      'Travel (flights, hotels, cabs)': '8000', 'Fuel': '3000', 'Utilities and telecom': '4000',
      'Everything else (offline retail)': '10000',
    };
    for (final e in amounts.entries) {
      await setAmount(tester, e.key, e.value);
    }
    for (final (category, merchants) in const [
      ('Dining and food delivery', {'Swiggy': '6000', 'Zomato': '2000'}),
      ('Online shopping', {'Amazon': '6000', 'Flipkart': '4000'}),
    ]) {
      FocusManager.instance.primaryFocus?.unfocus();
      tester.state<ScrollableState>(pageScroll.first).position.jumpTo(0);
      await tester.pumpAndSettle();
      await reveal(tester, find.text(category));
      final card = find.ancestor(of: find.text(category), matching: find.byType(Card));
      final split = find.descendant(of: card, matching: find.textContaining('Split by merchant'));
      // Groups whose merchants already have amounts open expanded.
      if (split.evaluate().isNotEmpty) {
        await reveal(tester, split);
        await tester.tap(split.hitTestable().first);
        await tester.pumpAndSettle();
      }
      for (final m in merchants.entries) {
        await setAmount(tester, m.key, m.value);
      }
    }
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pumpAndSettle();
    await tester.drag(pageScroll.first, const Offset(0, 3000));
    await tester.pumpAndSettle();
    await reveal(tester, find.text('₹1,000 other dining and food delivery'));
    await shot('03b_spends_grouped');
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pumpAndSettle();
    await tester.drag(pageScroll.first, const Offset(0, 3000));
    await tester.pumpAndSettle();
    await shot('03_spends');
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    await shot('04_preferences');
    await tester.tap(find.text('Finish'));
    await tester.pumpAndSettle();
    await shot('05_pay_empty');
  });

  testWidgets('pay', (tester) async {
    await pumpApp(tester);
    await ask(tester, 'Swiggy', '1200');
    await shot('06_pay_swiggy');
    await scroll(tester, 700);
    await shot('07_pay_swiggy_ranked');
    await tester.tap(find.text('I paid with this').first);
    await tester.pumpAndSettle();
    await shot('08_pay_logged');
  });

  testWidgets('pay with bank offer', (tester) async {
    await pumpApp(tester);
    await ask(tester, 'myntra.com', '8000');
    await shot('09_pay_myntra');
    await scroll(tester, 650);
    await shot('10_pay_myntra_offers');
    await tester.tap(find.textContaining('Source · hdfc.bank.in').first);
    await tester.pumpAndSettle();
    await scroll(tester, 300);
    await shot('11_pay_offer_source');
  });

  testWidgets('pay at a fuel pump', (tester) async {
    await pumpApp(tester);
    await ask(tester, 'BPCL', '2000');
    await shot('12_pay_fuel');
  });

  testWidgets('finder', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.text('Finder'));
    await tester.pumpAndSettle();
    await shot('13_finder');
    await scroll(tester, 800);
    await shot('14_finder_detail');
    await scroll(tester, 1200);
    await shot('15_finder_keep_close');
  });

  testWidgets('cards', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.text('Cards'));
    await tester.pumpAndSettle();
    await shot('16_cards');
    await tester.enterText(find.widgetWithText(TextField, 'Search cards or banks'), 'millennia');
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pumpAndSettle();
    await tester.tap(find.text('HDFC Bank Millennia Credit Card').first);
    await tester.pumpAndSettle();
    await shot('17_card_detail');
    await tester.tap(find.textContaining('Source · ').first);
    await tester.pumpAndSettle();
    await shot('18_card_source');
  });

  testWidgets('market and profile', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.text('Market'));
    await tester.pumpAndSettle();
    await shot('19_market');
    await tester.tap(find.text('What changed'));
    await tester.pumpAndSettle();
    await shot('20_what_changed');
    await tester.tap(find.byTooltip('Profile').first);
    await tester.pumpAndSettle();
    await shot('21_profile');
  });

  testWidgets('notice board', (tester) async {
    await pumpApp(tester);
    await shot('22_nav_badge');
    await tester.tap(find.text('Notices'));
    await tester.pumpAndSettle();
    await shot('23_notices');
    await reveal(tester, find.text('Free year on HSBC Live+ Credit Card ends 15 Nov 2026'));
    final card = find.ancestor(of: find.text('Free year on HSBC Live+ Credit Card ends 15 Nov 2026'), matching: find.byType(Card));
    final src = find.descendant(of: card, matching: find.textContaining('Source · '));
    await reveal(tester, src);
    await tester.tap(src.hitTestable());
    await tester.pumpAndSettle();
    await scroll(tester, 250);
    await shot('24_notice_source');
    await scroll(tester, 900);
    await shot('25_notices_more');
  });

  testWidgets('credit', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.byTooltip('Profile').first);
    await tester.pumpAndSettle();
    await shot('26_credit');
    await tester.tap(find.text('Bill paid').first);
    await tester.pumpAndSettle();
    await shot('27_bill_paid');
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Edit cards you hold'));
    await tester.pumpAndSettle();
    await shot('28_cards_with_limits');
    await tester.tap(find.text('Limit, balance and fee').at(1));
    await tester.pumpAndSettle();
    await shot('29_live_plus_details');
  });

  testWidgets('pay beyond available credit', (tester) async {
    await pumpApp(tester);
    await ask(tester, 'MakeMyTrip', '140000');
    await scroll(tester, 500);
    await shot('30_pay_no_credit');
  });
}
