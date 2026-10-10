/// Phone notification capture (Android): the Kotlin listener streams bank / UPI app
/// notifications here; they are parsed ON DEVICE and only the parsed fields are posted
/// to POST /me/capture/events — never the notification text, never 12–19 digit runs.
library;

import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'alerts.dart';
import 'api.dart';

const _kEnabled = 'notif_capture_enabled';

/// Issuer for a notifying app, when the text itself does not name the bank.
const packageIssuers = {
  'com.snapwork.hdfc': 'hdfc_bank',
  'com.hdfcbank.payzapp': 'hdfc_bank',
  'com.csam.icici.bank.imobile': 'icici_bank',
  'com.sbicard.sbicard': 'sbi_card',
  'com.axis.mobile': 'axis_bank',
  'com.hsbc.hsbcindia': 'hsbc_india',
  'com.msf.kbank.mobile': 'kotak_mahindra_bank',
  'com.idfcfirstbank.optimus': 'idfc_first_bank',
  'com.yesbank': 'yes_bank',
  'in.gokiwi.app': 'yes_bank',
  'com.aubank.aubankapp': 'au_small_finance_bank',
};

/// A digits-free id for a notification, so re-sends are idempotent and the id can never
/// look like a card number.
String eventId(String key, int postTime) {
  final h = '$key|$postTime'.hashCode.toUnsigned(32).toRadixString(16).padLeft(8, '0');
  final letters = String.fromCharCodes(h.codeUnits.map((c) => c >= 0x30 && c <= 0x39 ? c - 0x30 + 0x67 : c));
  return 'n-$letters-${key.length}';
}

/// Parsed, privacy-checked event for one notification, or null to drop it.
Map<String, Object?>? eventFromNotification(Map<dynamic, dynamic> n) {
  final pkg = '${n['package'] ?? ''}';
  final text = [n['title'], n['text']].where((e) => e != null && '$e'.isNotEmpty).join('\n');
  final postTime = (n['postTime'] as num?)?.toInt() ?? DateTime.now().millisecondsSinceEpoch;
  final alert = parseAlert(text, receivedAt: DateTime.fromMillisecondsSinceEpoch(postTime));
  if (alert == null) return null;
  final merchant = alert.merchantText == null ? null : stripLongDigitRuns(alert.merchantText!).trim();
  final e = <String, Object?>{
    'id': eventId('${n['key'] ?? pkg}', postTime),
    'amount_paise': alert.amountPaise,
    'currency': alert.currency,
    'last4': alert.last4,
    'merchant_text': (merchant == null || merchant.isEmpty) ? null : merchant,
    'ts': alert.ts,
    'kind': alert.kind,
    'issuer_hint': alert.issuerHint ?? packageIssuers[pkg],
    'instrument': alert.instrument,
  };
  // Belt and braces: nothing that looks like a card number leaves the phone.
  if (e.values.whereType<String>().any(hasLongDigitRun)) return null;
  return e;
}

class NotificationCapture {
  static const _methods = MethodChannel('cc_smith/notifications');
  static const _events = EventChannel('cc_smith/notification_events');

  final SharedPreferences _prefs;
  final Api Function() _api;
  StreamSubscription<dynamic>? _sub;
  int sent = 0;

  NotificationCapture(this._prefs, this._api);

  bool get supported => !kIsWeb && defaultTargetPlatform == TargetPlatform.android;
  bool get enabled => _prefs.getBool(_kEnabled) ?? false;

  Future<bool> hasAccess() async => supported && (await _methods.invokeMethod<bool>('hasAccess') ?? false);
  Future<void> openAccessSettings() async {
    if (supported) await _methods.invokeMethod('openSettings');
  }

  Future<void> enable() async {
    await _prefs.setBool(_kEnabled, true);
    await start();
  }

  Future<void> disable() async {
    await _prefs.setBool(_kEnabled, false);
    await _sub?.cancel();
    _sub = null;
    if (supported) await _methods.invokeMethod('setEnabled', false);
  }

  /// Called at boot when enabled, and after the user turns it on.
  Future<void> start() async {
    if (!supported || !enabled || _sub != null) return;
    await _methods.invokeMethod('setEnabled', true);
    _sub = _events.receiveBroadcastStream().listen((n) async {
      if (n is! Map) return;
      final e = eventFromNotification(n);
      if (e == null) return;
      try {
        await _api().postEvents([e]);
        sent++;
      } catch (_) {/* best effort; the statement reconciles anything missed */}
    });
  }
}
