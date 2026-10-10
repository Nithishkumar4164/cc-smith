/// Dart port of backend/src/cc_smith/capture/alerts.py: parses Indian card / bank
/// transaction alert text ON THE PHONE so only parsed fields leave the device (DR-2).
/// Both implementations must pass test/fixtures/alert_vectors.json (copied from
/// backend/fixtures/alerts/vectors.json). Pure Dart.
library;

class Alert {
  final int amountPaise;
  final String currency;
  final String? last4, merchantText, ts, issuerHint;
  final String kind; // debit | credit | refund | payment_received
  final String instrument; // credit_card | debit_card | account | card
  const Alert({
    required this.amountPaise,
    required this.currency,
    this.last4,
    this.merchantText,
    this.ts,
    required this.kind,
    this.issuerHint,
    required this.instrument,
  });

  Map<String, Object?> toJson() => {
    'amount_paise': amountPaise,
    'currency': currency,
    'last4': last4,
    'merchant_text': merchantText,
    'ts': ts,
    'kind': kind,
    'issuer_hint': issuerHint,
    'instrument': instrument,
  };
}

RegExp _re(String p, {bool i = true, bool s = false}) => RegExp(p, caseSensitive: !i, dotAll: s);

// ---------- privacy ----------
final _panRun = RegExp(r'(?<![\d])(?:\d{12,19}|\d{4}([ \-])\d{4}\1\d{4}\1\d{1,7}|\d{4}([ \-])\d{6}\2\d{4,5})(?![\d])');
final _digitRun = RegExp(r'\d{12,}');
bool hasLongDigitRun(String v) => _digitRun.hasMatch(v) || _panRun.hasMatch(v);
String stripLongDigitRuns(String t) => t.replaceAll(_panRun, '');

// ---------- issuer ----------
final _issuerWords = <(RegExp, String)>[
  (_re(r'\bhdfc\s*bank\b|\bhdfcbank\b|\bhdfc\b'), 'hdfc_bank'),
  (_re(r'\bicici\b'), 'icici_bank'),
  (_re(r'\bsbi\s*cards?\b|\bsbi\s+credit\s+card\b|\bsbicard\b|\bsbi\s+cardholder\b'), 'sbi_card'),
  (_re(r'\baxis\s*bank\b|\baxis\b'), 'axis_bank'),
  (_re(r'\bhsbc\b|hongkong\s+and\s+shanghai'), 'hsbc_india'),
  (_re(r'\bkotak\b'), 'kotak_mahindra_bank'),
  (_re(r'\bidfc\b|\bfirst\s+(?:wealth|millennia|classic|select|wow)\b'), 'idfc_first_bank'),
  (_re(r'\bkiwi\b'), 'yes_bank'),
  (_re(r'\byes\s*bank\b|\byesbank\b'), 'yes_bank'),
  (_re(r'\bau\s+(?:small\s+finance\s+)?bank\b|\baubank\b'), 'au_small_finance_bank'),
];
const _senderCodes = {
  'HDFCBK': 'hdfc_bank', 'HDFCCC': 'hdfc_bank', 'ICICIB': 'icici_bank', 'ICICIT': 'icici_bank',
  'SBICRD': 'sbi_card', 'SBIPSG': 'sbi_card', 'SBICAR': 'sbi_card', 'AXISBK': 'axis_bank', 'AXISCC': 'axis_bank',
  'HSBCIN': 'hsbc_india', 'HSBCBK': 'hsbc_india', 'KOTAKB': 'kotak_mahindra_bank', 'KOTAKD': 'kotak_mahindra_bank',
  'IDFCFB': 'idfc_first_bank', 'IDFCBK': 'idfc_first_bank', 'YESBNK': 'yes_bank', 'YESBCC': 'yes_bank',
  'AUBANK': 'au_small_finance_bank', 'AUBKCC': 'au_small_finance_bank', 'GOKIWI': 'yes_bank',
};
const _senderDomains = {
  'hdfcbank.net': 'hdfc_bank', 'hdfcbank.com': 'hdfc_bank', 'hdfc.bank.in': 'hdfc_bank', 'hdfcbank.bank.in': 'hdfc_bank',
  'icicibank.com': 'icici_bank', 'icici.bank.in': 'icici_bank', 'sbicard.com': 'sbi_card',
  'axisbank.com': 'axis_bank', 'axis.bank.in': 'axis_bank', 'hsbc.co.in': 'hsbc_india', 'hsbc.bank.in': 'hsbc_india',
  'kotak.com': 'kotak_mahindra_bank', 'kotak.bank.in': 'kotak_mahindra_bank',
  'idfcfirstbank.com': 'idfc_first_bank', 'idfcfirst.bank.in': 'idfc_first_bank',
  'yesbank.in': 'yes_bank', 'yes.bank.in': 'yes_bank', 'aubank.in': 'au_small_finance_bank', 'au.bank.in': 'au_small_finance_bank',
};

String? issuerFromSender(String? sender) {
  if (sender == null) return null;
  final s = sender.trim();
  if (s.contains('@')) {
    final domain = _strip(s.substring(s.lastIndexOf('@') + 1), ' >').toLowerCase();
    for (final e in _senderDomains.entries) {
      if (domain == e.key || domain.endsWith('.${e.key}')) return e.value;
    }
    return null;
  }
  for (final part in s.toUpperCase().split(RegExp(r'[-_ ]'))) {
    if (_senderCodes.containsKey(part)) return _senderCodes[part];
  }
  return null;
}

String? issuerFromText(String text) {
  (int, String)? best;
  for (final (rx, issuer) in _issuerWords) {
    final m = rx.firstMatch(text);
    if (m != null && (best == null || m.start < best.$1)) best = (m.start, issuer);
  }
  return best?.$2;
}

// ---------- normalise ----------
/// The NFKC folds that matter for alerts: Mathematical Alphanumeric letters/digits
/// (SBI Card's 𝗌𝗉𝖾𝗇𝗍), fullwidth ASCII and no-break spaces.
String foldCompat(String text) {
  final out = StringBuffer();
  for (final cp in text.runes) {
    if (cp >= 0x1D400 && cp <= 0x1D6A3) {
      final i = (cp - 0x1D400) % 52;
      out.writeCharCode(i < 26 ? 0x41 + i : 0x61 + i - 26);
    } else if (cp >= 0x1D7CE && cp <= 0x1D7FF) {
      out.writeCharCode(0x30 + (cp - 0x1D7CE) % 10);
    } else if (cp >= 0xFF01 && cp <= 0xFF5E) {
      out.writeCharCode(cp - 0xFEE0);
    } else if (cp == 0x00A0 || cp == 0x202F || cp == 0x2007 || (cp >= 0x2000 && cp <= 0x200A)) {
      out.write(' ');
    } else {
      out.writeCharCode(cp);
    }
  }
  return out.toString();
}

String normalise(String text) {
  var t = foldCompat(text).replaceAll('\r', '\n');
  t = stripLongDigitRuns(t);
  return t
      .split('\n')
      .map((ln) => ln.replaceAll(RegExp(r'[ \t]+'), ' ').trim())
      .where((ln) => ln.isNotEmpty)
      .join('\n');
}

String _strip(String s, String chars) {
  var a = 0, b = s.length;
  while (a < b && chars.contains(s[a])) {
    a++;
  }
  while (b > a && chars.contains(s[b - 1])) {
    b--;
  }
  return s.substring(a, b);
}

// ---------- skip ----------
final _notATransaction = _re(
  r'\bOTP\b|one[- ]time password|verification code|\bis due\b|\bdue (?:by|on)\b|payment due date'
  r'|statement (?:for|of) .{0,40}(?:generated|is ready)|\bdeclined\b|\bfailed\b|\bunsuccessful\b|has been blocked'
  r'|will be (?:debited|charged)|\bmandate\b|requested (?:money|payment)|collect request|\bbill alert\b',
);
final _promo = _re(r'\boffers?\b|\bapply now\b|\bpre-?approved\b|\bcashback offer\b|limit (?:has been )?(?:increased|enhanced)');

// ---------- amount ----------
const _cur = r'(?<cur>INR|Rs|₹|USD|EUR|GBP|SGD|AED|AUD|CAD|JPY|CHF|THB|MYR|HKD)';
final _amountRx = _re(_cur + r'\s*\.?\s*:?\s*(?<num>\d[\d,]*(?:\.\d{1,2})?|\.\d{1,2})(?![\d])');
final _notTxnAmount = _re(r'(?:limit|lmt|bal|balance|outstanding|due|available|avl|avbl)\W{0,3}(?:is\s+|of\s+)?\W{0,3}$');

int _paise(String num) {
  final n = num.replaceAll(',', '');
  final dot = n.indexOf('.');
  final rupees = dot < 0 ? n : n.substring(0, dot);
  final frac = dot < 0 ? '' : n.substring(dot + 1);
  return int.parse(rupees.isEmpty ? '0' : rupees) * 100 + int.parse('${frac}00'.substring(0, 2));
}

(int, String)? _amount(String t) {
  for (final m in _amountRx.allMatches(t)) {
    final before = t.substring(m.start - 25 < 0 ? 0 : m.start - 25, m.start);
    if (_notTxnAmount.hasMatch(before)) continue;
    final paise = _paise(m.namedGroup('num')!);
    if (paise <= 0) continue;
    final cur = m.namedGroup('cur')!.toUpperCase();
    return (paise, (cur == 'RS' || cur == '₹' || cur == 'INR') ? 'INR' : cur);
  }
  final m = _re(r'debited by (\d[\d,]*(?:\.\d{1,2})?) on date').firstMatch(t);
  if (m != null) return (_paise(m.group(1)!), 'INR');
  return null;
}

// ---------- card / account ----------
final _cardLast4 = _re(
  r'(?:credit\s*card|creditcard|debit\s*card|card)(?:\s+account)?\s*(?:no\.?|number|num)?\s*'
  r'(?:ending\s*(?:with|in)?)?\s*[:#\-]?\s*[0-9xX*•.]*?(?<l4>\d{4})(?!\d)',
);
final _endingLast4 = _re(r'\bending\s*(?:with|in)?\s*[xX*•.]*(?<l4>\d{4})(?!\d)');
final _blockLast4 = _re(r'\bBLOCK\s*(?:CC|PCC|DC|CARD)?\s*(?:XX)?(?<l4>\d{4})(?!\d)');
final _accountLast4 = _re(r'(?:a/c|acct|account|\bac)\s*(?:no\.?)?\s*[xX*]*(?<l4>\d{3,4})(?!\d)');
final _cardWord = _re(r'credit\s*card|creditcard|\bcard\b|\bcardmember\b|\bcardholder\b');
final _creditCard = _re(
    r'credit\s*card|creditcard|\bcardmember\b|\bcardholder\b|BLOCK\s*P?CC\b|CCBLOCK|BLKCC|\bAvl\.?\s*(?:Limit|Lmt)\b|\bAvbl\.?\s*Limit\b|available limit');
final _debitCard = _re(r'debit\s*card|BLOCK\s*DC\b|from\s+HDFC\s+Bank\s+Card');
final _account = _re(r'\ba/c\b|\bacct\b|\baccount\b|\bAC\s+X|\bupi user\b');

String _instrument(String t) {
  if (_debitCard.hasMatch(t)) return 'debit_card';
  if (_creditCard.hasMatch(t)) return 'credit_card';
  if (_cardWord.hasMatch(t) && !_account.hasMatch(t)) return 'card';
  if (_account.hasMatch(t)) return 'account';
  return _cardWord.hasMatch(t) ? 'card' : 'account';
}

String? _last4(String t, String instrument) {
  if (instrument == 'account') return _accountLast4.firstMatch(t)?.namedGroup('l4');
  for (final rx in [_cardLast4, _endingLast4, _blockLast4]) {
    final m = rx.firstMatch(t);
    if (m != null) return m.namedGroup('l4');
  }
  return null;
}

// ---------- kind ----------
final _refund = _re(r'\brefund|\brevers(?:ed|al)\b');
final _paymentReceived = _re(
  r'payment\s+of\b.{0,80}?\b(?:received|credited|processed)|thank you for (?:your )?payment|received (?:a |your )?payment'
  r'|payment\s+(?:has been\s+)?(?:received|credited)|we have received a payment',
  s: true,
);
final _debitVerb = _re(r'\bspent\b|\bdebited\b|\bused\b|\btxn\b(?! reversal)|\bpurchase\b|\bpaid\b|\bsent\b|\bdeducted\b|\btransaction of\b|\bwithdrawn\b|\bcharged\b'
    r'|\bfor using\b|\btransaction (?:amount|alert)\b');
final _creditVerb = _re(r'\bcredited\b|\breceived\b|\bdeposited\b|\bsent to your\b');

String? _kind(String t, String instrument) {
  if (_refund.hasMatch(t)) return 'refund';
  if (instrument != 'account' && _paymentReceived.hasMatch(t) && !_re(r'\bfrom\s+(?:your\s+)?a/c\b').hasMatch(t)) {
    return 'payment_received';
  }
  final d = _debitVerb.firstMatch(t), c = _creditVerb.firstMatch(t);
  if (c != null && _re(r'sent to your').matchAsPrefix(c.group(0)!) != null) return 'credit';
  if (d != null && (c == null || d.start <= c.start)) return 'debit';
  if (c != null) return 'credit';
  return null;
}

// ---------- date ----------
const _mon = r'(?<mon>jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*';
final _dates = [
  RegExp(r'(?<y>\d{4})-(?<m>\d{1,2})-(?<d>\d{1,2})(?:[:T ](?<H>\d{1,2}):(?<M>\d{2})(?::(?<S>\d{2}))?)?'),
  _re(r'(?<![\d/])(?<d>\d{1,2})[-/ ]' + _mon + r'[-/ ,]+(?<y>\d{4}|\d{2})(?![\d])'),
  _re(r'(?<![\d])(?<d>\d{1,2})' + _mon + r'(?<y>\d{2,4})(?![\d])'),
  _re(r'\b' + _mon + r'\s+(?<d>\d{1,2}),?\s+(?<y>\d{4})'),
  RegExp(r'(?<![\d/:.,])(?<d>\d{1,2})[-/.](?<m>\d{1,2})[-/.](?<y>\d{4}|\d{2})(?![\d/])'),
  RegExp(r'(?<![\d/:.,])(?<d>\d{1,2})-(?<m>\d{1,2})(?![\d/\-:.])'),
];
final _time = _re(r'(?:[ ,]+(?:at\s+)?|_?)(?<H>\d{1,2}):(?<M>\d{2})(?::(?<S>\d{2}))?(?:\s*(?<ap>[ap]\.?m\.?))?');
const _months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];

String? _group(RegExpMatch m, String name) => m.groupNames.contains(name) ? m.namedGroup(name) : null;

String _two(int v) => v.toString().padLeft(2, '0');

/// IST wall-clock date for an instant.
DateTime _istDate(DateTime instant) {
  final u = instant.toUtc().add(const Duration(hours: 5, minutes: 30));
  return DateTime.utc(u.year, u.month, u.day);
}

bool _validDate(int y, int m, int d) {
  if (m < 1 || m > 12 || d < 1) return false;
  final dt = DateTime.utc(y, m, d);
  return dt.year == y && dt.month == m && dt.day == d;
}

String? _ts(String t, DateTime? receivedAt) {
  final ref = _istDate(receivedAt ?? DateTime.now());
  final found = <RegExpMatch>[];
  for (final rx in _dates) {
    final m = rx.firstMatch(t);
    if (m != null) found.add(m);
  }
  found.sort((a, b) => a.start.compareTo(b.start));
  for (final m in found) {
    final mon = _group(m, 'mon');
    int month, day, year;
    try {
      month = mon != null ? _months.indexOf(mon.toLowerCase().substring(0, 3)) + 1 : int.parse(_group(m, 'm')!);
      day = int.parse(_group(m, 'd')!);
      final y = _group(m, 'y');
      if (y != null) {
        year = int.parse(y);
        if (year < 100) year += 2000;
      } else {
        year = ref.year;
        if (_validDate(year, month, day) && DateTime.utc(year, month, day).isAfter(ref.add(const Duration(days: 1)))) year -= 1;
      }
    } catch (_) {
      continue;
    }
    if (!_validDate(year, month, day)) continue;
    var hh = 0, mm = 0, ss = 0;
    if (_group(m, 'H') != null) {
      hh = int.parse(_group(m, 'H')!);
      mm = int.parse(_group(m, 'M')!);
      ss = int.parse(_group(m, 'S') ?? '0');
    } else {
      final tm = _time.matchAsPrefix(t, m.end) as RegExpMatch?;
      if (tm != null) {
        hh = int.parse(tm.namedGroup('H')!);
        mm = int.parse(tm.namedGroup('M')!);
        ss = int.parse(tm.namedGroup('S') ?? '0');
        final ap = (tm.namedGroup('ap') ?? '').toLowerCase().replaceAll('.', '');
        if (ap == 'pm' && hh < 12) {
          hh += 12;
        } else if (ap == 'am' && hh == 12) {
          hh = 0;
        }
      }
    }
    if (hh > 23 || mm > 59 || ss > 59) hh = mm = ss = 0;
    return '${year.toString().padLeft(4, '0')}-${_two(month)}-${_two(day)}T${_two(hh)}:${_two(mm)}:${_two(ss)}+05:30';
  }
  return null;
}

// ---------- merchant ----------
const _end = r'(?=\s+(?:on|for|was|by|via|ref|avl|avbl|info|using|with|txn|if|not|card|dated?|at\s+\d)\b|\s*[.;](?:\s|$)|\n|$|\s+\d{1,2}[-/]\d{1,2}[-/]\d{2,4})';
final _merchantPatterns = [
  _re(r'Merchant Name\s*:?\s*(?<m>[^\n]+)'),
  _re(r'\bInfo\s*:\s*(?<m>[^\n.]+)'),
  _re(r'\brefunded by (?<m>.+?)' + _end),
  _re(r'\bfrom (?<m>.+?) refunded\b'),
  RegExp(r'^(?<m>[A-Za-z][^\n]{1,60}?) refund of\b', caseSensitive: false),
  _re(r'\b(?:used|spent|purchase|paid|transaction|txn|reversal)\b[^\n]*?\bat\s+(?<m>.+?)' + _end),
  _re(r'(?:^|\n|\s)at\s+(?<m>.+?)' + _end),
  _re(r'@\s*(?:UPI_)?(?<m>[^@\n]+?)(?=\s+\d{1,2}-\d{1,2}-\d{2,4}|\s+on\b|\.\s|\n|$)'),
  _re(r'\btowards (?!your\b)(?<m>.+?)' + _end),
  _re(r'\bon \d{1,2}-[A-Za-z]{3}-\d{2,4} on (?<m>.+?)' + _end),
  _re(r'\bBy (?<m>.+?)\s+On\s+\d'),
  _re(r';\s*(?<m>[^;\n]+?) credited\b'),
  _re(r'\btrf to (?<m>.+?) Ref'),
  _re(r'\bto (?!your\b|a/c\b)(?<m>[^\n]+?)(?=\s+(?:using|via|from)\b|\s+on\s+\d)'),
  _re(r'\nTo (?<m>[^\n]+)\nOn\b'),
  _re(r'\n\d{2}-\d{2}-\d{2,4},?\s+\d{2}:\d{2}:\d{2}(?:\s*IST)?\n(?<m>[^\n]+)'),
];
final _badMerchant = _re(r'^(?:https?:|www\.|\d{1,2}:\d{2}|your\b|the\b|card\b|a/c\b|\d+$|rs\b|inr\b)');

String? _cleanMerchant(String raw) {
  var m = _strip(raw, ' .,:;-*');
  if (m.contains('@') && !m.contains(' ')) m = m.split('@').first.replaceAll(RegExp(r'[._\-]+'), ' ');
  m = m.replaceFirst(_re(r'^(?:UPI[-_/ ]+(?:P2[AM][-_/ ]+)?)+'), '');
  m = m.replaceFirst(RegExp(r'(?:\s+\d{1,6})+$'), '');
  m = m.replaceAll(RegExp(r'[-_/]{2,}'), '-');
  m = _strip(m.replaceAll(RegExp(r'\s{2,}'), ' '), ' .,:;-*');
  if (m.length < 2 || _badMerchant.hasMatch(m)) return null;
  return m.length > 80 ? m.substring(0, 80) : m;
}

String? _merchant(String t) {
  for (final rx in _merchantPatterns) {
    for (final m in rx.allMatches(t)) {
      final c = _cleanMerchant(m.namedGroup('m')!);
      if (c != null) return c;
    }
  }
  return null;
}

// ---------- entry point ----------
/// Null when the text is not a completed transaction (OTP, reminder, promo, decline) or has no amount.
Alert? parseAlert(String text, {String? sender, DateTime? receivedAt}) {
  if (text.trim().isEmpty) return null;
  final t = normalise(text);
  if (_notATransaction.hasMatch(t) && !_refund.hasMatch(t) && !_paymentReceived.hasMatch(t)) return null;
  if (_promo.hasMatch(t) && !(_debitVerb.hasMatch(t) || _creditVerb.hasMatch(t))) return null;
  final amt = _amount(t);
  if (amt == null) return null;
  final instrument = _instrument(t);
  final kind = _kind(t, instrument);
  if (kind == null) return null;
  return Alert(
    amountPaise: amt.$1,
    currency: amt.$2,
    last4: _last4(t, instrument),
    merchantText: kind == 'payment_received' ? null : _merchant(t),
    ts: _ts(t, receivedAt),
    kind: kind,
    issuerHint: issuerFromSender(sender) ?? issuerFromText(t),
    instrument: instrument,
  );
}
