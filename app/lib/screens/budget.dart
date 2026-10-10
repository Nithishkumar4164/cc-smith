import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../format.dart';
import '../models.dart';
import '../state.dart';
import '../widgets.dart';
import 'editors.dart';

/// Monthly budget that fills itself (demo SMS + email import) and adapts each month to
/// last month's actual spend. Edited lines are pinned; "Reset to auto" unpins them.
class BudgetPanel extends StatefulWidget {
  /// Onboarding shows a Next button once there is a budget; Profile/Finder don't.
  final VoidCallback? onNext;
  const BudgetPanel({super.key, this.onNext});
  @override
  State<BudgetPanel> createState() => _BudgetPanelState();
}

class _BudgetPanelState extends State<BudgetPanel> {
  Budget? _budget;
  Object? _error;
  bool _busy = false;
  int? _imported;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final b = await AppScope.read(context).api.budget();
      if (mounted) setState(() => _budget = b);
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  Future<void> _run(Future<Budget> Function() f) async {
    setState(() => _busy = true);
    try {
      final b = await f();
      if (!mounted) return;
      setState(() {
        _budget = b;
        _error = null;
      });
      AppScope.read(context).bumpData();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _import() => _run(() async {
    final (n, b) = await AppScope.read(context).api.importBudgetDemo();
    _imported = n;
    return b;
  });

  Future<void> _edit(BudgetLine l) async {
    final ctrl = TextEditingController(text: '${l.budgetPaise ~/ 100}');
    final v = await showDialog<int>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l.label),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (l.lastMonthPaise != null) Text('Last month you spent ${rupees(l.lastMonthPaise!)}.'),
          const SizedBox(height: 8),
          TextField(
            controller: ctrl,
            autofocus: true,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: const InputDecoration(labelText: 'Monthly budget', prefixText: '₹ ', suffixText: '/mo'),
          ),
          const SizedBox(height: 6),
          const Text('Saving pins this line; it stops adapting to last month until you reset it.'),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, parseRupeesToPaise(ctrl.text)), child: const Text('Save')),
        ],
      ),
    );
    if (v == null) return;
    await _run(() => AppScope.read(context).api.putBudget({l.key: v}));
  }

  Future<void> _reset(BudgetLine l) => _run(() => AppScope.read(context).api.putBudget({l.key: null}));

  void _manual() => Navigator.of(context).push(MaterialPageRoute(
    builder: (ctx) => Scaffold(
      appBar: AppBar(title: const Text('Monthly spends')),
      body: SpendsEditor(
        actionLabel: 'Save',
        onSaved: () {
          Navigator.of(ctx).pop();
          _load();
          widget.onNext?.call();
        },
      ),
    ),
  ));

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final s = t.colorScheme;
    final b = _budget;
    final hasLines = b != null && b.lines.isNotEmpty;
    return Column(children: [
      if (_busy) const LinearProgressIndicator(),
      Expanded(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 16), children: [
          if (!hasLines) ...[
            Text('Fill your monthly budget from your payment messages, or enter it yourself.', style: t.textTheme.bodyLarge),
            const SizedBox(height: 16),
          ],
          FilledButton.icon(
            onPressed: _busy ? null : _import,
            icon: const Icon(Icons.auto_fix_high),
            label: Text(hasLines ? 'Re-read my SMS & email' : 'Read my SMS & email'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(onPressed: _busy ? null : _manual, icon: const Icon(Icons.edit_note), label: const Text('Enter manually')),
          if (_imported != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Row(children: [
                Icon(Icons.check_circle, size: 18, color: s.primary),
                const SizedBox(width: 8),
                Expanded(child: Text('Read $_imported card transactions from last month\'s SMS and email.', style: t.textTheme.bodyMedium)),
              ]),
            ),
          if (_error != null && b == null)
            Padding(padding: const EdgeInsets.only(top: 12), child: Text('$_error', style: t.textTheme.bodySmall)),
          if (hasLines) ...[
            SectionHeader('Budget for ${_monthLabel(b.month)} · ${rupees(b.totalPaise)}'),
            Text(
              b.adaptedFrom != null
                  ? 'Auto lines follow what you actually spent in ${_monthLabel(b.adaptedFrom!)}. Tap a line to set it yourself.'
                  : 'Auto lines adapt to last month\'s spend each new month. Tap a line to set it yourself.',
              style: t.textTheme.bodySmall,
            ),
            const SizedBox(height: 6),
            Card(
              child: Column(children: [
                for (final l in b.lines)
                  ListTile(
                    onTap: _busy ? null : () => _edit(l),
                    title: Text(l.label),
                    subtitle: Wrap(spacing: 6, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
                      l.pinned
                          ? Pill('Edited', icon: Icons.push_pin_outlined, color: s.secondaryContainer, onColor: s.onSecondaryContainer)
                          : Pill('Auto', icon: Icons.autorenew, color: s.surfaceContainerHighest, onColor: s.onSurfaceVariant),
                      if (l.kind == 'merchant') Text('part of ${AppScope.of(context).meta?.shortLabel(l.category ?? '') ?? l.category}', style: t.textTheme.labelSmall),
                      if (l.lastMonthPaise != null) Text('last month ${rupees(l.lastMonthPaise!)}', style: t.textTheme.labelSmall),
                    ]),
                    trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                      Text(rupees(l.budgetPaise), style: t.textTheme.titleSmall),
                      if (l.pinned)
                        IconButton(tooltip: 'Reset to auto', onPressed: _busy ? null : () => _reset(l), icon: const Icon(Icons.restart_alt, size: 20)),
                    ]),
                  ),
              ]),
            ),
          ],
        ]),
      ),
      if (widget.onNext != null)
        SaveBar(label: 'Next', busy: false, onPressed: hasLines ? widget.onNext : null),
    ]);
  }
}

const _monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
String _monthLabel(String ym) {
  final p = ym.split('-');
  final m = p.length == 2 ? int.tryParse(p[1]) : null;
  return m == null || m < 1 || m > 12 ? ym : '${_monthNames[m - 1]} ${p[0]}';
}

class BudgetScreen extends StatelessWidget {
  const BudgetScreen({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('Budget')), body: const BudgetPanel());
}
