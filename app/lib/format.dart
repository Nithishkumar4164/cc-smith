/// Formatting helpers. Pure Dart (no Flutter import) so tests and the CLI smoke
/// script can use them.
library;

/// Indian digit grouping: 1234567 -> "12,34,567".
String groupIndian(int n) {
  final neg = n < 0;
  var s = n.abs().toString();
  if (s.length > 3) {
    final last3 = s.substring(s.length - 3);
    var rest = s.substring(0, s.length - 3);
    final parts = <String>[];
    while (rest.length > 2) {
      parts.insert(0, rest.substring(rest.length - 2));
      rest = rest.substring(0, rest.length - 2);
    }
    if (rest.isNotEmpty) parts.insert(0, rest);
    s = '${parts.join(',')},$last3';
  }
  return neg ? '-$s' : s;
}

/// Paise -> rupee string with Indian grouping. Whole rupees drop the decimals
/// ("₹1,00,000"); otherwise two decimals ("₹0.48"). Negative values use a
/// proper minus sign before the rupee symbol ("−₹5,180").
String rupees(int paise, {bool forceDecimals = false, bool signed = false}) {
  final neg = paise < 0;
  final abs = paise.abs();
  final whole = abs ~/ 100;
  final frac = abs % 100;
  var body = '₹${groupIndian(whole)}';
  if (frac != 0 || forceDecimals) body += '.${frac.toString().padLeft(2, '0')}';
  if (neg) return '−$body';
  if (signed && paise > 0) return '+$body';
  return body;
}

/// Parses a user-typed rupee amount ("1,200", "₹ 99.5") into paise. Returns
/// null when it is not a positive amount.
int? parseRupeesToPaise(String input) {
  final cleaned = input.replaceAll(RegExp(r'[₹,\s]'), '');
  if (cleaned.isEmpty) return null;
  final v = double.tryParse(cleaned);
  if (v == null || v < 0 || v.isNaN || v.isInfinite) return null;
  return (v * 100).round();
}

const _months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/// ISO timestamp -> "8 Oct 2026". Returns the input unchanged if unparseable.
String shortDate(String? iso) {
  if (iso == null || iso.isEmpty) return '—';
  final d = DateTime.tryParse(iso);
  if (d == null) return iso;
  final l = d.toLocal();
  return '${l.day} ${_months[l.month - 1]} ${l.year}';
}

/// Human period label for a cap/milestone period key.
String periodLabel(String period) => switch (period) {
      'statement_cycle' => 'statement cycle',
      'calendar_month' => 'month',
      'calendar_quarter' => 'quarter',
      'statement_quarter' => 'statement quarter',
      'anniversary_year' => 'card year',
      'calendar_year' => 'year',
      _ => period.replaceAll('_', ' '),
    };

/// Basis points -> "5%", "7.5%".
String bpPercent(int bp) {
  final whole = bp ~/ 100;
  final frac = bp % 100;
  if (frac == 0) return '$whole%';
  final f = frac.toString().padLeft(2, '0').replaceAll(RegExp(r'0+$'), '');
  return '$whole.$f%';
}

String plural(int n, String one, [String? many]) => n == 1 ? one : (many ?? '${one}s');
