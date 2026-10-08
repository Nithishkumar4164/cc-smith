import 'package:flutter/material.dart';

import '../describe.dart';
import '../format.dart';
import '../models.dart';
import '../state.dart';
import '../widgets.dart';
import 'card_detail.dart';

/// Launch Radar plus the recent fact changes across the catalogue.
class MarketScreen extends StatefulWidget {
  const MarketScreen({super.key});
  @override
  State<MarketScreen> createState() => _MarketScreenState();
}

class _MarketScreenState extends State<MarketScreen> {
  Future<List<Launch>>? _launches;
  Future<List<ChangeEvent>>? _changes;
  int _version = -1;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final app = AppScope.of(context);
    if (_version != app.dataVersion) {
      _version = app.dataVersion;
      _fetch();
    }
  }

  void _fetch() {
    final api = AppScope.read(context).api;
    _launches = api.launches();
    _changes = api.changes(limit: 40);
  }

  void _load() => setState(_fetch);

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Market'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Launch Radar'),
              Tab(text: 'What changed'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            RefreshIndicator(
              onRefresh: () async {
                _load();
                await _launches;
              },
              child: _LaunchList(future: _launches),
            ),
            RefreshIndicator(
              onRefresh: () async {
                _load();
                await _changes;
              },
              child: _ChangeList(future: _changes),
            ),
          ],
        ),
      ),
    );
  }
}

class _LaunchList extends StatelessWidget {
  final Future<List<Launch>>? future;
  const _LaunchList({required this.future});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Launch>>(
      future: future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        if (snap.hasError) {
          return ListView(
            children: [ErrorRetry(error: snap.error!, onRetry: () => (context as Element).markNeedsBuild())],
          );
        }
        final items = snap.data!.where((l) => !l.rejected).toList();
        if (items.isEmpty) {
          return ListView(
            children: const [
              SizedBox(height: 60),
              EmptyState(
                icon: Icons.radar,
                title: 'No new launches spotted yet',
                message:
                    'Launch Radar watches bank card ads and launch news each night. New cards appear here, '
                    'scored against your spends once the bank publishes its own page.',
              ),
            ],
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          children: [for (final l in items) _LaunchCard(l: l)],
        );
      },
    );
  }
}

class _LaunchCard extends StatelessWidget {
  final Launch l;
  const _LaunchCard({required this.l});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = Theme.of(context);
    final s = t.colorScheme;
    final inCatalogue = l.cardId != null && app.cardsById.containsKey(l.cardId);
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 6,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                if (l.confirmed)
                  const OfficialPill(text: 'Confirmed by bank')
                else if (l.known)
                  Pill(
                    'Already in catalogue',
                    icon: Icons.library_books_outlined,
                    color: s.secondaryContainer,
                    onColor: s.onSecondaryContainer,
                  )
                else
                  const SpeculationPill(),
                Text('Spotted ${shortDate(l.firstSeen)}', style: t.textTheme.labelSmall),
              ],
            ),
            const SizedBox(height: 8),
            Text(l.name, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
            if (l.issuer != null) Text(l.issuer!, style: t.textTheme.bodySmall?.copyWith(color: s.onSurfaceVariant)),
            if (l.summary != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(l.summary!)),
            if (l.confirmed && l.gainPaise != null)
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Row(
                  children: [
                    Icon(
                      l.gainPaise! > 0 ? Icons.trending_up : Icons.trending_down,
                      size: 20,
                      color: l.gainPaise! > 0 ? moneyColor(context) : s.error,
                    ),
                    const SizedBox(width: 6),
                    Flexible(
                      child: l.gainPaise! > 0
                          ? Money(l.gainPaise!, suffix: '/yr for you', signed: true)
                          : Text(
                              l.gainPaise! == 0
                                  ? 'Adds nothing on your spends'
                                  : 'Not worth it for you: ${rupees(l.gainPaise!)}/yr after fees',
                              style: t.textTheme.bodyMedium?.copyWith(color: s.error),
                            ),
                    ),
                  ],
                ),
              )
            else if (l.confirmed)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text('Add your monthly spends to see what it is worth to you.', style: t.textTheme.bodySmall),
              )
            else if (l.speculative)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Not scored: we only do rupee maths on facts from the bank\'s own page.',
                  style: t.textTheme.bodySmall,
                ),
              ),
            SourceList(refs: l.refs, label: 'References'),
            if (inCatalogue)
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () => Navigator.of(
                    context,
                  ).push(MaterialPageRoute(builder: (_) => CardDetailScreen(cardId: l.cardId!))),
                  child: const Text('View card'),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ChangeList extends StatelessWidget {
  final Future<List<ChangeEvent>>? future;
  const _ChangeList({required this.future});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = Theme.of(context);
    final s = t.colorScheme;
    return FutureBuilder<List<ChangeEvent>>(
      future: future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        if (snap.hasError) {
          return ListView(
            children: [
              EmptyState(icon: Icons.cloud_off_outlined, title: 'Couldn\'t load changes', message: '${snap.error}'),
            ],
          );
        }
        final items = snap.data!;
        if (items.isEmpty) {
          return ListView(
            children: const [EmptyState(icon: Icons.history, title: 'No changes recorded yet')],
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          children: [
            Text(
              'Every change to a card\'s facts, as published from the bank\'s own pages.',
              style: t.textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            for (final e in items)
              Card(
                child: ListTile(
                  title: Text(app.cardName(e.cardId)),
                  subtitle: Text(
                    '${fieldTitle(e.field ?? 'card')} ${e.eventType.replaceAll('_', ' ')} · ${shortDate(e.at)}',
                  ),
                  trailing: e.largeChange
                      ? Pill('Big change', color: s.errorContainer, onColor: s.onErrorContainer)
                      : (e.tier == 'speculation'
                            ? Pill('Unconfirmed', color: s.tertiaryContainer, onColor: s.onTertiaryContainer)
                            : null),
                  onTap: () =>
                      Navigator.of(context).push(MaterialPageRoute(builder: (_) => CardDetailScreen(cardId: e.cardId))),
                ),
              ),
          ],
        );
      },
    );
  }
}
