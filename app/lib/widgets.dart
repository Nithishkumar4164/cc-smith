import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api.dart';
import 'format.dart';
import 'models.dart';

void showError(BuildContext context, Object e) {
  final msg = e is ApiException ? e.message : 'Something went wrong: $e';
  final m = ScaffoldMessenger.maybeOf(context);
  m?.hideCurrentSnackBar();
  m?.showSnackBar(SnackBar(
    content: Text(msg),
    backgroundColor: Theme.of(context).colorScheme.errorContainer,
    behavior: SnackBarBehavior.floating,
    showCloseIcon: true,
    closeIconColor: Theme.of(context).colorScheme.onErrorContainer,
  ));
}

void showInfo(BuildContext context, String msg) {
  final m = ScaffoldMessenger.maybeOf(context);
  m?.hideCurrentSnackBar();
  m?.showSnackBar(SnackBar(content: Text(msg), behavior: SnackBarBehavior.floating));
}

Future<void> openUrl(BuildContext context, String url) async {
  final uri = Uri.tryParse(url);
  if (uri == null || !(uri.scheme == 'https' || uri.scheme == 'http')) {
    showError(context, ApiException('Not a web link: $url'));
    return;
  }
  final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
  if (!ok && context.mounted) showError(context, ApiException("Couldn't open $url"));
}

String hostOf(String url) => Uri.tryParse(url)?.host.replaceFirst('www.', '') ?? url;

class EmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? message;
  final Widget? action;
  const EmptyState({super.key, required this.icon, required this.title, this.message, this.action});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 48, color: t.colorScheme.outline),
          const SizedBox(height: 16),
          Text(title, style: t.textTheme.titleMedium, textAlign: TextAlign.center),
          if (message != null) ...[
            const SizedBox(height: 8),
            Text(message!, style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant), textAlign: TextAlign.center),
          ],
          if (action != null) ...[const SizedBox(height: 20), action!],
        ]),
      ),
    );
  }
}

class ErrorRetry extends StatelessWidget {
  final Object error;
  final VoidCallback onRetry;
  const ErrorRetry({super.key, required this.error, required this.onRetry});
  @override
  Widget build(BuildContext context) => EmptyState(
        icon: Icons.cloud_off_outlined,
        title: 'Couldn\'t load this',
        message: error is ApiException ? (error as ApiException).message : '$error',
        action: FilledButton.tonalIcon(onPressed: onRetry, icon: const Icon(Icons.refresh), label: const Text('Try again')),
      );
}

class SectionHeader extends StatelessWidget {
  final String text;
  final Widget? trailing;
  const SectionHeader(this.text, {super.key, this.trailing});
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 20, 4, 8),
      child: Row(children: [
        Expanded(
          child: Text(text.toUpperCase(),
              style: t.textTheme.labelMedium?.copyWith(color: t.colorScheme.primary, letterSpacing: 1.1, fontWeight: FontWeight.w700)),
        ),
        ?trailing,
      ]),
    );
  }
}

/// Small rounded label.
class Pill extends StatelessWidget {
  final String text;
  final Color? color;
  final Color? onColor;
  final IconData? icon;
  const Pill(this.text, {super.key, this.color, this.onColor, this.icon});
  @override
  Widget build(BuildContext context) {
    final s = Theme.of(context).colorScheme;
    final bg = color ?? s.secondaryContainer;
    final fg = onColor ?? s.onSecondaryContainer;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(20)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (icon != null) ...[Icon(icon, size: 13, color: fg), const SizedBox(width: 4)],
        Flexible(
          child: Text(text,
              overflow: TextOverflow.ellipsis,
              maxLines: 2,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(color: fg, fontWeight: FontWeight.w600)),
        ),
      ]),
    );
  }
}

/// The DR-12 label for anything not stated by the bank itself.
class SpeculationPill extends StatelessWidget {
  const SpeculationPill({super.key});
  @override
  Widget build(BuildContext context) {
    final s = Theme.of(context).colorScheme;
    return Pill('Reported, not confirmed by the bank', icon: Icons.help_outline, color: s.tertiaryContainer, onColor: s.onTertiaryContainer);
  }
}

class OfficialPill extends StatelessWidget {
  final String text;
  const OfficialPill({super.key, this.text = 'Confirmed by bank'});
  @override
  Widget build(BuildContext context) {
    final s = Theme.of(context).colorScheme;
    return Pill(text, icon: Icons.verified_outlined, color: s.primaryContainer, onColor: s.onPrimaryContainer);
  }
}

/// "Source" disclosure: verbatim quote, the page it came from, fetch date.
class SourceList extends StatelessWidget {
  final List<Ref> refs;
  final String? asOf;
  final String label;
  const SourceList({super.key, required this.refs, this.asOf, this.label = 'Source'});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    if (refs.isEmpty) return const SizedBox.shrink();
    return Theme(
      data: t.copyWith(dividerColor: Colors.transparent),
      child: ExpansionTile(
        dense: true,
        tilePadding: EdgeInsets.zero,
        childrenPadding: const EdgeInsets.only(bottom: 8),
        visualDensity: VisualDensity.compact,
        leading: Icon(Icons.format_quote_rounded, size: 18, color: t.colorScheme.primary),
        title: Text(
          refs.length == 1 ? '$label · ${hostOf(refs.first.url)}' : '$label · ${refs.length} quotes',
          style: t.textTheme.labelLarge?.copyWith(color: t.colorScheme.primary),
        ),
        children: [for (final r in refs) _RefView(r, asOf: asOf)],
      ),
    );
  }
}

class _RefView extends StatelessWidget {
  final Ref r;
  final String? asOf;
  const _RefView(this.r, {this.asOf});
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final s = t.colorScheme;
    return Container(
      margin: const EdgeInsets.only(top: 6),
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 6),
      decoration: BoxDecoration(
        color: s.surfaceContainerHighest.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(10),
        border: Border(left: BorderSide(color: r.official == false ? s.tertiary : s.primary, width: 3)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (r.quote != null && r.quote!.isNotEmpty)
          SelectableText('“${r.quote}”', style: t.textTheme.bodySmall?.copyWith(fontStyle: FontStyle.italic, height: 1.4)),
        if ((r.quote == null || r.quote!.isEmpty) && r.title != null)
          Text(r.title!, style: t.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        Wrap(spacing: 8, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
          if (r.official == true) const OfficialPill(text: 'Official bank page'),
          if (r.kind == 'ad') Pill('Bank ad', color: s.surfaceContainerHigh, onColor: s.onSurface),
          if (r.kind == 'news') Pill('News', color: s.surfaceContainerHigh, onColor: s.onSurface),
          if (r.official == false && r.kind != 'ad') Pill('Not an official source', color: s.tertiaryContainer, onColor: s.onTertiaryContainer),
          if (r.fetchedAt != null) Text('Fetched ${shortDate(r.fetchedAt)}', style: t.textTheme.labelSmall),
          if (asOf != null) Text('As of ${shortDate(asOf)}', style: t.textTheme.labelSmall),
        ]),
        if (r.url.isNotEmpty)
          TextButton.icon(
            style: TextButton.styleFrom(padding: EdgeInsets.zero, visualDensity: VisualDensity.compact),
            onPressed: () => openUrl(context, r.url),
            icon: const Icon(Icons.open_in_new, size: 16),
            label: Text(hostOf(r.url), overflow: TextOverflow.ellipsis),
          ),
      ]),
    );
  }
}

/// Money in the brand accent colour.
class Money extends StatelessWidget {
  final int paise;
  final TextStyle? style;
  final bool signed;
  final String suffix;
  const Money(this.paise, {super.key, this.style, this.signed = false, this.suffix = ''});
  @override
  Widget build(BuildContext context) {
    final s = Theme.of(context).colorScheme;
    final color = paise < 0 ? s.error : (paise == 0 ? s.onSurfaceVariant : moneyColor(context));
    return Text('${rupees(paise, signed: signed)}$suffix',
        style: (style ?? Theme.of(context).textTheme.titleMedium)?.copyWith(color: color, fontWeight: FontWeight.w700));
  }
}

Color moneyColor(BuildContext context) =>
    Theme.of(context).brightness == Brightness.dark ? const Color(0xFF7FD6A8) : const Color(0xFF1B7A4B);

/// App-bar avatar that opens Profile (cards, spends, credit, settings).
class ProfileAction extends StatelessWidget {
  const ProfileAction({super.key});
  @override
  Widget build(BuildContext context) {
    final s = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: IconButton(
        tooltip: 'Profile',
        onPressed: () => Navigator.of(context).pushNamed('/profile'),
        icon: CircleAvatar(radius: 15, backgroundColor: s.primaryContainer, child: Icon(Icons.person, size: 18, color: s.onPrimaryContainer)),
      ),
    );
  }
}

/// "First year free · bank page" or the speculation label for a fee offer.
class FeeOfferPill extends StatelessWidget {
  final FeeOffer o;
  const FeeOfferPill(this.o, {super.key});
  @override
  Widget build(BuildContext context) {
    final s = Theme.of(context).colorScheme;
    return o.isFact
        ? Pill('${o.kindLabel} · bank page', icon: Icons.card_giftcard, color: s.primaryContainer, onColor: s.onPrimaryContainer)
        : Pill('${o.kindLabel} · reported, not confirmed', icon: Icons.help_outline, color: s.tertiaryContainer, onColor: s.onTertiaryContainer);
  }
}

/// Full fee offer: title, conditions, validity and source.
class FeeOfferView extends StatelessWidget {
  final FeeOffer o;
  const FeeOfferView(this.o, {super.key});
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final cond = [
      if (o.spendConditionPaise != null)
        'Spend ${rupees(o.spendConditionPaise!)}${o.spendWindowDays != null ? ' in ${o.spendWindowDays} days' : ''}',
      if (o.validTo != null) 'till ${shortDate(o.validTo)}',
    ];
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      FeeOfferPill(o),
      const SizedBox(height: 6),
      Text(o.title, style: t.textTheme.bodyLarge),
      if (cond.isNotEmpty) Text(cond.join(' · '), style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
      if (o.source != null) SourceList(refs: [o.source!], label: o.isFact ? 'Source' : 'Reference'),
    ]);
  }
}
