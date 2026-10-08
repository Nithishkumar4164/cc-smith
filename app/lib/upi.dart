/// Parses UPI payment QR payloads (`upi://pay?pa=..&pn=..&mc=..&am=..`).
library;

class UpiPayment {
  final String payeeAddress; // pa (VPA)
  final String? payeeName; // pn
  final String? mcc; // mc, 4 digits
  final int? amountPaise; // am, rupees with up to 2 decimals

  const UpiPayment({required this.payeeAddress, this.payeeName, this.mcc, this.amountPaise});

  /// The best merchant string to send to /pay: the payee name, else the VPA handle.
  String get merchant {
    final n = payeeName?.trim();
    if (n != null && n.isNotEmpty) return n;
    return payeeAddress.split('@').first;
  }

  @override
  String toString() => 'UpiPayment(pa: $payeeAddress, pn: $payeeName, mc: $mcc, am: $amountPaise)';
}

/// Returns null if [raw] is not a UPI pay URI with a payee address.
UpiPayment? parseUpi(String raw) {
  final text = raw.trim();
  if (!text.toLowerCase().startsWith('upi://')) return null;
  Uri uri;
  try {
    uri = Uri.parse(text);
  } on FormatException {
    // Some QR generators leave raw spaces or stray '%' in pn; encode and retry.
    try {
      uri = Uri.parse(Uri.encodeFull(text));
    } on FormatException {
      return null;
    }
  }
  if (uri.host.toLowerCase() != 'pay') return null;
  // Query keys are case-insensitive in practice (some apps emit PA=, PN=).
  final q = <String, String>{};
  uri.queryParameters.forEach((k, v) => q[k.toLowerCase()] = v);
  final pa = q['pa']?.trim();
  if (pa == null || pa.isEmpty) return null;

  final mcRaw = q['mc']?.trim();
  final mcc = (mcRaw != null && RegExp(r'^\d{4}$').hasMatch(mcRaw) && mcRaw != '0000') ? mcRaw : null;

  int? amount;
  final am = q['am']?.trim();
  if (am != null && am.isNotEmpty) {
    final v = double.tryParse(am);
    if (v != null && v > 0) amount = (v * 100).round();
  }
  final pn = q['pn']?.trim();
  return UpiPayment(payeeAddress: pa, payeeName: (pn == null || pn.isEmpty) ? null : pn, mcc: mcc, amountPaise: amount);
}
