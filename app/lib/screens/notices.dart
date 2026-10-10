import 'package:flutter/material.dart';

import '../format.dart';
import '../models.dart';
import '../state.dart';
import '../widgets.dart';
import 'card_detail.dart';

/// Notice board: what needs doing on the cards you hold, most urgent first.
class NoticesScreen extends StatelessWidget {
  const NoticesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final notices = app.notices;
    Widget body;
    if (notices == null && app.noticesError == null) {
      body = const Center(child: CircularProgressIndicator());
    } else if (notices == null) {
      body = ListView(children: [ErrorRetry(error: app.noticesError!, onRetry: app.refreshUserData)]);
    } else if (notices.isEmpty) {
      body = ListView(children: const [
        SizedBox(height: 60),
        EmptyState(
          icon: Icons.task_alt,
          title: 'Nothing needs you right now',
          message: 'Fee renewals, caps running out, milestones within reach and credit use show up here.',
        ),
      ]);
    } else {
      body = NoticeList(notices: notices);
    }
    return Scaffold(
      appBar: AppBar(title: const Text('Notices'), actions: const [ProfileAction()]),
      body: RefreshIndicator(onRefresh: app.refreshUserData, child: body),
    );
  }
}

(Color, Color, String, IconData) severityStyle(BuildContext context, String severity) {
  final s = Theme.of(context).colorScheme;
  return switch (severity) {
    'act' => (s.error, s.errorContainer, 'Act now', Icons.priority_high),
    'watch' => (s.tertiary, s.tertiaryContainer, 'Keep an eye', Icons.visibility_outlined),
    _ => (s.primary, s.primaryContainer, 'Good to know', Icons.info_outline),
  };
}

IconData noticeIcon(String kind) => switch (kind) {
  'fee' => Icons.receipt_long_outlined,
  'cap' => Icons.speed,
  'milestone' => Icons.flag_outlined,
  'credit' => Icons.account_balance_wallet_outlined,
  'fee_offer' => Icons.card_giftcard,
  'offer' => Icons.local_offer_outlined,
  'card_change' => Icons.change_circle_outlined,
  'launch' => Icons.rocket_launch_outlined,
  _ => Icons.notifications_none,
};

class NoticeCard extends StatelessWidget {
  final Notice n;
  const NoticeCard({super.key, required this.n});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = Theme.of(context);
    final s = t.colorScheme;
    final (stripe, chipBg, label, icon) = severityStyle(context, n.severity);
    final onChip = switch (n.severity) {
      'act' => s.onErrorContainer,
      'watch' => s.onTertiaryContainer,
      _ => s.onPrimaryContainer,
    };
    return Card(
      clipBehavior: Clip.antiAlias,
      child: DecoratedBox(
        decoration: BoxDecoration(border: Border(left: BorderSide(color: stripe, width: 5))),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 14, 4),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Wrap(spacing: 8, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
                  Pill(label, icon: icon, color: chipBg, onColor: onChip),
                  if (n.due != null) Pill('By ${shortDate(n.due)}', icon: Icons.event, color: s.surfaceContainerHigh, onColor: s.onSurface),
                  if (n.tier == 'speculation') const SpeculationPill(),
                  if (n.isGuidance) Pill('General guidance', icon: Icons.lightbulb_outline, color: s.surfaceContainerHighest, onColor: s.onSurfaceVariant),
                ]),
                const SizedBox(height: 8),
                Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Icon(noticeIcon(n.kind), size: 20, color: stripe),
                  const SizedBox(width: 8),
                  Expanded(child: Text(n.title, style: t.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700))),
                ]),
                if (n.rupeesPaise != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 6, left: 28),
                    child: Text('${rupees(n.rupeesPaise!)} at stake',
                        style: t.textTheme.titleMedium?.copyWith(color: moneyColor(context), fontWeight: FontWeight.w800)),
                  ),
                const SizedBox(height: 8),
                _Labelled('Why', n.reason),
                _Labelled('What to do', n.action),
                if (n.cardId != null)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      style: TextButton.styleFrom(padding: EdgeInsets.zero, visualDensity: VisualDensity.compact),
                      onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CardDetailScreen(cardId: n.cardId!))),
                      icon: const Icon(Icons.credit_card, size: 16),
                      label: Text(app.cardName(n.cardId!), overflow: TextOverflow.ellipsis),
                    ),
                  ),
                for (final c in n.requires) ConditionAsk(c),
                // Guidance is general advice, not a bank statement: no source to show.
                if (!n.isGuidance) SourceList(refs: n.refs, label: n.tier == 'fact' ? 'Source' : 'References'),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}

class _Labelled extends StatelessWidget {
  final String label, text;
  const _Labelled(this.label, this.text);
  @override
  Widget build(BuildContext context) {
    if (text.isEmpty) return const SizedBox.shrink();
    final t = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Text.rich(TextSpan(children: [
        TextSpan(text: '$label  ', style: t.textTheme.labelMedium?.copyWith(color: t.colorScheme.primary, fontWeight: FontWeight.w700)),
        TextSpan(text: text, style: t.textTheme.bodyMedium),
      ])),
    );
  }
}


/// Notices with a summary line; ones whose conditions the user said No to collapse into
/// "Not for you (N)" at the end. Unanswered ones stay in the list with their question.
class NoticeList extends StatelessWidget {
  final List<Notice> notices;
  final bool showCounts;
  final Widget? header;
  const NoticeList({super.key, required this.notices, this.showCounts = true, this.header});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    String elig(Notice n) => eligibilityFor(n.requires, app.answers, n.eligibility);
    final notForYou = notices.where((n) => elig(n) == 'no').toList();
    final shown = notices.where((n) => elig(n) != 'no').toList();
    final act = shown.where((n) => n.severity == 'act').length;
    final watch = shown.where((n) => n.severity == 'watch').length;
    return ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 24), children: [
      ?header,
      if (showCounts)
        Text(
          [if (act > 0) '$act to act on', if (watch > 0) '$watch to keep an eye on', if (act + watch == 0) 'All good'].join(' · '),
          style: Theme.of(context).textTheme.titleSmall,
        ),
      const SizedBox(height: 4),
      for (final n in shown) NoticeCard(n: n),
      if (notForYou.isNotEmpty)
        Card(
          child: Theme(
            data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
            child: ExpansionTile(
              leading: const Icon(Icons.block),
              title: Text('Not for you (${notForYou.length})'),
              subtitle: const Text('Offers whose conditions you said you don\'t meet'),
              childrenPadding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
              children: [for (final n in notForYou) NoticeCard(n: n)],
            ),
          ),
        ),
    ]);
  }
}
