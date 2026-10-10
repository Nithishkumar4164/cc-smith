/// HTTP client for the cc-smith FastAPI backend. Pure Dart (package:http only).
library;

import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:http/http.dart' as http;

import 'models.dart';

class ApiException implements Exception {
  final int? status;
  final String message;

  /// Machine-readable reason when the server sends `{"detail": {"code": ...}}` (e.g. password_required).
  final String? code;
  const ApiException(this.message, {this.status, this.code});

  bool get unknownUser => status == 401;
  bool get unreachable => status == null;

  @override
  String toString() => message;
}

String? errorCode(String body) {
  try {
    final d = (jsonDecode(body) as Map)['detail'];
    return d is Map ? d['code']?.toString() : null;
  } catch (_) {
    return null;
  }
}

/// Turns a FastAPI error body into one readable sentence.
/// `{"detail": "text"}` or `{"detail": [{"loc": [...], "msg": "..."}]}`.
String describeError(int status, String body) {
  try {
    final j = jsonDecode(body);
    final d = j is Map ? j['detail'] : null;
    if (d is String) return d;
    if (d is Map && d['message'] != null) return '${d['message']}';
    if (d is List) {
      return d.map((e) {
        if (e is! Map) return '$e';
        final loc = (e['loc'] as List? ?? []).where((p) => p != 'body').map(_fieldName).join(' › ');
        final msg = '${e['msg'] ?? 'invalid'}';
        return loc.isEmpty ? msg : '$loc: $msg';
      }).join('; ');
    }
  } catch (_) {/* not JSON */}
  return switch (status) {
    404 => 'Not found',
    500 => 'The server hit an error. Try again.',
    _ => 'Request failed ($status)',
  };
}

String _fieldName(Object? p) => switch ('$p') {
      'amount_paise' => 'Amount',
      'merchant' => 'Merchant',
      'mcc' => 'MCC',
      'last4' => 'Last 4 digits',
      'statement_day' => 'Statement day',
      final s => s.replaceAll('_', ' '),
    };

/// Random 128-bit hex string for idempotency keys.
String newIdempotencyKey() {
  final r = Random.secure();
  return List.generate(16, (_) => r.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
}

class Api {
  final String baseUrl;
  final String? userId;
  final http.Client _client;
  final Duration timeout;

  Api(String baseUrl, {this.userId, http.Client? client, this.timeout = const Duration(seconds: 20)})
      : baseUrl = baseUrl.replaceAll(RegExp(r'/+$'), ''),
        _client = client ?? http.Client();

  Api withUser(String? id) => Api(baseUrl, userId: id, client: _client, timeout: timeout);

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-User-Id': ?userId,
      };

  Future<dynamic> _send(String method, String path, [Object? body]) async {
    final uri = Uri.parse('$baseUrl$path');
    final req = http.Request(method, uri)..headers.addAll(_headers);
    if (body != null) req.body = jsonEncode(body);
    return _dispatch(req);
  }

  /// Multipart PDF upload (statements, credit reports). The file goes only to our server.
  Future<dynamic> _upload(String path, List<int> bytes, String filename, Map<String, String> fields) async {
    final req = http.MultipartRequest('POST', Uri.parse('$baseUrl$path'))
      ..headers.addAll({'Accept': 'application/json', 'X-User-Id': ?userId})
      ..fields.addAll(fields)
      ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
    return _dispatch(req);
  }

  Future<dynamic> _dispatch(http.BaseRequest req) async {
    http.Response res;
    try {
      res = await http.Response.fromStream(await _client.send(req).timeout(timeout));
    } on TimeoutException {
      throw ApiException("The server at $baseUrl didn't answer in time.");
    } catch (_) {
      throw ApiException("Can't reach the server at $baseUrl. Is it running? You can change it in Profile › Settings.");
    }
    final text = utf8.decode(res.bodyBytes);
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return text.isEmpty ? null : jsonDecode(text);
    }
    throw ApiException(describeError(res.statusCode, text), status: res.statusCode, code: errorCode(text));
  }

  Json _map(Object? v) => Map<String, dynamic>.from(v as Map);
  List<Json> _maps(Object? v) => (v as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();

  Future<bool> health() async => (await _send('GET', '/health')) is Map;

  Future<String> createUser() async => _map(await _send('POST', '/users'))['user_id'] as String;

  Future<Meta> meta() async => Meta.fromJson(_map(await _send('GET', '/meta')));
  Future<List<CardSummary>> cards() async => _maps(await _send('GET', '/cards')).map(CardSummary.fromJson).toList();
  Future<CardDetail> card(String id) async =>
      CardDetail.fromJson(_map(await _send('GET', '/cards/${Uri.encodeComponent(id)}')));

  Future<Me> me() async => Me.fromJson(_map(await _send('GET', '/me')));
  Future<Me> putProfile(Profile p) async => Me.fromJson(_map(await _send('PUT', '/me/profile', p.toJson())));
  Future<Me> putHoldings(List<Holding> h) async =>
      Me.fromJson(_map(await _send('PUT', '/me/holdings', h.map((e) => e.toJson()).toList())));
  Future<Me> putSpends(Map<String, int> monthlyPaise) async =>
      Me.fromJson(_map(await _send('PUT', '/me/spends', monthlyPaise)));

  Future<Me> putPools(List<Pool> pools) async =>
      Me.fromJson(_map(await _send('PUT', '/me/pools', pools.map((p) => p.toJson()).toList())));
  Future<List<Credit>> credit() async => _maps(await _send('GET', '/me/credit')).map(Credit.fromJson).toList();

  /// [amountPaise] null = paid the full outstanding.
  Future<List<Credit>> billPaid(String cardId, {int? amountPaise}) async =>
      _maps(await _send('POST', '/me/cards/${Uri.encodeComponent(cardId)}/bill-paid', {'amount_paise': ?amountPaise}))
          .map(Credit.fromJson)
          .toList();
  /// Merge answers: true / false, or null to clear.
  Future<Me> putAnswers(Map<String, bool?> answers) async => Me.fromJson(_map(await _send('PUT', '/me/answers', answers)));
  // ---------- demo discovery and budget (simulated by the server; labelled "Demo" in the UI) ----------
  Future<Json> bureauStart(String phone) async =>
      _map(await _send('POST', '/me/discovery/bureau/start', {'phone': phone, 'consent': true}));
  Future<Json> bureauVerify(String requestId, String otp) async =>
      _map(await _send('POST', '/me/discovery/bureau/verify', {'request_id': requestId, 'otp': otp}));
  /// Names the product from the card number's first 6 digits and runs the ₹1 check. The full
  /// number never leaves the phone: only the first 6 and the last 4 are sent.
  Future<Json> cardCheck(String lender, String last4, String bin) async =>
      _map(await _send('POST', '/me/discovery/card', {'lender': lender, 'last4': last4, 'bin': bin}));
  Future<Budget> budget() async => Budget.fromJson(_map(await _send('GET', '/me/budget')));
  Future<(int, Budget)> importBudgetDemo() async {
    final j = _map(await _send('POST', '/me/budget/import-demo', {'sources': ['sms', 'email']}));
    return ((j['transactions'] as num?)?.toInt() ?? 0, Budget.fromJson(Map<String, dynamic>.from(j['budget'] as Map)));
  }

  /// Pins lines to a monthly amount; null unpins (back to auto).
  Future<Budget> putBudget(Map<String, int?> lines) async => Budget.fromJson(_map(await _send('PUT', '/me/budget', lines)));
  Future<List<Notice>> marketOffers() async => _maps(await _send('GET', '/me/market/offers')).map(Notice.fromJson).toList();

  // ---------- capture ----------
  Future<Json> uploadStatement(List<int> bytes, String filename, {String? password, String? cardId}) async => _map(await _upload(
        '/me/capture/statement',
        bytes,
        filename,
        {if (password != null && password.isNotEmpty) 'password': password, 'card_id': ?cardId},
      ));
  Future<Json> uploadCreditReport(List<int> bytes, String filename, {String? password}) async => _map(await _upload(
        '/me/capture/credit-report',
        bytes,
        filename,
        {'consent': 'true', if (password != null && password.isNotEmpty) 'password': password},
      ));
  Future<Json> postEvents(List<Json> events) async => _map(await _send('POST', '/me/capture/events', events));
  Future<Json> captureStatus() async => _map(await _send('GET', '/me/capture/status'));
  Future<Json> gmailAuthUrl() async => _map(await _send('GET', '/me/capture/gmail/auth-url'));
  Future<Json> gmailCallback(String code, {String? state}) async =>
      _map(await _send('POST', '/me/capture/gmail/callback', {'code': code, 'state': ?state}));
  Future<Json> gmailSync() async => _map(await _send('POST', '/me/capture/gmail/sync'));
  Future<void> gmailDisconnect() async => _send('DELETE', '/me/capture/gmail');

  Future<List<Notice>> notices() async => _maps(await _send('GET', '/me/notices')).map(Notice.fromJson).toList();

  Future<FinderReport> finder({int maxNew = 3}) async =>
      FinderReport.fromJson(_map(await _send('POST', '/finder', {'max_new': maxNew})));

  Future<AssessResult> assess(String cardId) async =>
      AssessResult.fromJson(_map(await _send('POST', '/finder/assess', {'card_id': cardId})));

  Future<PayResult> pay({required String merchant, required int amountPaise, String? channel, String? mcc}) async =>
      PayResult.fromJson(_map(await _send('POST', '/pay', {
        'merchant': merchant,
        'amount_paise': amountPaise,
        'channel': ?channel,
        'mcc': ?mcc,
      })));

  /// Returns the reward recorded, in paise.
  Future<int> confirm({
    required String cardId,
    required String merchant,
    required int amountPaise,
    required String idempotencyKey,
    String? channel,
    String? mcc,
  }) async {
    final j = _map(await _send('POST', '/pay/confirm', {
      'card_id': cardId,
      'merchant': merchant,
      'amount_paise': amountPaise,
      'idempotency_key': idempotencyKey,
      'channel': ?channel,
      'mcc': ?mcc,
    }));
    return (j['reward_paise'] as num).toInt();
  }

  Future<List<Transaction>> transactions() async =>
      _maps(await _send('GET', '/me/transactions')).map(Transaction.fromJson).toList();

  Future<List<Launch>> launches() async => _maps(await _send('GET', '/launches')).map(Launch.fromJson).toList();

  Future<List<ChangeEvent>> changes({int limit = 50}) async =>
      _maps(await _send('GET', '/ops/changes?limit=$limit')).map(ChangeEvent.fromJson).toList();

  Future<void> report(String cardId, {required String field, required String message, String? evidenceUrl}) async {
    await _send('POST', '/cards/${Uri.encodeComponent(cardId)}/report', {
      'field': field,
      'message': message,
      if (evidenceUrl != null && evidenceUrl.isNotEmpty) 'evidence_url': evidenceUrl,
    });
  }
}
