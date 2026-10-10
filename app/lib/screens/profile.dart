import 'package:flutter/material.dart';

import '../api.dart';
import '../format.dart';
import '../models.dart';
import '../state.dart';
import '../widgets.dart';
import 'budget.dart';
import 'capture.dart';
import 'discovery.dart';
import 'editors.dart';

export 'editors.dart';


// ---------------------------------------------------------------- onboarding

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});
  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  int _step = 0;
  bool _busy = false;

  Future<void> _start() async {
    setState(() => _busy = true);
    try {
      await AppScope.read(context).ensureUser();
      setState(() => _step = 1);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    // A returning user with an account but no cards resumes at step 1.
    final step = (_step == 0 && app.userId != null && app.me != null) ? 1 : _step;
    final t = Theme.of(context);
    if (step == 0) {
      return Scaffold(
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Spacer(),
              Icon(Icons.credit_card, size: 56, color: t.colorScheme.primary),
              const SizedBox(height: 20),
              Text('cc-smith', style: t.textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w800, color: t.colorScheme.primary)),
              const SizedBox(height: 12),
              Text('Which card to pay with, and which cards to get — in rupees, with the bank\'s own words behind every number.',
                  style: t.textTheme.titleMedium),
              const SizedBox(height: 24),
              for (final (icon, text) in const [
                (Icons.point_of_sale, 'At checkout: the card that earns the most, and by how much'),
                (Icons.auto_awesome, 'The 1–3 cards that would earn you the most a year'),
                (Icons.radar, 'New cards in the market, scored against your spends'),
                (Icons.verified_outlined, 'Facts only from official bank pages. No affiliate links.'),
              ])
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Row(children: [
                    Icon(icon, size: 20, color: t.colorScheme.tertiary),
                    const SizedBox(width: 12),
                    Expanded(child: Text(text)),
                  ]),
                ),
              const Spacer(),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _busy ? null : _start,
                  style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
                  child: _busy ? const SizedBox.square(dimension: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Get started'),
                ),
              ),
              const SizedBox(height: 8),
            ]),
          ),
        ),
      );
    }
    final titles = ['', 'Cards you hold', 'What you spend each month'];
    return Scaffold(
      appBar: AppBar(
        title: Text(titles[step]),
        leading: step > 1 ? BackButton(onPressed: () => setState(() => _step = step - 1)) : null,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(4),
          child: LinearProgressIndicator(value: step / 2),
        ),
      ),
      body: switch (step) {
        1 => Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: Card(
              color: Theme.of(context).colorScheme.primaryContainer,
              child: ListTile(
                leading: const Icon(Icons.travel_explore),
                title: const Text('Find my cards'),
                subtitle: const Text('From your credit bureau, with your mobile number and a one-time code'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const BureauDiscoveryScreen())),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
            child: Text('or pick manually', style: Theme.of(context).textTheme.labelMedium),
          ),
          Expanded(
            child: HoldingsEditor(
              // Rebuilt when the bureau flow adds cards, so they show as selected.
              key: ValueKey(app.me?.holdings.map((h) => h.cardId).join(',')),
              actionLabel: 'Next',
              onSaved: () => setState(() => _step = 2),
              requireOne: true,
            ),
          ),
        ]),
        // Reward type and fee ceiling are asked the first time the user opens Card Finder.
        _ => BudgetPanel(onNext: () => AppScope.read(context).completeOnboarding()),
      },
    );
  }
}

// ---------------------------------------------------------------- profile tab

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  void _push(BuildContext context, String title, Widget Function(VoidCallback done) body) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (ctx) => Scaffold(appBar: AppBar(title: Text(title)), body: body(() => Navigator.of(ctx).pop())),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final me = app.me;
    final meta = app.meta;
    final t = Theme.of(context);
    // Category totals already include their merchants (a category amount is its total).
    final totalSpend = (me?.categoryTotals.isNotEmpty ?? false)
        ? me!.categoryTotals.values.fold<int>(0, (a, b) => a + b)
        : (me?.spends.values.fold<int>(0, (a, b) => a + b) ?? 0);
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(padding: const EdgeInsets.symmetric(horizontal: 16), children: [
        const SectionHeader('Your cards'),
        Card(
          child: Column(children: [
            for (final h in me?.holdings ?? const <Holding>[])
              CreditTile(holding: h, credit: app.creditByCard[h.cardId], pools: me?.pools ?? const []),
            ListTile(
              leading: const Icon(Icons.edit_outlined),
              title: const Text('Edit cards you hold'),
              onTap: () => _push(context, 'Cards you hold', (done) => HoldingsEditor(actionLabel: 'Save', onSaved: done, requireOne: true)),
            ),
          ]),
        ),
        SectionHeader('Monthly spends · ${rupees(totalSpend)}'),
        Card(
          child: Column(children: [
            if (me != null && me.spends.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                child: Wrap(spacing: 8, runSpacing: 8, children: [
                  for (final e in (me.categoryTotals.isNotEmpty ? me.categoryTotals : me.spends).entries)
                    Chip(label: Text('${meta?.shortLabel(e.key) ?? e.key} ${rupees(e.value)}')),
                ]),
              ),
            ListTile(
              leading: const Icon(Icons.edit_outlined),
              title: Text(me?.spends.isEmpty ?? true ? 'Add monthly spends' : 'Edit monthly spends'),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const BudgetScreen())),
            ),
          ]),
        ),
        const SectionHeader('Memberships'),
        Card(
          child: ListTile(
            leading: const Icon(Icons.card_membership),
            title: Text((me?.profile.flags ?? const <String>[]).isEmpty
                ? 'None added'
                : [for (final f in me!.profile.flags) meta?.membership(f)?.name ?? f].join(' · ')),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _push(context, 'Memberships', (done) => PreferencesEditor(actionLabel: 'Save', onSaved: done, finder: false)),
          ),
        ),
        const SectionHeader('Data sources'),
        Card(
          child: ListTile(
            leading: const Icon(Icons.cloud_sync_outlined),
            title: const Text('Statements, credit report, notifications, Gmail'),
            subtitle: const Text('Optional: keep balances, limits and caps up to date without typing'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const DataSourcesScreen())),
          ),
        ),
        const SectionHeader('Your answers'),
        const _AnswersCard(),
        const SectionHeader('Payments you logged'),
        const _TransactionsCard(),
        const SectionHeader('App'),
        Card(
          child: Column(children: [
            ListTile(
              leading: const Icon(Icons.dns_outlined),
              title: const Text('Server'),
              subtitle: Text(app.baseUrl),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen())),
            ),
            ListTile(
              leading: const Icon(Icons.info_outline),
              title: const Text('How cc-smith gets its numbers'),
              subtitle: const Text('Rewards maths uses only facts quoted from official bank pages. Anything else is shown as '
                  '"reported, not confirmed by the bank" and never used in the maths. No affiliate links.'),
              isThreeLine: true,
            ),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: Text('User ${app.userId ?? '—'}', style: t.textTheme.labelSmall, textAlign: TextAlign.center),
        ),
      ]),
    );
  }
}

class _TransactionsCard extends StatefulWidget {
  const _TransactionsCard();
  @override
  State<_TransactionsCard> createState() => _TransactionsCardState();
}

class _TransactionsCardState extends State<_TransactionsCard> {
  Future<List<Transaction>>? _f;
  int _version = -1;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final app = AppScope.of(context);
    if (_version != app.dataVersion) {
      _version = app.dataVersion;
      _f = app.api.transactions();
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Card(
      child: FutureBuilder<List<Transaction>>(
        future: _f,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Padding(padding: EdgeInsets.all(16), child: LinearProgressIndicator());
          }
          if (snap.hasError) return ListTile(title: Text('${snap.error}'));
          final txns = snap.data!;
          if (txns.isEmpty) {
            return const ListTile(
              leading: Icon(Icons.receipt_long_outlined),
              title: Text('Nothing logged yet'),
              subtitle: Text('Tap "I paid with this" on the Pay tab so caps are tracked.'),
            );
          }
          return Column(children: [
            for (final t in txns.take(8))
              ListTile(
                dense: true,
                title: Text('${t.merchantName ?? 'Payment'} · ${rupees(t.amountPaise)}'),
                subtitle: Text('${app.cardName(t.cardId)} · ${shortDate(t.ts)}'),
                trailing: Money(t.rewardPaise, style: Theme.of(context).textTheme.labelLarge),
              ),
          ]);
        },
      ),
    );
  }
}

// ---------------------------------------------------------------- settings

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _url;
  String? _status;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _url = TextEditingController(text: AppScope.read(context).baseUrl);
  }

  @override
  void dispose() {
    _url.dispose();
    super.dispose();
  }

  bool _valid(String s) {
    final u = Uri.tryParse(s.trim());
    return u != null && (u.scheme == 'http' || u.scheme == 'https') && u.host.isNotEmpty;
  }

  Future<void> _test() async {
    if (!_valid(_url.text)) {
      setState(() => _status = 'Enter a URL like http://10.0.2.2:8000');
      return;
    }
    setState(() {
      _busy = true;
      _status = null;
    });
    try {
      await Api(_url.text.trim()).health();
      final meta = await Api(_url.text.trim()).meta();
      setState(() => _status = 'Connected: ${meta.merchants.length} merchants, ${meta.categories.length} categories');
    } catch (e) {
      setState(() => _status = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _save() async {
    if (!_valid(_url.text)) {
      showError(context, const ApiException('Enter a URL like http://10.0.2.2:8000'));
      return;
    }
    setState(() => _busy = true);
    final app = AppScope.read(context);
    await app.setBaseUrl(_url.text);
    if (!mounted) return;
    setState(() => _busy = false);
    if (app.bootError != null) {
      showError(context, app.bootError!);
    } else {
      showInfo(context, 'Server saved');
      Navigator.of(context).pop();
    }
  }

  Future<void> _resetUser() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Start over?'),
        content: const Text('This forgets your cards and spends on this device and starts onboarding again.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Start over')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    await AppScope.read(context).resetUser();
    if (mounted) Navigator.of(context).popUntil((r) => r.isFirst);
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        TextField(
          controller: _url,
          keyboardType: TextInputType.url,
          autocorrect: false,
          decoration: const InputDecoration(labelText: 'Server URL', helperText: 'Emulator: http://10.0.2.2:8000 · Web: http://127.0.0.1:8000'),
        ),
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: [
          OutlinedButton(onPressed: _busy ? null : _test, child: const Text('Test connection')),
          FilledButton(onPressed: _busy ? null : _save, child: const Text('Save')),
          TextButton(onPressed: () => setState(() => _url.text = defaultBaseUrl()), child: const Text('Use default')),
        ]),
        if (_status != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_status!)),
        if (app.userId != null) ...[
          const SectionHeader('Account'),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.restart_alt),
            title: const Text('Start over'),
            subtitle: const Text('Create a fresh profile'),
            onTap: _resetUser,
          ),
        ],
      ]),
    );
  }
}


/// A held card with its available credit, utilisation bar and a "Bill paid" action.
class CreditTile extends StatelessWidget {
  final Holding holding;
  final Credit? credit;
  final List<Pool> pools;
  const CreditTile({super.key, required this.holding, required this.credit, required this.pools});

  Future<void> _billPaid(BuildContext context) async {
    final app = AppScope.read(context);
    final ctrl = TextEditingController();
    final owed = credit?.outstandingPaise ?? 0;
    final choice = await showDialog<int?>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Bill paid'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${app.cardName(holding.cardId)} · owes ${rupees(owed)}'),
          const SizedBox(height: 12),
          TextField(
            controller: ctrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Amount paid (leave empty if paid in full)', prefixText: '₹ '),
          ),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          FilledButton(
            onPressed: () {
              final p = parseRupeesToPaise(ctrl.text);
              Navigator.pop(ctx, p == null || p <= 0 ? -1 : p);
            },
            child: const Text('Record payment'),
          ),
        ],
      ),
    );
    if (choice == null || !context.mounted) return;
    try {
      await app.billPaid(holding.cardId, amountPaise: choice == -1 ? null : choice);
      if (context.mounted) showInfo(context, choice == -1 ? 'Recorded: paid in full' : 'Recorded ${rupees(choice)} paid');
    } catch (e) {
      if (context.mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = Theme.of(context);
    final s = t.colorScheme;
    final c = credit;
    final util = c?.utilisationBp;
    final barColor = util == null ? s.outline : (util >= 7000 ? s.error : (util >= 3000 ? s.tertiary : moneyColor(context)));
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 8, 4),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.credit_card, size: 20),
          const SizedBox(width: 10),
          Expanded(child: Text(app.cardName(holding.cardId), style: t.textTheme.titleSmall)),
          TextButton(onPressed: () => _billPaid(context), child: const Text('Bill paid')),
        ]),
        Padding(
          padding: const EdgeInsets.only(left: 30, right: 8),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (c?.availablePaise != null) ...[
              Row(children: [
                Expanded(child: Text('${rupees(c!.availablePaise!)} available', style: t.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600))),
                Text('${(util ?? 0) ~/ 100}% used', style: t.textTheme.labelMedium?.copyWith(color: barColor)),
              ]),
              const SizedBox(height: 4),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: ((util ?? 0) / 10000).clamp(0.0, 1.0),
                  minHeight: 6,
                  color: barColor,
                  backgroundColor: s.surfaceContainerHighest,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                [
                  'Owes ${rupees(c.outstandingPaise)} of ${rupees(c.limitPaise ?? 0)}',
                  if (c.poolName != null) 'shared limit: ${c.poolName}',
                ].join(' · '),
                style: t.textTheme.labelSmall?.copyWith(color: s.onSurfaceVariant),
              ),
            ] else
              Text(c == null ? holdingSummary(holding, pools) : 'Owes ${rupees(c.outstandingPaise)} · add a credit limit to track what is left',
                  style: t.textTheme.bodySmall),
            Text(feeStatusLabel(holding), style: t.textTheme.labelSmall?.copyWith(color: s.onSurfaceVariant)),
          ]),
        ),
      ]),
    );
  }
}


/// Every condition the user answered (editable), plus the ones still open.
class _AnswersCard extends StatelessWidget {
  const _AnswersCard();
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = Theme.of(context);
    final conds = app.meta?.conditions ?? const <Condition>[];
    final answered = conds.where((c) => app.answers.containsKey(c.key)).toList();
    final open = conds.where((c) => !app.answers.containsKey(c.key)).toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Used to tell which offers and rewards apply to you. Change them any time.', style: t.textTheme.bodySmall),
          if (answered.isEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text('Nothing answered yet.', style: t.textTheme.bodyMedium)),
          for (final c in answered) ConditionAsk(c, showWhy: false),
          if (open.isNotEmpty)
            Theme(
              data: t.copyWith(dividerColor: Colors.transparent),
              child: ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: Text('Other questions (${open.length})', style: t.textTheme.labelLarge),
                children: [for (final c in open) ConditionAsk(c)],
              ),
            ),
        ]),
      ),
    );
  }
}
