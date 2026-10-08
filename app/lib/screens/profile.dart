import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
import '../format.dart';
import '../models.dart';
import '../state.dart';
import '../widgets.dart';

/// Spend keys offered up front (category or merchant keys from /meta).
const commonSpendKeys = ['amazon', 'flipkart', 'swiggy', 'zomato', 'grocery', 'dining', 'travel', 'fuel', 'utilities', 'rent', 'other'];

const feeOptions = <int?>[null, 0, 50000, 100000, 250000, 500000, 1000000];
String feeOptionLabel(int? p) => p == null ? 'No limit' : (p == 0 ? 'Free only' : 'Up to ${rupees(p)}');

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
              Center(
                child: TextButton(
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen())),
                  child: Text('Server: ${app.baseUrl}', style: t.textTheme.labelSmall),
                ),
              ),
            ]),
          ),
        ),
      );
    }
    final titles = ['', 'Cards you hold', 'What you spend each month', 'Your preferences'];
    return Scaffold(
      appBar: AppBar(
        title: Text(titles[step]),
        leading: step > 1 ? BackButton(onPressed: () => setState(() => _step = step - 1)) : null,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(4),
          child: LinearProgressIndicator(value: step / 3),
        ),
      ),
      body: switch (step) {
        1 => HoldingsEditor(actionLabel: 'Next', onSaved: () => setState(() => _step = 2), requireOne: true),
        2 => SpendsEditor(actionLabel: 'Next', onSaved: () => setState(() => _step = 3)),
        _ => PreferencesEditor(actionLabel: 'Finish', onSaved: () => AppScope.read(context).completeOnboarding()),
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
    final totalSpend = me?.spends.values.fold<int>(0, (a, b) => a + b) ?? 0;
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(padding: const EdgeInsets.symmetric(horizontal: 16), children: [
        const SectionHeader('Your cards'),
        Card(
          child: Column(children: [
            for (final h in me?.holdings ?? const <Holding>[])
              ListTile(
                leading: const Icon(Icons.credit_card),
                title: Text(app.cardName(h.cardId)),
                subtitle: h.statementDay != null ? Text('Statement day ${h.statementDay}') : null,
              ),
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
                  for (final e in me.spends.entries)
                    Chip(label: Text('${meta?.shortLabel(e.key) ?? e.key} ${rupees(e.value)}')),
                ]),
              ),
            ListTile(
              leading: const Icon(Icons.edit_outlined),
              title: Text(me?.spends.isEmpty ?? true ? 'Add monthly spends' : 'Edit monthly spends'),
              onTap: () => _push(context, 'Monthly spends', (done) => SpendsEditor(actionLabel: 'Save', onSaved: done)),
            ),
          ]),
        ),
        const SectionHeader('Preferences'),
        Card(
          child: ListTile(
            leading: const Icon(Icons.tune),
            title: Text([
              if (me?.profile.flags.contains('amazon_prime') ?? false) 'Amazon Prime',
              'Rewards: ${me?.profile.rewardPreference ?? 'any'}',
              'Max fee: ${feeOptionLabel(me?.profile.maxAnnualFeePaise)}',
            ].join(' · ')),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _push(context, 'Preferences', (done) => PreferencesEditor(actionLabel: 'Save', onSaved: done)),
          ),
        ),
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

// ---------------------------------------------------------------- editors

class _SaveBar extends StatelessWidget {
  final String label;
  final bool busy;
  final VoidCallback? onPressed;
  const _SaveBar({required this.label, required this.busy, this.onPressed});
  @override
  Widget build(BuildContext context) => SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
          child: SizedBox(
            width: double.infinity,
            child: FilledButton(
              style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 14)),
              onPressed: busy ? null : onPressed,
              child: busy ? const SizedBox.square(dimension: 20, child: CircularProgressIndicator(strokeWidth: 2)) : Text(label),
            ),
          ),
        ),
      );
}

class HoldingsEditor extends StatefulWidget {
  final String actionLabel;
  final VoidCallback onSaved;
  final bool requireOne;
  const HoldingsEditor({super.key, required this.actionLabel, required this.onSaved, this.requireOne = false});
  @override
  State<HoldingsEditor> createState() => _HoldingsEditorState();
}

class _HoldingsEditorState extends State<HoldingsEditor> {
  late Map<String, Holding> _selected;
  String _query = '';
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final me = AppScope.read(context).me;
    _selected = {for (final h in me?.holdings ?? const <Holding>[]) h.cardId: h};
  }

  Future<void> _save() async {
    if (widget.requireOne && _selected.isEmpty) {
      showError(context, const ApiException('Pick at least one card you hold.'));
      return;
    }
    setState(() => _busy = true);
    try {
      await AppScope.read(context).saveHoldings(_selected.values.toList());
      widget.onSaved();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickStatementDay(String cardId) async {
    final current = _selected[cardId]?.statementDay;
    final day = await showDialog<int>(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: const Text('Statement day'),
        children: [
          SimpleDialogOption(onPressed: () => Navigator.pop(ctx, 0), child: const Text("Don't know")),
          SizedBox(
            width: 300,
            child: Wrap(alignment: WrapAlignment.center, children: [
              for (var d = 1; d <= 31; d++)
                Padding(
                  padding: const EdgeInsets.all(2),
                  child: ChoiceChip(label: Text('$d'), selected: d == current, onSelected: (_) => Navigator.pop(ctx, d)),
                ),
            ]),
          ),
        ],
      ),
    );
    if (day == null) return;
    setState(() {
      final h = _selected[cardId]!;
      _selected[cardId] = day == 0 ? h.copyWith(clearStatementDay: true) : h.copyWith(statementDay: day);
    });
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final q = _query.toLowerCase();
    final cards = (app.cards ?? const <CardSummary>[])
        .where((c) => q.isEmpty || c.name.toLowerCase().contains(q) || c.issuer.toLowerCase().contains(q))
        .toList()
      ..sort((a, b) => a.name.compareTo(b.name));
    final t = Theme.of(context);
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
        child: TextField(
          decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search cards or banks'),
          onChanged: (v) => setState(() => _query = v),
        ),
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
        child: Row(children: [
          Expanded(child: Text('${_selected.length} selected', style: t.textTheme.labelMedium)),
          Flexible(child: Text('${app.cards?.length ?? 0} cards in catalogue', style: t.textTheme.labelSmall, textAlign: TextAlign.end)),
        ]),
      ),
      Expanded(
        child: ListView.builder(
          itemCount: cards.length,
          itemBuilder: (context, i) {
            final c = cards[i];
            final h = _selected[c.id];
            return CheckboxListTile(
              value: h != null,
              onChanged: (v) => setState(() => v == true ? _selected[c.id] = Holding(cardId: c.id) : _selected.remove(c.id)),
              title: Text(c.name),
              subtitle: h == null
                  ? Text(c.issuer)
                  : Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton.icon(
                        style: TextButton.styleFrom(padding: EdgeInsets.zero, visualDensity: VisualDensity.compact),
                        onPressed: () => _pickStatementDay(c.id),
                        icon: const Icon(Icons.event, size: 16),
                        label: Text(h.statementDay == null ? 'Statement day (optional)' : 'Statement day ${h.statementDay}'),
                      ),
                    ),
              secondary: CircleAvatar(
                backgroundColor: t.colorScheme.primaryContainer,
                child: Text(c.issuer.isEmpty ? '?' : c.issuer[0], style: TextStyle(color: t.colorScheme.onPrimaryContainer)),
              ),
            );
          },
        ),
      ),
      _SaveBar(label: widget.actionLabel, busy: _busy, onPressed: _save),
    ]);
  }
}

class SpendsEditor extends StatefulWidget {
  final String actionLabel;
  final VoidCallback onSaved;
  const SpendsEditor({super.key, required this.actionLabel, required this.onSaved});
  @override
  State<SpendsEditor> createState() => _SpendsEditorState();
}

class _SpendsEditorState extends State<SpendsEditor> {
  final _ctrls = <String, TextEditingController>{};
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final app = AppScope.read(context);
    final meta = app.meta!;
    final existing = app.me?.spends ?? const <String, int>{};
    final valid = {...meta.categories.keys, ...meta.merchants.map((m) => m.key)};
    for (final k in [...commonSpendKeys.where(valid.contains), ...existing.keys]) {
      _ctrls.putIfAbsent(k, () => TextEditingController(text: existing[k] == null ? '' : '${existing[k]! ~/ 100}'));
    }
  }

  @override
  void dispose() {
    for (final c in _ctrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  int get _total => _ctrls.values.map((c) => parseRupeesToPaise(c.text) ?? 0).fold(0, (a, b) => a + b);

  Future<void> _add() async {
    final meta = AppScope.read(context).meta!;
    final options = [
      ...meta.categories.entries.map((e) => (e.key, e.value, 'Category')),
      ...meta.merchants.map((m) => (m.key, m.name, 'Merchant · ${meta.shortLabel(m.category)}')),
    ].where((o) => !_ctrls.containsKey(o.$1)).toList();
    final key = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => _KeyPicker(options: options),
    );
    if (key != null) setState(() => _ctrls[key] = TextEditingController());
  }

  Future<void> _save() async {
    final out = <String, int>{};
    for (final e in _ctrls.entries) {
      final p = parseRupeesToPaise(e.value.text);
      if (p != null && p > 0) out[e.key] = p;
    }
    if (out.isEmpty) {
      showError(context, const ApiException('Enter at least one monthly spend.'));
      return;
    }
    setState(() => _busy = true);
    try {
      await AppScope.read(context).saveSpends(out);
      widget.onSaved();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final meta = AppScope.of(context).meta!;
    final t = Theme.of(context);
    return Column(children: [
      Expanded(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 16), children: [
          Text('Rough monthly amounts are fine. Merchants (Amazon, Swiggy…) are scored with their own offers; '
              'categories cover everything else.', style: t.textTheme.bodySmall),
          const SizedBox(height: 8),
          for (final e in _ctrls.entries)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: Row(children: [
                Expanded(
                  flex: 5,
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(meta.label(e.key), style: t.textTheme.bodyLarge, maxLines: 2, overflow: TextOverflow.ellipsis),
                    if (meta.merchant(e.key) != null)
                      Text('Merchant', style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
                  ]),
                ),
                const SizedBox(width: 12),
                Expanded(
                  flex: 4,
                  child: TextField(
                    controller: e.value,
                    keyboardType: const TextInputType.numberWithOptions(decimal: false),
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                    textAlign: TextAlign.end,
                    onChanged: (_) => setState(() {}),
                    decoration: const InputDecoration(prefixText: '₹ ', hintText: '0', suffixText: '/mo', isDense: true),
                  ),
                ),
              ]),
            ),
          const SizedBox(height: 8),
          OutlinedButton.icon(onPressed: _add, icon: const Icon(Icons.add), label: const Text('Add a category or merchant')),
        ]),
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Row(children: [
          Text('Total', style: t.textTheme.titleSmall),
          const SizedBox(width: 12),
          Expanded(
            child: Text('${rupees(_total)}/month · ${rupees(_total * 12)}/year',
                style: t.textTheme.titleSmall, textAlign: TextAlign.end),
          ),
        ]),
      ),
      _SaveBar(label: widget.actionLabel, busy: _busy, onPressed: _save),
    ]);
  }
}

class _KeyPicker extends StatefulWidget {
  final List<(String, String, String)> options;
  const _KeyPicker({required this.options});
  @override
  State<_KeyPicker> createState() => _KeyPickerState();
}

class _KeyPickerState extends State<_KeyPicker> {
  String _q = '';
  @override
  Widget build(BuildContext context) {
    final q = _q.toLowerCase();
    final list = widget.options.where((o) => q.isEmpty || o.$2.toLowerCase().contains(q) || o.$1.contains(q)).toList();
    return SizedBox(
      height: MediaQuery.of(context).size.height * 0.75,
      child: Column(children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: TextField(
            autofocus: true,
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search'),
            onChanged: (v) => setState(() => _q = v),
          ),
        ),
        Expanded(
          child: ListView(children: [
            for (final o in list)
              ListTile(title: Text(o.$2), subtitle: Text(o.$3), onTap: () => Navigator.pop(context, o.$1)),
          ]),
        ),
      ]),
    );
  }
}

class PreferencesEditor extends StatefulWidget {
  final String actionLabel;
  final VoidCallback onSaved;
  const PreferencesEditor({super.key, required this.actionLabel, required this.onSaved});
  @override
  State<PreferencesEditor> createState() => _PreferencesEditorState();
}

class _PreferencesEditorState extends State<PreferencesEditor> {
  late Profile _p;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _p = AppScope.read(context).me?.profile ?? const Profile();
  }

  bool get _prime => _p.flags.contains('amazon_prime');

  Profile _with({List<String>? flags, String? pref, int? maxFee, bool setFee = false}) => Profile(
        flags: flags ?? _p.flags,
        scoreBand: _p.scoreBand,
        incomeBand: _p.incomeBand,
        rewardPreference: pref ?? _p.rewardPreference,
        maxAnnualFeePaise: setFee ? maxFee : _p.maxAnnualFeePaise,
      );

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      await AppScope.read(context).saveProfile(_p);
      widget.onSaved();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Column(children: [
      Expanded(
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Card(
            child: SwitchListTile(
              value: _prime,
              onChanged: (v) => setState(() => _p = _with(
                  flags: v ? {..._p.flags, 'amazon_prime'}.toList() : _p.flags.where((f) => f != 'amazon_prime').toList())),
              title: const Text('Amazon Prime member'),
              subtitle: const Text('Some cards pay more on Amazon for Prime members'),
            ),
          ),
          const SectionHeader('Reward type you prefer'),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'any', label: Text('Any')),
              ButtonSegment(value: 'cashback', label: Text('Cashback')),
              ButtonSegment(value: 'points', label: Text('Points')),
            ],
            selected: {_p.rewardPreference},
            onSelectionChanged: (s) => setState(() => _p = _with(pref: s.first)),
          ),
          const SectionHeader('Highest annual fee you\'d pay'),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final f in feeOptions)
              ChoiceChip(
                label: Text(feeOptionLabel(f)),
                selected: _p.maxAnnualFeePaise == f,
                onSelected: (_) => setState(() => _p = _with(maxFee: f, setFee: true)),
              ),
          ]),
          const SizedBox(height: 12),
          Text('Card Finder only suggests new cards that match these. Cards you already hold are always scored.',
              style: t.textTheme.bodySmall),
        ]),
      ),
      _SaveBar(label: widget.actionLabel, busy: _busy, onPressed: _save),
    ]);
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
            subtitle: const Text('Create a fresh profile (useful for demos)'),
            onTap: _resetUser,
          ),
        ],
      ]),
    );
  }
}
