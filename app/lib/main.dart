import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'screens/cards.dart';
import 'screens/finder.dart';
import 'screens/market.dart';
import 'screens/pay.dart';
import 'screens/profile.dart';
import 'state.dart';
import 'widgets.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final state = AppState(prefs);
  runApp(AppScope(state: state, child: const CcSmithApp()));
  state.boot();
}

/// Deep teal brand with a warm saffron accent: calm, and reads as "money" without
/// shouting.
const _seed = Color(0xFF0E5E6F);

ThemeData _theme(Brightness b) {
  final scheme = ColorScheme.fromSeed(
    seedColor: _seed,
    brightness: b,
    tertiary: b == Brightness.light ? const Color(0xFF8A5100) : const Color(0xFFFFB86B),
  );
  return ThemeData(
    colorScheme: scheme,
    useMaterial3: true,
    scaffoldBackgroundColor: scheme.surface,
    appBarTheme: AppBarTheme(backgroundColor: scheme.surface, scrolledUnderElevation: 1, centerTitle: false),
    cardTheme: CardThemeData(
      elevation: 0,
      color: scheme.surfaceContainerLow,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: BorderSide(color: scheme.outlineVariant.withValues(alpha: 0.5))),
      margin: const EdgeInsets.symmetric(vertical: 6),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: scheme.surfaceContainerHighest.withValues(alpha: 0.5),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
    ),
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
  );
}

class CcSmithApp extends StatelessWidget {
  const CcSmithApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'cc-smith',
        debugShowCheckedModeBanner: false,
        theme: _theme(Brightness.light),
        darkTheme: _theme(Brightness.dark),
        themeMode: ThemeMode.system,
        home: const RootGate(),
      );
}

class RootGate extends StatelessWidget {
  const RootGate({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    if (app.meta == null && app.bootError == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (app.meta == null) {
      return Scaffold(
        body: SafeArea(
          child: EmptyState(
            icon: Icons.cloud_off_outlined,
            title: "Can't reach cc-smith",
            message: '${app.bootError}',
            action: Wrap(spacing: 12, children: [
              FilledButton.icon(onPressed: app.boot, icon: const Icon(Icons.refresh), label: const Text('Retry')),
              OutlinedButton.icon(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen())),
                icon: const Icon(Icons.settings_outlined),
                label: const Text('Server settings'),
              ),
            ]),
          ),
        ),
      );
    }
    if (!app.onboarded) return const OnboardingScreen();
    return const HomeShell();
  }
}

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _tab = 0;

  void goTo(int i) => setState(() => _tab = i);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _tab, children: [
        const PayScreen(),
        const FinderScreen(),
        const CardsScreen(),
        const MarketScreen(),
        const ProfileScreen(),
      ]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: goTo,
        destinations: const [
          NavigationDestination(icon: Icon(Icons.point_of_sale_outlined), selectedIcon: Icon(Icons.point_of_sale), label: 'Pay'),
          NavigationDestination(icon: Icon(Icons.auto_awesome_outlined), selectedIcon: Icon(Icons.auto_awesome), label: 'Finder'),
          NavigationDestination(icon: Icon(Icons.credit_card_outlined), selectedIcon: Icon(Icons.credit_card), label: 'Cards'),
          NavigationDestination(icon: Icon(Icons.radar_outlined), selectedIcon: Icon(Icons.radar), label: 'Market'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}
