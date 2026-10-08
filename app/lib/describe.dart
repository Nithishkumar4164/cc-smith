/// Renders card-profile field values (knowledge/schema.py) as readable sentences.
/// Pure Dart. Unknown shapes fall back to a compact key: value rendering so new
/// backend fields never crash the app.
library;

import 'format.dart';
import 'models.dart';

/// One readable statement plus the verbatim official source(s) it came from.
class Line {
  final String text;
  final String? detail;
  final List<Ref> sources;
  const Line(this.text, {this.detail, this.sources = const []});
}

const fieldTitles = {
  'fees': 'Fees',
  'currency': 'Reward currency',
  'earn_rules': 'How you earn',
  'caps': 'Caps',
  'exclusions': 'Exclusions',
  'min_txn': 'Minimum transaction',
  'milestones': 'Milestone benefits',
  'identity': 'Card network',
};

/// Display order for known fields; unknown ones follow alphabetically.
const fieldOrder = ['earn_rules', 'caps', 'exclusions', 'milestones', 'fees', 'currency', 'min_txn', 'identity'];

String fieldTitle(String f) => fieldTitles[f] ?? f.replaceAll('_', ' ').replaceFirstMapped(RegExp(r'^.'), (m) => m[0]!.toUpperCase());

class Describer {
  final Meta? meta;
  final Map<String, FieldView> fields;
  Describer(this.fields, {this.meta});

  /// Element sources resolved against the field-level refs (which carry
  /// `official` and `fetched_at`).
  List<Ref> _sources(Object? item, String field) {
    final refs = fields[field]?.refs ?? const <Ref>[];
    if (item is! Map || item['src'] is! List) return refs;
    return (item['src'] as List).whereType<Map>().map((s) {
      final url = '${s['url']}';
      final quote = s['quote']?.toString();
      for (final r in refs) {
        if (r.url == url && (r.quote == quote || quote == null)) return r;
      }
      return Ref(url: url, quote: quote);
    }).toList();
  }

  String _names(List<dynamic>? keys) {
    if (keys == null || keys.isEmpty) return '';
    final names = keys.map((k) => meta?.shortLabel('$k') ?? '$k').toList();
    return _joinAnd(names);
  }

  String get _unit => _currency?['name']?.toString() ?? 'points';
  Map? get _currency => fields['currency']?.value as Map?;
  int? get _unitValuePaise => (_currency?['value_paise'] as num?)?.toInt();

  String rate(Map r) {
    if (r['kind'] == 'pct' && r['bp'] is num) return bpPercent((r['bp'] as num).toInt());
    if (r['kind'] == 'per_spend') {
      final pts = (r['points'] as num?)?.toInt() ?? 0;
      final per = (r['per_paise'] as num?)?.toInt() ?? 0;
      var s = '$pts $_unit per ${rupees(per)}';
      final v = _unitValuePaise;
      if (v != null && per > 0) {
        // effective value in basis points: pts * value / per * 10000
        final bp = (pts * v * 10000 / per).round();
        s += ' (≈${bpPercent(bp)} value)';
      }
      return s;
    }
    return r.toString();
  }

  String matchText(Map? m) {
    if (m == null) return 'on all spends';
    final merchants = _names(m['merchants'] as List?);
    final cats = _names(m['categories'] as List?);
    final channels = (m['channels'] as List? ?? []).map((c) => channelLabel('$c')).toList();
    final parts = <String>[];
    if (merchants.isNotEmpty) parts.add('at $merchants');
    if (cats.isNotEmpty) parts.add('on $cats');
    if (parts.isEmpty) parts.add('on all other spends');
    if (channels.isNotEmpty) parts.add('(${_joinAnd(channels)} only)');
    return parts.join(' ');
  }

  String capText(Map cap) {
    final amount = (cap['amount'] as num?)?.toInt() ?? 0;
    final per = periodLabel('${cap['period']}');
    return switch ('${cap['unit']}') {
      'paise' => 'capped at ${rupees(amount)} per $per',
      'points' => 'capped at ${groupIndian(amount)} $_unit per $per',
      'spend_paise' => 'on the first ${rupees(amount)} of spend per $per',
      _ => 'capped at $amount ${cap['unit']} per $per',
    };
  }

  Map? _capById(String id) {
    final caps = fields['caps']?.value;
    if (caps is! List) return null;
    for (final c in caps) {
      if (c is Map && c['id'] == id) return c;
    }
    return null;
  }

  List<Line> lines(String field) {
    final f = fields[field];
    if (f == null) return const [];
    return describeValue(field, f.value);
  }

  /// Also used for speculation values (which have the same shapes, minus refs).
  List<Line> describeValue(String field, Object? v) {
    switch (field) {
      case 'earn_rules' when v is List:
        return v.whereType<Map>().map((r) {
          final bits = <String>['${rate(r['rate'] as Map? ?? {})} ${matchText(r['match'] as Map?)}'];
          final caps = (r['cap_ids'] as List? ?? []).map((id) => _capById('$id')).whereType<Map>().map(capText);
          bits.addAll(caps);
          if (r['min_txn_paise'] is num) bits.add('min ${rupees((r['min_txn_paise'] as num).toInt())} per transaction');
          final req = (r['requires'] as List? ?? []).map((x) => flagLabel('$x')).toList();
          if (req.isNotEmpty) bits.add('${_joinAnd(req)} only');
          if (r['stacks'] == true) bits.add('on top of the base rate');
          return Line(_cap(bits.join(', ')), detail: r['note']?.toString(), sources: _sources(r, field));
        }).toList();
      case 'caps' when v is List:
        return v.whereType<Map>().map((c) {
          final rules = _rulesUsingCap('${c['id']}');
          final label = rules.isEmpty ? '' : ' (${_joinAnd(rules)})';
          return Line(_cap('${capText(c)}$label'), sources: _sources(c, field));
        }).toList();
      case 'exclusions' when v is List:
        return v.whereType<Map>().map((e) {
          final what = [
            _names(e['categories'] as List?),
            _names(e['merchants'] as List?),
            (e['channels'] as List? ?? []).map((c) => '${channelLabel('$c')} payments').join(', '),
          ].where((s) => s.isNotEmpty).join(', ');
          var s = 'No rewards on ${what.isEmpty ? 'some spends' : what}';
          final except = _names(e['except_merchants'] as List?);
          if (except.isNotEmpty) s += ' (except at $except)';
          final rules = (e['rule_ids'] as List? ?? []);
          if (rules.isNotEmpty) s += ' — applies to the ${rules.join(', ')} rate only';
          return Line(s, sources: _sources(e, field));
        }).toList();
      case 'milestones' when v is List:
        return v.whereType<Map>().map((m) {
          final spend = (m['spend_paise'] as num?)?.toInt() ?? 0;
          final value = (m['value_paise'] as num?)?.toInt() ?? 0;
          return Line(
            '${m['description'] ?? 'Milestone'}',
            detail: 'Spend ${rupees(spend)} in a ${periodLabel('${m['period']}')} · worth ${rupees(value)}',
            sources: _sources(m, field),
          );
        }).toList();
      case 'fees' when v is Map:
        final joining = (v['joining_paise'] as num?)?.toInt();
        final annual = (v['annual_paise'] as num?)?.toInt();
        final waiver = (v['waiver_spend_paise'] as num?)?.toInt();
        final parts = <String>[
          if (joining != null) 'Joining ${joining == 0 ? 'free' : rupees(joining)}',
          if (annual != null) 'Annual ${annual == 0 ? 'free' : rupees(annual)}',
        ];
        return [
          Line(parts.join(' · '),
              detail: waiver != null ? 'Annual fee waived on ${rupees(waiver)} spend in a year' : null,
              sources: _sources(v, field)),
        ];
      case 'currency' when v is Map:
        final value = (v['value_paise'] as num?)?.toInt();
        final kind = v['kind'] == 'cashback' ? 'Cashback' : 'Reward points';
        return [
          Line('${v['name']} ($kind)',
              detail: value != null ? '1 ${v['name']} is worth about ${rupees(value, forceDecimals: true)}' : null,
              sources: _sources(v, field)),
        ];
      case 'min_txn' when v is Map:
        final p = (v['min_txn_paise'] as num?)?.toInt();
        return [Line(p == null ? 'No minimum' : 'Rewards only on transactions of ${rupees(p)} or more', sources: _sources(v, field))];
      case 'identity' when v is Map:
        final parts = <String>[
          if (v['network'] != null) '${v['network']}',
          if (v['upi_rupay'] == true) 'RuPay on UPI supported',
          if (v['upi_rupay'] == false) 'Not usable on UPI',
        ];
        return [Line(parts.isEmpty ? '—' : parts.join(' · '), sources: _sources(v, field))];
    }
    return [Line(compact(v))];
  }

  List<String> _rulesUsingCap(String capId) {
    final rules = fields['earn_rules']?.value;
    if (rules is! List) return const [];
    return rules
        .whereType<Map>()
        .where((r) => (r['cap_ids'] as List? ?? []).contains(capId))
        .map((r) => matchText(r['match'] as Map?).replaceFirst(RegExp(r'^(at|on) '), ''))
        .toList();
  }
}

String channelLabel(String c) => switch (c) {
      'online' => 'online',
      'offline' => 'in-store',
      'upi' => 'UPI',
      _ => c,
    };

String flagLabel(String f) => switch (f) {
      'amazon_prime' => 'Amazon Prime members',
      _ => f.replaceAll('_', ' '),
    };

/// Readable label for a /pay reason code ("excluded:fuel", "capped", ...).
String reasonLabel(String code, {Meta? meta}) {
  final i = code.indexOf(':');
  final head = i < 0 ? code : code.substring(0, i);
  final arg = i < 0 ? null : code.substring(i + 1);
  final argLabel = arg == null ? null : (meta?.shortLabel(arg) ?? arg);
  return switch (head) {
    'excluded' => argLabel == null ? 'Excluded' : '$argLabel excluded',
    'capped' => 'Capped',
    'cap_exhausted' => 'Cap used up',
    'rounds_to_zero' => 'Rounds to ₹0',
    'no_matching_rule' => 'No reward rule matches',
    'below_min_txn' => 'Below minimum spend',
    'no_upi' => 'Not usable on UPI',
    'not_assessable' => 'Not enough official data',
    'requires' => argLabel == null ? 'Needs membership' : 'Needs ${flagLabel(arg!)}',
    _ => code.replaceAll('_', ' '),
  };
}

/// Compact readable rendering for unknown values.
String compact(Object? v) {
  if (v == null) return '—';
  if (v is Map) {
    return v.entries.where((e) => e.key != 'src').map((e) => '${e.key.toString().replaceAll('_', ' ')}: ${compact(e.value)}').join(' · ');
  }
  if (v is List) return v.map(compact).join('; ');
  return '$v';
}

String _joinAnd(List<String> xs) {
  if (xs.isEmpty) return '';
  if (xs.length == 1) return xs.first;
  if (xs.length <= 4) return '${xs.sublist(0, xs.length - 1).join(', ')} and ${xs.last}';
  return '${xs.take(3).join(', ')} and ${xs.length - 3} more';
}

String _cap(String s) => s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);
