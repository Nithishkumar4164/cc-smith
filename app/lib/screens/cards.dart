import 'package:flutter/material.dart';

import '../format.dart';
import '../models.dart';
import '../state.dart';
import '../widgets.dart';
import 'card_detail.dart';

String feeLabel(int? annualPaise) => annualPaise == null ? 'Fee unknown' : (annualPaise == 0 ? 'Lifetime free' : '${rupees(annualPaise)}/yr');

/// The catalogue: every card with the date its facts were last confirmed.
class CardsScreen extends StatefulWidget {
  const CardsScreen({super.key});
  @override
  State<CardsScreen> createState() => _CardsScreenState();
}

class _CardsScreenState extends State<CardsScreen> {
  String _q = '';
  bool _heldOnly = false;

  Future<void> _refresh() async {
    try {
      await AppScope.read(context).refreshCatalogue();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final held = {for (final h in app.me?.holdings ?? const <Holding>[]) h.cardId};
    final q = _q.toLowerCase();
    final cards = (app.cards ?? const <CardSummary>[])
        .where((c) => (!_heldOnly || held.contains(c.id)) && (q.isEmpty || c.name.toLowerCase().contains(q) || c.issuer.toLowerCase().contains(q)))
        .toList()
      ..sort((a, b) => a.issuer == b.issuer ? a.name.compareTo(b.name) : a.issuer.compareTo(b.issuer));
    final t = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Cards'), actions: const [ProfileAction()]),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 0, 16, 24), children: [
          TextField(
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search cards or banks'),
            onChanged: (v) => setState(() => _q = v),
          ),
          const SizedBox(height: 8),
          Row(children: [
            FilterChip(label: const Text('Cards I hold'), selected: _heldOnly, onSelected: (v) => setState(() => _heldOnly = v)),
            const Spacer(),
            Text('${cards.length} ${plural(cards.length, 'card')}', style: t.textTheme.labelMedium),
          ]),
          const SizedBox(height: 4),
          if (cards.isEmpty) const EmptyState(icon: Icons.credit_card_off_outlined, title: 'No cards match'),
          for (final c in cards) _CardTile(c: c, held: held.contains(c.id)),
        ]),
      ),
    );
  }
}

class _CardTile extends StatelessWidget {
  final CardSummary c;
  final bool held;
  const _CardTile({required this.c, required this.held});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final s = t.colorScheme;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CardDetailScreen(cardId: c.id))),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: 44,
              height: 30,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(6),
                gradient: LinearGradient(colors: [s.primary, s.tertiary]),
              ),
              alignment: Alignment.center,
              child: Text(c.issuer.isEmpty ? '' : c.issuer.split(' ').first.substring(0, 1), style: TextStyle(color: s.onPrimary, fontWeight: FontWeight.w800)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(c.name, style: t.textTheme.titleSmall),
                Text(c.issuer, style: t.textTheme.bodySmall?.copyWith(color: s.onSurfaceVariant)),
                const SizedBox(height: 8),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  if (held) Pill('You hold', icon: Icons.check, color: s.primary, onColor: s.onPrimary),
                  Pill(feeLabel(c.annualFeePaise)),
                  if (c.currencyKind != null) Pill(c.currencyKind == 'cashback' ? 'Cashback' : 'Points · ${c.currencyName ?? ''}'),
                  for (final o in c.feeOffers) FeeOfferPill(o),
                  if (c.speculationCount > 0) Pill('${c.speculationCount} unconfirmed ${plural(c.speculationCount, 'report')}', icon: Icons.help_outline, color: s.tertiaryContainer, onColor: s.onTertiaryContainer),
                  if (!c.assessable) Pill('Not scored yet', color: s.surfaceContainerHighest, onColor: s.onSurfaceVariant),
                  if (c.status != 'active') Pill(c.status, color: s.surfaceContainerHighest, onColor: s.onSurfaceVariant),
                ]),
                const SizedBox(height: 6),
                Text('Bank data as of ${shortDate(c.asOf)}', style: t.textTheme.labelSmall?.copyWith(color: s.onSurfaceVariant)),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}
