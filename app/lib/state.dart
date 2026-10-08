import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';
import 'models.dart';

const _kBaseUrl = 'base_url';
const _kUserId = 'user_id';
const _kOnboardedUser = 'onboarded_user';

/// Build-time override: `flutter build apk --dart-define=CC_SMITH_API=http://10.0.2.2:8001`.
const _apiOverride = String.fromEnvironment('CC_SMITH_API');

/// Android emulator reaches the host loopback at 10.0.2.2; web runs on the host.
String defaultBaseUrl() =>
    _apiOverride.isNotEmpty ? _apiOverride : (kIsWeb ? 'http://127.0.0.1:8000' : 'http://10.0.2.2:8000');

/// App-wide state: server address, the anonymous user, and cached catalogue data.
class AppState extends ChangeNotifier {
  final SharedPreferences _prefs;
  final http.Client? _client; // injectable for tests
  late String baseUrl;
  String? userId;
  Meta? meta;
  List<CardSummary>? cards;
  Me? me;
  Object? bootError;

  /// Bumped whenever holdings/spends/profile change so dependent screens reload.
  int dataVersion = 0;

  AppState(this._prefs, {http.Client? client}) : _client = client {
    baseUrl = _prefs.getString(_kBaseUrl) ?? defaultBaseUrl();
    userId = _prefs.getString(_kUserId);
  }

  Api get api => Api(baseUrl, userId: userId, client: _client);
  bool get onboarded => userId != null && me != null && _prefs.getString(_kOnboardedUser) == userId;

  Future<void> completeOnboarding() async {
    await _prefs.setString(_kOnboardedUser, userId!);
    notifyListeners();
  }

  Map<String, CardSummary> get cardsById => {for (final c in cards ?? const <CardSummary>[]) c.id: c};
  String cardName(String id) => cardsById[id]?.name ?? id;

  /// Loads catalogue data and, if we have a user, their state. A user unknown to
  /// the server (e.g. after a reseed) is forgotten so onboarding starts again.
  Future<void> boot() async {
    bootError = null;
    try {
      final a = api;
      final results = await Future.wait([a.meta(), a.cards()]);
      meta = results[0] as Meta;
      cards = results[1] as List<CardSummary>;
      if (userId != null) {
        try {
          me = await a.me();
        } on ApiException catch (e) {
          if (!e.unknownUser) rethrow;
          await _setUser(null);
        }
      }
    } catch (e) {
      bootError = e;
    }
    notifyListeners();
  }

  /// Something user-specific changed server-side (e.g. a logged payment).
  void bumpData() {
    dataVersion++;
    notifyListeners();
  }

  Future<void> refreshCatalogue() async {
    cards = await api.cards();
    notifyListeners();
  }

  Future<void> _setUser(String? id) async {
    userId = id;
    me = null;
    if (id == null) {
      await _prefs.remove(_kUserId);
    } else {
      await _prefs.setString(_kUserId, id);
    }
  }

  Future<void> ensureUser() async {
    if (userId != null && me != null) return;
    final id = await api.createUser();
    await _setUser(id);
    me = await api.me();
    notifyListeners();
  }

  Future<void> resetUser() async {
    await _setUser(null);
    dataVersion++;
    notifyListeners();
  }

  Future<void> setBaseUrl(String url) async {
    baseUrl = url.trim().replaceAll(RegExp(r'/+$'), '');
    await _prefs.setString(_kBaseUrl, baseUrl);
    meta = null;
    cards = null;
    me = null;
    await boot();
  }

  Future<void> _apply(Future<Me> f) async {
    me = await f;
    dataVersion++;
    notifyListeners();
  }

  Future<void> saveHoldings(List<Holding> h) => _apply(api.putHoldings(h));
  Future<void> saveSpends(Map<String, int> s) => _apply(api.putSpends(s));
  Future<void> saveProfile(Profile p) => _apply(api.putProfile(p));
}

class AppScope extends InheritedNotifier<AppState> {
  const AppScope({super.key, required AppState state, required super.child}) : super(notifier: state);

  static AppState of(BuildContext context) => context.dependOnInheritedWidgetOfExactType<AppScope>()!.notifier!;
  static AppState read(BuildContext context) => context.getInheritedWidgetOfExactType<AppScope>()!.notifier!;
}
