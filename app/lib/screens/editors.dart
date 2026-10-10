import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
import '../format.dart';
import '../models.dart';
import '../state.dart';
import '../widgets.dart';

const feeOptions = <int?>[null, 0, 50000, 100000, 250000, 500000, 1000000];
String feeOptionLabel(int? p) => p == null ? 'No limit' : (p == 0 ? 'Free only' : 'Up to ${rupees(p)}');

String feeStatusLabel(Holding h) => switch (h.feeStatus) {
  'ltf' => 'Lifetime free',
  'fyf' => h.fyfUntil == null ? 'First year free' : 'Free until ${shortDate(h.fyfUntil)}',
  _ => 'Standard fee',
};

/// One-line summary of a held card's limit, balance and fee status.
String holdingSummary(Holding h, List<Pool> pools) {
  final pool = pools.where((p) => p.id == h.poolId).firstOrNull;
  return [
    if (pool != null) 'Shares ${pool.name} (${rupees(pool.limitPaise)})'
    else if (h.creditLimitPaise != null) 'Limit ${rupees(h.creditLimitPaise!)}'
    else 'Limit not set',
    if (h.balancePaise != null) 'owes ${rupees(h.balancePaise!)}',
    feeStatusLabel(h),
    if (h.statementDay != null) 'statement day ${h.statementDay}',
  ].join(' · ');
}

String _rupeeText(int? paise) => paise == null ? '' : '${paise ~/ 100}';

String _isoDate(DateTime d) => '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

String _slug(String s) {
  final slug = s.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '_').replaceAll(RegExp(r'^_+|_+$'), '');
  return slug.isEmpty ? 'pool' : (slug.length > 30 ? slug.substring(0, 30) : slug);
}

class SaveBar extends StatelessWidget {
  final String label;
  final bool busy;
  final VoidCallback? onPressed;
  const SaveBar({super.key, required this.label, required this.busy, this.onPressed});
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

// ---------------------------------------------------------------- holdings

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
  late List<Pool> _pools;
  late Set<String> _flags;
  late final List<Pool> _origPools;
  late final Set<String> _origFlags;
  String _query = '';
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final me = AppScope.read(context).me;
    _selected = {for (final h in me?.holdings ?? const <Holding>[]) h.cardId: h};
    _pools = [...?me?.pools];
    _origPools = [..._pools];
    _flags = {...?me?.profile.flags};
    _origFlags = {..._flags};
  }

  bool get _poolsChanged =>
      _pools.length != _origPools.length ||
      _pools.indexed.any((e) => e.$2.id != _origPools[e.$1].id || e.$2.limitPaise != _origPools[e.$1].limitPaise || e.$2.name != _origPools[e.$1].name);

  Future<void> _save() async {
    if (widget.requireOne && _selected.isEmpty) {
      showError(context, const ApiException('Pick at least one card you hold.'));
      return;
    }
    setState(() => _busy = true);
    try {
      final ids = _pools.map((p) => p.id).toSet();
      final holdings = _selected.values.map((h) => h.poolId != null && !ids.contains(h.poolId) ? h.copyWith(clearPool: true) : h).toList();
      final flagsChanged = _flags.length != _origFlags.length || !_flags.containsAll(_origFlags);
      await AppScope.read(context).saveHoldings(holdings, pools: _poolsChanged ? _pools : null, flags: flagsChanged ? _flags.toList() : null);
      widget.onSaved();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _editDetails(CardSummary c) async {
    final result = await showModalBottomSheet<(Holding, List<Pool>)>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => CardDetailsSheet(card: c, holding: _selected[c.id]!, pools: _pools),
    );
    if (result != null) {
      setState(() {
        _selected[c.id] = result.$1;
        _pools = result.$2;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final q = _query.toLowerCase();
    final cards =
        (app.cards ?? const <CardSummary>[])
            .where((c) => q.isEmpty || c.name.toLowerCase().contains(q) || c.issuer.toLowerCase().contains(q))
            .toList()
          ..sort((a, b) {
            // Held cards first so their details stay in view.
            final ha = _selected.containsKey(a.id) ? 0 : 1, hb = _selected.containsKey(b.id) ? 0 : 1;
            return ha != hb ? ha - hb : a.name.compareTo(b.name);
          });
    final t = Theme.of(context);
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          child: TextField(
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search cards or banks'),
            onChanged: (v) => setState(() => _query = v),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
          child: Row(
            children: [
              Expanded(child: Text('${_selected.length} selected', style: t.textTheme.labelMedium)),
              Flexible(
                child: Text('${app.cards?.length ?? 0} cards in catalogue', style: t.textTheme.labelSmall, textAlign: TextAlign.end),
              ),
            ],
          ),
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
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(holdingSummary(h, _pools), style: t.textTheme.bodySmall),
                          for (final m in c.memberships)
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: FilterChip(
                                label: Text('I have ${app.meta?.membership(m.key)?.name ?? m.name}'),
                                selected: _flags.contains(m.key),
                                onSelected: (v) => setState(() => v ? _flags.add(m.key) : _flags.remove(m.key)),
                              ),
                            ),
                          TextButton.icon(
                            style: TextButton.styleFrom(padding: EdgeInsets.zero, visualDensity: VisualDensity.compact),
                            onPressed: () => _editDetails(c),
                            icon: const Icon(Icons.tune, size: 16),
                            label: const Text('Limit, balance and fee'),
                          ),
                        ],
                      ),
                secondary: CircleAvatar(
                  backgroundColor: t.colorScheme.primaryContainer,
                  child: Text(c.issuer.isEmpty ? '?' : c.issuer[0], style: TextStyle(color: t.colorScheme.onPrimaryContainer)),
                ),
              );
            },
          ),
        ),
        SaveBar(label: widget.actionLabel, busy: _busy, onPressed: _save),
      ],
    );
  }
}

/// Per-card details: own limit or a shared one, today's outstanding, fee status.
class CardDetailsSheet extends StatefulWidget {
  final CardSummary card;
  final Holding holding;
  final List<Pool> pools;
  const CardDetailsSheet({super.key, required this.card, required this.holding, required this.pools});
  @override
  State<CardDetailsSheet> createState() => _CardDetailsSheetState();
}

class _CardDetailsSheetState extends State<CardDetailsSheet> {
  late Holding _h;
  late List<Pool> _pools;
  late bool _shared;
  late final TextEditingController _limit;
  late final TextEditingController _balance;

  @override
  void initState() {
    super.initState();
    _h = widget.holding;
    _pools = [...widget.pools];
    _shared = _h.poolId != null;
    _limit = TextEditingController(text: _rupeeText(_h.creditLimitPaise));
    _balance = TextEditingController(text: _rupeeText(_h.balancePaise));
  }

  @override
  void dispose() {
    _limit.dispose();
    _balance.dispose();
    super.dispose();
  }

  Future<void> _newPool() async {
    final name = TextEditingController(text: '${widget.card.issuer.split(' ').first} shared');
    final limit = TextEditingController();
    final pool = await showDialog<Pool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('New shared limit'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Banks often give one limit across all your cards with them.'),
            const SizedBox(height: 12),
            TextField(controller: name, decoration: const InputDecoration(labelText: 'Shared limit name')),
            const SizedBox(height: 8),
            TextField(
              controller: limit,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              decoration: const InputDecoration(labelText: 'Shared limit', prefixText: '₹ '),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          FilledButton(
            onPressed: () {
              final p = parseRupeesToPaise(limit.text);
              if (name.text.trim().isEmpty || p == null || p <= 0) return;
              var id = _slug(name.text);
              while (_pools.any((x) => x.id == id)) {
                id = '${id}_2';
              }
              Navigator.pop(ctx, Pool(id: id, name: name.text.trim(), limitPaise: p));
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
    if (pool != null) {
      setState(() {
        _pools.add(pool);
        _h = _h.copyWith(poolId: pool.id);
      });
    }
  }

  Future<void> _pickFyf() async {
    final now = DateTime.now();
    final init = DateTime.tryParse(_h.fyfUntil ?? '') ?? DateTime(now.year + 1, now.month, now.day);
    final d = await showDatePicker(context: context, initialDate: init, firstDate: DateTime(now.year - 1), lastDate: DateTime(now.year + 3));
    if (d != null) setState(() => _h = _h.copyWith(fyfUntil: _isoDate(d)));
  }

  void _done() {
    final limit = parseRupeesToPaise(_limit.text);
    final balance = parseRupeesToPaise(_balance.text);
    var h = _h.copyWith(
      creditLimitPaise: limit,
      clearLimit: _shared || limit == null,
      clearPool: !_shared,
      balancePaise: balance,
      clearBalance: balance == null,
    );
    if (h.feeStatus == 'fyf' && h.fyfUntil == null) {
      showError(context, const ApiException('Pick the date the free year ends.'));
      return;
    }
    if (_shared && h.poolId == null) {
      showError(context, const ApiException('Pick or create the shared limit.'));
      return;
    }
    Navigator.pop(context, (h, _pools));
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 0, 16, MediaQuery.of(context).viewInsets.bottom + 16),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(widget.card.name, style: t.textTheme.titleLarge),
            const SectionHeader('Credit limit'),
            SegmentedButton<bool>(
              segments: const [
                ButtonSegment(value: false, label: Text('Own limit')),
                ButtonSegment(value: true, label: Text('Shares a limit')),
              ],
              selected: {_shared},
              onSelectionChanged: (v) => setState(() => _shared = v.first),
            ),
            const SizedBox(height: 10),
            if (!_shared)
              TextField(
                controller: _limit,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: const InputDecoration(labelText: 'Credit limit', prefixText: '₹ '),
              )
            else ...[
              if (_pools.isNotEmpty)
                DropdownButtonFormField<String>(
                  isExpanded: true,
                  initialValue: _pools.any((p) => p.id == _h.poolId) ? _h.poolId : null,
                  decoration: const InputDecoration(labelText: 'Shares a limit with…'),
                  items: [for (final p in _pools) DropdownMenuItem(value: p.id, child: Text('${p.name} · ${rupees(p.limitPaise)}', overflow: TextOverflow.ellipsis))],
                  onChanged: (v) => setState(() => _h = _h.copyWith(poolId: v)),
                ),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(onPressed: _newPool, icon: const Icon(Icons.add), label: const Text('New shared limit')),
              ),
            ],
            const SizedBox(height: 10),
            TextField(
              controller: _balance,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              decoration: const InputDecoration(
                labelText: 'Outstanding today',
                prefixText: '₹ ',
                helperText: 'What you owe on this card right now. Payments you log are added to it.',
              ),
            ),
            const SectionHeader('Annual fee'),
            SegmentedButton<String>(
              showSelectedIcon: false,
              segments: const [
                ButtonSegment(value: 'standard', label: Text('Standard')),
                ButtonSegment(value: 'ltf', label: Text('Lifetime free')),
                ButtonSegment(value: 'fyf', label: Text('First year free')),
              ],
              selected: {_h.feeStatus},
              onSelectionChanged: (v) => setState(() => _h = _h.copyWith(feeStatus: v.first)),
            ),
            if (_h.feeStatus == 'fyf')
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: _pickFyf,
                  icon: const Icon(Icons.event),
                  label: Text(_h.fyfUntil == null ? 'Free until… (pick date)' : 'Free until ${shortDate(_h.fyfUntil)}'),
                ),
              ),
            const SectionHeader('Statement day'),
            DropdownButtonFormField<int?>(
              isExpanded: true,
              initialValue: _h.statementDay,
              decoration: const InputDecoration(labelText: 'Statement day (optional)'),
              items: [
                const DropdownMenuItem<int?>(value: null, child: Text("Don't know")),
                for (var d = 1; d <= 31; d++) DropdownMenuItem<int?>(value: d, child: Text('$d')),
              ],
              onChanged: (v) => setState(() => _h = v == null ? _h.copyWith(clearStatementDay: true) : _h.copyWith(statementDay: v)),
            ),
            const SizedBox(height: 16),
            FilledButton(onPressed: _done, child: const Text('Done')),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- spends

class SpendsEditor extends StatefulWidget {
  final String actionLabel;
  final VoidCallback onSaved;
  const SpendsEditor({super.key, required this.actionLabel, required this.onSaved});
  @override
  State<SpendsEditor> createState() => _SpendsEditorState();
}

class _SpendsEditorState extends State<SpendsEditor> {
  final _ctrls = <String, TextEditingController>{};
  final _expanded = <String>{};
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final app = AppScope.read(context);
    final existing = app.me?.spends ?? const <String, int>{};
    for (final g in app.meta!.groups) {
      _ctrls[g.category] = TextEditingController(text: _rupeeText(existing[g.category]));
      for (final m in g.merchants) {
        _ctrls[m.key] = TextEditingController(text: _rupeeText(existing[m.key]));
        if ((existing[m.key] ?? 0) > 0) _expanded.add(g.category);
      }
    }
  }

  @override
  void dispose() {
    for (final c in _ctrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  int _v(String key) => parseRupeesToPaise(_ctrls[key]?.text ?? '') ?? 0;
  int _merchantSum(SpendGroup g) => g.merchants.fold(0, (a, m) => a + _v(m.key));

  /// The category total as the backend counts it: the amount typed, or the merchants' sum if larger.
  int _groupTotal(SpendGroup g) {
    final c = _v(g.category), m = _merchantSum(g);
    return c > m ? c : m;
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

  Widget _amountField(String key, {String? hint}) => TextField(
    controller: _ctrls[key],
    keyboardType: const TextInputType.numberWithOptions(decimal: false),
    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
    textAlign: TextAlign.end,
    onChanged: (_) => setState(() {}),
    decoration: InputDecoration(prefixText: '₹ ', hintText: hint ?? '0', suffixText: '/mo', isDense: true),
  );

  Widget _group(SpendGroup g) {
    final t = Theme.of(context);
    final s = t.colorScheme;
    final merchants = _merchantSum(g);
    final typed = _v(g.category);
    final open = _expanded.contains(g.category);
    final short = g.label.contains(' (') ? g.label.substring(0, g.label.indexOf(' (')) : g.label;
    String? note;
    if (merchants > 0 && typed >= merchants) {
      note = '${rupees(typed - merchants)} other ${short.toLowerCase()}';
    } else if (merchants > 0) {
      note = 'Merchants add up to ${rupees(merchants)}, so that is the ${short.toLowerCase()} total';
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(flex: 5, child: Text(g.label, style: t.textTheme.bodyLarge, maxLines: 2, overflow: TextOverflow.ellipsis)),
                const SizedBox(width: 12),
                Expanded(flex: 4, child: _amountField(g.category, hint: merchants > 0 ? groupIndian(merchants ~/ 100) : null)),
              ],
            ),
            if (note != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(note, style: t.textTheme.labelSmall?.copyWith(color: s.onSurfaceVariant)),
              ),
            if (g.merchants.isNotEmpty)
              TextButton.icon(
                style: TextButton.styleFrom(padding: EdgeInsets.zero, visualDensity: VisualDensity.compact),
                onPressed: () => setState(() => open ? _expanded.remove(g.category) : _expanded.add(g.category)),
                icon: Icon(open ? Icons.expand_less : Icons.expand_more, size: 18),
                label: Text(open ? 'Hide merchants' : 'Split by merchant (${g.merchants.take(3).map((m) => m.name).join(', ')}${g.merchants.length > 3 ? '…' : ''})'),
              ),
            if (open)
              for (final m in g.merchants)
                Padding(
                  padding: const EdgeInsets.only(left: 16, bottom: 6),
                  child: Row(
                    children: [
                      Expanded(flex: 5, child: Text(m.name, style: t.textTheme.bodyMedium)),
                      const SizedBox(width: 12),
                      Expanded(flex: 4, child: _amountField(m.key)),
                    ],
                  ),
                ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final meta = AppScope.of(context).meta!;
    final t = Theme.of(context);
    final total = meta.groups.fold<int>(0, (a, g) => a + _groupTotal(g));
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            children: [
              Text(
                'Enter each category\'s monthly total. Split out merchants with their own offers (Swiggy, Amazon…) — '
                'they are part of the category, not extra.',
                style: t.textTheme.bodySmall,
              ),
              const SizedBox(height: 8),
              for (final g in meta.groups) _group(g),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Row(
            children: [
              Text('Total', style: t.textTheme.titleSmall),
              const SizedBox(width: 12),
              Expanded(
                child: Text('${rupees(total)}/month · ${rupees(total * 12)}/year', style: t.textTheme.titleSmall, textAlign: TextAlign.end),
              ),
            ],
          ),
        ),
        SaveBar(label: widget.actionLabel, busy: _busy, onPressed: _save),
      ],
    );
  }
}

// ---------------------------------------------------------------- preferences

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
    final app = AppScope.of(context);
    final t = Theme.of(context);
    final memberships = app.relevantMemberships;
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const SectionHeader('Memberships'),
              if (memberships.isEmpty)
                Text('None of your cards pays more for a membership.', style: t.textTheme.bodySmall)
              else
                Card(
                  child: Column(
                    children: [
                      for (final m in memberships)
                        SwitchListTile(
                          value: _p.flags.contains(m.key),
                          onChanged: (v) => setState(
                            () => _p = _with(flags: v ? {..._p.flags, m.key}.toList() : _p.flags.where((f) => f != m.key).toList()),
                          ),
                          title: Text('${m.name} member'),
                          subtitle: Text(m.why ?? (m.by != null ? 'From ${m.by}' : '')),
                        ),
                    ],
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
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final f in feeOptions)
                    ChoiceChip(
                      label: Text(feeOptionLabel(f)),
                      selected: _p.maxAnnualFeePaise == f,
                      onSelected: (_) => setState(() => _p = _with(maxFee: f, setFee: true)),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                'Card Finder only suggests new cards that match these. Cards you already hold are always scored.',
                style: t.textTheme.bodySmall,
              ),
            ],
          ),
        ),
        SaveBar(label: widget.actionLabel, busy: _busy, onPressed: _save),
      ],
    );
  }
}
