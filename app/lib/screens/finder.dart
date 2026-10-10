import 'package:flutter/material.dart';

import '../api.dart';
import '../format.dart';
import '../models.dart';
import '../state.dart';
import '../widgets.dart';
import 'card_detail.dart';
import 'budget.dart';
import 'editors.dart';

/// Card Finder: the 1–3 new cards that add the most rupees a year.
class FinderScreen extends StatefulWidget {
  const FinderScreen({super.key});
  @override
  State<FinderScreen> createState() => _FinderScreenState();
}

class _FinderScreenState extends State<FinderScreen> {
  Future<FinderReport>? _future;
  int _version = -1;
  int _maxNew = 3;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final app = AppScope.of(context);
    if (_version != app.dataVersion) {
      _version = app.dataVersion;
      _future = app.api.finder(maxNew: _maxNew);
    }
  }

  void _load() => setState(() => _future = AppScope.read(context).api.finder(maxNew: _maxNew));

  void _editSpends() => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const BudgetScreen()));

  void _editPrefs() => Navigator.of(context).push(MaterialPageRoute(
        builder: (ctx) => Scaffold(
          appBar: AppBar(title: const Text('Finder preferences')),
          body: PreferencesEditor(actionLabel: 'Save', memberships: false, onSaved: () => Navigator.of(ctx).pop()),
        ),
      ));

  @override
  Widget build(BuildContext context) {
    if (!AppScope.of(context).finderPrefsSet) {
      return Scaffold(
        appBar: AppBar(title: const Text('Card Finder'), actions: const [ProfileAction()]),
        body: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
            child: Text('Before we look for new cards: what kind of rewards do you want, and how much annual fee would you pay?',
                style: Theme.of(context).textTheme.titleMedium),
          ),
          Expanded(
            child: PreferencesEditor(
              actionLabel: 'Find my best cards',
              memberships: false,
              onSaved: () => AppScope.read(context).markFinderPrefsSet(),
            ),
          ),
        ]),
      );
    }
    return Scaffold(
      appBar: AppBar(
        title: const Text('Card Finder'),
        actions: [
          IconButton(onPressed: _editPrefs, tooltip: 'Finder preferences', icon: const Icon(Icons.tune)),
          TextButton.icon(onPressed: _editSpends, icon: const Icon(Icons.edit_outlined, size: 18), label: const Text('Spends')),
          const ProfileAction(),
        ],
      ),
      body: FutureBuilder<FinderReport>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
          if (snap.hasError) {
            final e = snap.error;
            if (e is ApiException && e.status == 422) {
              return EmptyState(
                icon: Icons.savings_outlined,
                title: 'Add your monthly spends',
                message: e.message,
                action: FilledButton(onPressed: _editSpends, child: const Text('Add spends')),
              );
            }
            return ErrorRetry(error: e!, onRetry: _load);
          }
          return RefreshIndicator(
            onRefresh: () async {
              _load();
              await _future;
            },
            child: _FinderBody(
              r: snap.data!,
              maxNew: _maxNew,
              onMaxNew: (n) {
                _maxNew = n;
                _load();
              },
            ),
          );
        },
      ),
    );
  }
}

class _FinderBody extends StatelessWidget {
  final FinderReport r;
  final int maxNew;
  final ValueChanged<int> onMaxNew;
  const _FinderBody({required this.r, required this.maxNew, required this.onMaxNew});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final meta = app.meta;
    final t = Theme.of(context);
    final s = t.colorScheme;
    final best = r.portfolios.isNotEmpty ? r.portfolios.first : null;
    return ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 32), children: [
      Card(
        color: s.primaryContainer,
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('YOUR CARDS TODAY', style: t.textTheme.labelMedium?.copyWith(color: s.onPrimaryContainer, letterSpacing: 1.2)),
            const SizedBox(height: 4),
            Text('${rupees(r.baseNetPaise)}/yr net',
                style: t.textTheme.headlineSmall?.copyWith(color: s.onPrimaryContainer, fontWeight: FontWeight.w700)),
            Text('rewards + milestones − fees, on your spends', style: t.textTheme.bodySmall?.copyWith(color: s.onPrimaryContainer)),
            if (best != null && best.gainPaise > 0) ...[
              const SizedBox(height: 14),
              Text('Best move: add ${best.newCards.map(app.cardName).join(' + ')}',
                  style: t.textTheme.titleMedium?.copyWith(color: s.onPrimaryContainer)),
              Text('${rupees(best.gainPaise, signed: true)}/yr more',
                  style: t.textTheme.titleLarge?.copyWith(color: s.onPrimaryContainer, fontWeight: FontWeight.w800)),
            ],
          ]),
        ),
      ),
      const SizedBox(height: 8),
      Row(children: [
        Expanded(child: Text('New cards at most', style: t.textTheme.labelLarge)),
        SegmentedButton<int>(
          showSelectedIcon: false,
          segments: const [ButtonSegment(value: 1, label: Text('1')), ButtonSegment(value: 2, label: Text('2')), ButtonSegment(value: 3, label: Text('3'))],
          selected: {maxNew},
          onSelectionChanged: (v) => onMaxNew(v.first),
        ),
      ]),
      const SectionHeader('Top card sets'),
      if (r.portfolios.isEmpty)
        const Card(child: ListTile(leading: Icon(Icons.check_circle_outline), title: Text('No new card beats what you hold, within your fee and reward preferences.'))),
      for (final (i, p) in r.portfolios.take(5).indexed) _PortfolioCard(p: p, rank: i + 1, initiallyExpanded: i == 0),
      if (r.keepOrClose.isNotEmpty) ...[
        const SectionHeader('Cards you hold: keep or close?'),
        Card(
          child: Column(children: [
            for (final e in r.keepOrClose.entries)
              ListTile(
                title: Text(app.cardName(e.key)),
                subtitle: Text(e.value >= 0
                    ? 'Worth ${rupees(e.value)}/yr to you — keep it'
                    : 'Closing it would save ${rupees(-e.value)}/yr on these spends'),
                trailing: Pill(e.value >= 0 ? 'Keep' : 'Consider closing',
                    color: e.value >= 0 ? s.primaryContainer : s.errorContainer, onColor: e.value >= 0 ? s.onPrimaryContainer : s.onErrorContainer),
                onTap: () => _openCard(context, e.key),
              ),
          ]),
        ),
      ],
      if (r.unearned.isNotEmpty) ...[
        const SectionHeader('Where you earn ₹0 today'),
        Card(
          child: Column(children: [
            for (final e in r.unearned.entries)
              ListTile(
                dense: true,
                leading: Icon(Icons.money_off, color: s.error),
                title: Text(meta?.label(e.key) ?? e.key),
                trailing: Text('${rupees(e.value)}/yr spend', style: t.textTheme.labelLarge),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              child: Text('None of your cards rewards these (excluded or no matching rule).', style: t.textTheme.bodySmall),
            ),
          ]),
        ),
      ],
      if (r.notAssessable.isNotEmpty) ...[
        const SectionHeader('Not scored'),
        Card(
          child: ListTile(
            leading: const Icon(Icons.hourglass_empty),
            title: Text(r.notAssessable.map(app.cardName).join(', ')),
            subtitle: const Text("We don't yet have enough facts from the bank's own pages to score these."),
          ),
        ),
      ],
      const SizedBox(height: 12),
      Text('Annual figures from your monthly spends × 12. Every rate comes from the issuing bank\'s page — tap a card to see the quote.',
          style: t.textTheme.bodySmall?.copyWith(color: s.onSurfaceVariant)),
    ]);
  }
}

void _openCard(BuildContext context, String id) =>
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => CardDetailScreen(cardId: id)));

class _PortfolioCard extends StatelessWidget {
  final Portfolio p;
  final int rank;
  final bool initiallyExpanded;
  const _PortfolioCard({required this.p, required this.rank, required this.initiallyExpanded});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = Theme.of(context);
    final s = t.colorScheme;
    final newOnes = p.cards.where((c) => p.newCards.contains(c.cardId)).toList();
    final held = p.cards.where((c) => !p.newCards.contains(c.cardId)).toList();
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Theme(
        data: t.copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: initiallyExpanded,
          leading: CircleAvatar(radius: 14, backgroundColor: s.tertiaryContainer, child: Text('$rank', style: TextStyle(fontSize: 12, color: s.onTertiaryContainer))),
          title: Text('Add ${p.newCards.map(app.cardName).join(' + ')}', style: t.textTheme.titleSmall),
          subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Money(p.gainPaise, signed: true, suffix: '/yr more', style: t.textTheme.titleMedium),
            if (p.joiningFeePaise > 0)
              Text('One-time joining fees ${rupees(p.joiningFeePaise)} (first year)', style: t.textTheme.labelSmall),
          ]),
          childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
          children: [
            for (final c in newOnes) _CardBreakdown(c: c, isNew: true, feeOffers: p.feeOffers[c.cardId] ?? const []),
            if (held.isNotEmpty) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(4, 8, 4, 4),
                child: Text('Your cards in this set', style: t.textTheme.labelMedium?.copyWith(color: s.onSurfaceVariant)),
              ),
              for (final c in held) _CardBreakdown(c: c, isNew: false),
            ],
          ],
        ),
      ),
    );
  }
}

class _CardBreakdown extends StatelessWidget {
  final CardResult c;
  final bool isNew;
  final List<FeeOffer> feeOffers;
  const _CardBreakdown({required this.c, required this.isNew, this.feeOffers = const []});

  @override
  Widget build(BuildContext context) {
    final meta = AppScope.of(context).meta;
    final t = Theme.of(context);
    final s = t.colorScheme;
    final small = t.textTheme.bodySmall;
    Widget row(String l, Widget r, {TextStyle? style}) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 2),
          child: Row(children: [Expanded(child: Text(l, style: style ?? small)), r]),
        );
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => _openCard(context, c.cardId),
      child: Container(
        margin: const EdgeInsets.only(top: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isNew ? s.surfaceContainerHighest.withValues(alpha: 0.7) : null,
          border: Border.all(color: isNew ? s.tertiary : s.outlineVariant),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            if (isNew) ...[Pill('NEW', color: s.tertiary, onColor: s.onTertiary), const SizedBox(width: 8)],
            Expanded(child: Text(c.name, style: t.textTheme.titleSmall)),
            const Icon(Icons.chevron_right, size: 18),
          ]),
          if (feeOffers.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Wrap(spacing: 6, runSpacing: 4, children: [for (final o in feeOffers) FeeOfferPill(o)]),
            ),
          for (final c in {for (final o in feeOffers) for (final r in o.requires) r.key: r}.values)
            if (AppScope.of(context).answers[c.key] == null) ConditionAsk(c),
          const SizedBox(height: 8),
          if (c.lines.isEmpty) Text('No spends routed to this card', style: small),
          for (final l in c.lines)
            row(
              '${meta?.shortLabel(l.spendKey) ?? l.spendKey} · ${rupees(l.spendPaise)}/yr',
              Row(mainAxisSize: MainAxisSize.min, children: [
                if (l.capped) ...[Pill('capped', color: s.errorContainer, onColor: s.onErrorContainer), const SizedBox(width: 6)],
                Money(l.rewardPaise, style: t.textTheme.labelLarge),
              ]),
            ),
          if (c.milestonePaise > 0) row('Milestone benefits', Money(c.milestonePaise, style: t.textTheme.labelLarge)),
          for (final m in c.milestonesHit)
            Padding(
              padding: const EdgeInsets.only(left: 12, bottom: 2),
              child: Text('• $m', style: small?.copyWith(color: s.onSurfaceVariant)),
            ),
          row(
            c.feeWaived
                ? 'Annual fee (waived on your spend)'
                : 'Annual fee${c.feeIncludesGst ? ' incl. GST' : ''}',
            Text(c.feeWaived ? '₹0' : '−${rupees(c.feePaise)}', style: t.textTheme.labelLarge?.copyWith(color: c.feeWaived ? moneyColor(context) : s.error)),
          ),
          const Divider(height: 14),
          row('Net per year', Money(c.netPaise, style: t.textTheme.titleSmall), style: t.textTheme.titleSmall),
        ]),
      ),
    );
  }
}
