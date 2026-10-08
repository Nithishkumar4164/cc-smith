import 'package:app/format.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('rupees (Indian grouping, paise in)', () {
    test('whole rupees drop decimals', () {
      expect(rupees(0), '₹0');
      expect(rupees(100), '₹1');
      expect(rupees(99900), '₹999');
      expect(rupees(100000), '₹1,000');
      expect(rupees(10000000), '₹1,00,000');
      expect(rupees(1234567800), '₹1,23,45,678');
      expect(rupees(100000000000), '₹1,00,00,00,000');
    });
    test('fractional rupees keep two decimals', () {
      expect(rupees(48), '₹0.48');
      expect(rupees(12345), '₹123.45');
      expect(rupees(1000005), '₹10,000.05');
      expect(rupees(100, forceDecimals: true), '₹1.00');
    });
    test('negative and signed', () {
      expect(rupees(-518000), '−₹5,180');
      expect(rupees(122000, signed: true), '+₹1,220');
      expect(rupees(0, signed: true), '₹0');
    });
  });

  test('groupIndian', () {
    expect(groupIndian(999), '999');
    expect(groupIndian(1000), '1,000');
    expect(groupIndian(100000), '1,00,000');
    expect(groupIndian(-1234567), '-12,34,567');
  });

  test('parseRupeesToPaise', () {
    expect(parseRupeesToPaise('1,200'), 120000);
    expect(parseRupeesToPaise('₹ 99.5'), 9950);
    expect(parseRupeesToPaise('0.01'), 1);
    expect(parseRupeesToPaise(''), isNull);
    expect(parseRupeesToPaise('abc'), isNull);
    expect(parseRupeesToPaise('-5'), isNull);
  });

  test('bpPercent and periods', () {
    expect(bpPercent(500), '5%');
    expect(bpPercent(750), '7.5%');
    expect(bpPercent(125), '1.25%');
    expect(periodLabel('calendar_month'), 'month');
    expect(periodLabel('statement_cycle'), 'statement cycle');
  });

  test('shortDate', () {
    expect(shortDate('2026-10-08T10:37:33.360091+00:00'), contains('Oct 2026'));
    expect(shortDate(null), '—');
  });
}
