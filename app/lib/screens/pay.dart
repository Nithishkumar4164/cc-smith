import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
import '../describe.dart';
import '../format.dart';
import '../models.dart';
import '../state.dart';
import '../upi.dart';
import '../widgets.dart';
import 'card_detail.dart';
import 'scan.dart';

/// Checkout Advisor: which held card earns the most on this payment.
class PayScreen extends StatefulWidget {
  const PayScreen({super.key});
  @override
  State<PayScreen> createState() => _PayScreenState();
}

/// null = let the server infer the channel from the merchant.
const _channels = <String?, String>{null: 'Auto', 'online': 'Online', 'offline': 'In-store', 'upi': 'UPI'};

class _PayScreenState extends State<PayScreen> {
  final _merchant = TextEditingController();
  final _amount = TextEditingController();
  final _amountFocus = FocusNode();
  final _merchantFocus = FocusNode();
  String? _channel;
  String? _mcc; // from a scanned QR
  bool _busy = false;
  PayResult? _result;
  _PayRequest? _request;
  final _confirmed = <String>{}; // card ids confirmed for the current result

  @override
  void dispose() {
    _merchant.dispose();
    _amount.dispose();
    _amountFocus.dispose();
    _merchantFocus.dispose();
    super.dispose();
  }

  Future<void> _ask() async {
    final merchant = _merchant.text.trim();
    final amount = parseRupeesToPaise(_amount.text);
    if (merchant.isEmpty) {
      showError(context, const ApiException('Enter where you are paying.'));
      return;
    }
    if (amount == null || amount <= 0) {
      showError(context, const ApiException('Enter the amount in rupees.'));
      _amountFocus.requestFocus();
      return;
    }
    FocusScope.of(context).unfocus();
    final req = _PayRequest(merchant, amount, _channel, _mcc, newIdempotencyKey());
    setState(() => _busy = true);
    try {
      final r = await AppScope.read(context).api.pay(merchant: merchant, amountPaise: amount, channel: _channel, mcc: _mcc);
      setState(() {
        _result = r;
        _request = req;
        _confirmed.clear();
      });
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _scan() async {
    final upi = await Navigator.of(context).push<UpiPayment>(MaterialPageRoute(builder: (_) => const ScanScreen()));
    if (upi == null || !mounted) return;
    setState(() {
      _merchant.text = upi.merchant;
      _mcc = upi.mcc;
      _channel = 'upi';
      if (upi.amountPaise != null) _amount.text = _rupeeInput(upi.amountPaise!);
      _result = null;
    });
    if (upi.amountPaise != null) {
      await _ask();
    } else {
      showInfo(context, 'Scanned ${upi.merchant}${upi.mcc != null ? ' (MCC ${upi.mcc})' : ''}. Enter the amount.');
      _amountFocus.requestFocus();
    }
  }

  String _rupeeInput(int paise) => paise % 100 == 0 ? '${paise ~/ 100}' : (paise / 100).toStringAsFixed(2);

  Future<void> _confirm(PayOption o) async {
    final req = _request!;
    try {
      final reward = await AppScope.read(context).api.confirm(
            cardId: o.cardId,
            merchant: req.merchant,
            amountPaise: req.amountPaise,
            channel: req.channel,
            mcc: req.mcc,
            // One key per (advice, card): a double tap or retry records once.
            idempotencyKey: '${req.nonce}-${o.cardId}',
          );
      if (!mounted) return;
      setState(() => _confirmed.add(o.cardId));
      AppScope.read(context).bumpData();
      showInfo(context, 'Logged ${rupees(req.amountPaise)} on ${o.name}: ${rupees(reward)} reward. Caps updated.');
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  void _clearScan() => setState(() => _mcc = null);

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final merchants = app.meta?.merchants ?? const <MerchantMeta>[];
    final t = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Checkout Advisor'),
        actions: [IconButton(tooltip: 'Scan UPI QR', onPressed: _scan, icon: const Icon(Icons.qr_code_scanner)), const ProfileAction()],
      ),
      body: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 32), children: [
        Text('Which card should I pay with?', style: t.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)),
        const SizedBox(height: 16),
        RawAutocomplete<MerchantMeta>(
          textEditingController: _merchant,
          focusNode: _merchantFocus,
          displayStringForOption: (m) => m.name,
          optionsBuilder: (v) {
            final q = v.text.trim().toLowerCase();
            if (q.isEmpty) return const Iterable<MerchantMeta>.empty();
            return merchants.where((m) => m.name.toLowerCase().contains(q) || m.key.contains(q)).take(6);
          },
          onSelected: (_) => _amountFocus.requestFocus(),
          fieldViewBuilder: (context, ctrl, focus, onSubmit) => TextField(
            controller: ctrl,
            focusNode: focus,
            textInputAction: TextInputAction.next,
            onChanged: (_) => _mcc == null ? null : _clearScan(),
            onSubmitted: (_) => _amountFocus.requestFocus(),
            decoration: InputDecoration(
              labelText: 'Merchant',
              hintText: 'Swiggy, Amazon, a shop name…',
              prefixIcon: const Icon(Icons.storefront_outlined),
              helperText: _mcc != null ? 'From QR · MCC $_mcc' : null,
            ),
          ),
          optionsViewBuilder: (context, onSelected, options) => Align(
            alignment: Alignment.topLeft,
            child: Material(
              elevation: 4,
              borderRadius: BorderRadius.circular(12),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 280, maxWidth: 400),
                child: ListView(shrinkWrap: true, padding: EdgeInsets.zero, children: [
                  for (final m in options)
                    ListTile(
                      dense: true,
                      title: Text(m.name),
                      subtitle: Text('${app.meta!.shortLabel(m.category)} · ${channelLabel(m.channel)}'),
                      onTap: () => onSelected(m),
                    ),
                ]),
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _amount,
          focusNode: _amountFocus,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]'))],
          textInputAction: TextInputAction.done,
          onSubmitted: (_) => _ask(),
          style: t.textTheme.titleLarge,
          decoration: const InputDecoration(labelText: 'Amount', prefixText: '₹ ', prefixIcon: Icon(Icons.currency_rupee)),
        ),
        const SizedBox(height: 12),
        SegmentedButton<String?>(
          showSelectedIcon: false,
          segments: [for (final e in _channels.entries) ButtonSegment(value: e.key, label: Text(e.value))],
          selected: {_channel},
          onSelectionChanged: (s) => setState(() => _channel = s.first),
        ),
        const SizedBox(height: 16),
        Row(children: [
          Expanded(
            child: FilledButton.icon(
              style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
              onPressed: _busy ? null : _ask,
              icon: _busy
                  ? const SizedBox.square(dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.bolt),
              label: const Text('Find best card'),
            ),
          ),
          const SizedBox(width: 12),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 16)),
            onPressed: _scan,
            icon: const Icon(Icons.qr_code_scanner),
            label: const Text('Scan QR'),
          ),
        ]),
        if (_result != null) ...[
          const SizedBox(height: 24),
          _ResultView(result: _result!, request: _request!, confirmed: _confirmed, onConfirm: _confirm),
        ] else if (!_busy) ...[
          const SizedBox(height: 32),
          _Hint(heldCount: app.me?.holdings.length ?? 0),
        ],
      ]),
    );
  }
}

class _PayRequest {
  final String merchant;
  final int amountPaise;
  final String? channel, mcc;
  final String nonce;
  _PayRequest(this.merchant, this.amountPaise, this.channel, this.mcc, this.nonce);
}

class _Hint extends StatelessWidget {
  final int heldCount;
  const _Hint({required this.heldCount});
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Column(children: [
      Icon(Icons.credit_score_outlined, size: 40, color: t.colorScheme.outline),
      const SizedBox(height: 8),
      Text('Comparing your $heldCount ${plural(heldCount, 'card')} on caps, exclusions and minimums — in rupees.',
          textAlign: TextAlign.center, style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant)),
    ]);
  }
}

class _ResultView extends StatelessWidget {
  final PayResult result;
  final _PayRequest request;
  final Set<String> confirmed;
  final void Function(PayOption) onConfirm;
  const _ResultView({required this.result, required this.request, required this.confirmed, required this.onConfirm});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final meta = app.meta;
    final t = Theme.of(context);
    final s = t.colorScheme;
    final m = result.merchant;
    final best = result.best;
    final earns = best != null && best.rewardPaise > 0;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Wrap(spacing: 8, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
        Text(m.name, style: t.textTheme.titleMedium),
        Pill(meta?.shortLabel(m.category) ?? m.category),
        Pill(channelLabel(result.channel), color: s.surfaceContainerHighest, onColor: s.onSurface),
        if (m.isGuess)
          Pill('Category is a guess', icon: Icons.help_outline, color: s.tertiaryContainer, onColor: s.onTertiaryContainer),
      ]),
      const SizedBox(height: 12),
      Card(
        color: earns ? s.primaryContainer : s.surfaceContainerHigh,
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (best != null) ...[
              Text(earns ? 'PAY WITH' : 'NO CARD EARNS HERE',
                  style: t.textTheme.labelMedium?.copyWith(letterSpacing: 1.2, color: earns ? s.onPrimaryContainer : s.onSurfaceVariant)),
              const SizedBox(height: 6),
              Text(best.name, style: t.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700, color: earns ? s.onPrimaryContainer : null)),
              const SizedBox(height: 12),
              Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Text(rupees(best.rewardPaise),
                    style: t.textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w800, color: earns ? s.onPrimaryContainer : s.onSurfaceVariant)),
                const SizedBox(width: 8),
                Flexible(
                  child: Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text('back on ${rupees(request.amountPaise)}', style: t.textTheme.bodyMedium?.copyWith(color: earns ? s.onPrimaryContainer : null)),
                  ),
                ),
              ]),
              if (earns && result.marginPaise > 0)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Pill(
                    // With a spend profile the margin is over the rest of the month, not this payment alone.
                    result.best?.monthPaise != null
                        ? (result.runnerUp != null
                            ? '${rupees(result.marginPaise)} more this month than ${result.runnerUp!.name}'
                            : '${rupees(result.marginPaise)} more this month than any other card')
                        : (result.runnerUp != null
                            ? '${rupees(result.marginPaise)} more than ${result.runnerUp!.name}'
                            : '${rupees(result.marginPaise)} more than any other card'),
                    icon: Icons.trending_up,
                    color: s.surface,
                    onColor: moneyColor(context),
                  ),
                ),
            ],
            const SizedBox(height: 12),
            Text(result.text, style: t.textTheme.bodyMedium?.copyWith(color: earns ? s.onPrimaryContainer : null, height: 1.4)),
            if (best != null && best.notes.isNotEmpty) ...[
              const SizedBox(height: 10),
              for (final n in best.notes)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Icon(Icons.check, size: 16, color: earns ? s.onPrimaryContainer : s.onSurfaceVariant),
                    const SizedBox(width: 6),
                    Expanded(child: Text(n, style: t.textTheme.bodySmall?.copyWith(color: earns ? s.onPrimaryContainer : null))),
                  ]),
                ),
            ] else if (best != null && best.reasonCodes.isNotEmpty) ...[
              const SizedBox(height: 8),
              _ReasonChips(best.reasonCodes),
            ],
            if (best != null) ...[
              const SizedBox(height: 16),
              Row(children: [
                Expanded(
                  child: confirmed.contains(best.cardId)
                      ? FilledButton.tonalIcon(onPressed: null, icon: const Icon(Icons.check), label: const Text('Logged'))
                      : FilledButton.icon(
                          onPressed: () => onConfirm(best),
                          icon: const Icon(Icons.check_circle_outline),
                          label: const Text('I paid with this'),
                        ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  tooltip: 'Card details and sources',
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CardDetailScreen(cardId: best.cardId))),
                  icon: const Icon(Icons.info_outline),
                ),
              ]),
            ],
          ]),
        ),
      ),
      if (result.offers.isNotEmpty) ...[
        const SectionHeader('Bank offers here'),
        for (final o in result.offers) _OfferCard(o: o),
      ],
      if (result.ranked.length > 1 || best == null) ...[
        const SectionHeader('All your cards'),
        for (final (i, o) in result.ranked.indexed)
          Card(
            child: ListTile(
              contentPadding: const EdgeInsets.fromLTRB(16, 6, 8, 6),
              leading: CircleAvatar(
                radius: 14,
                backgroundColor: o.cardId == best?.cardId ? s.primary : s.surfaceContainerHighest,
                child: Text('${i + 1}', style: TextStyle(fontSize: 12, color: o.cardId == best?.cardId ? s.onPrimary : s.onSurface)),
              ),
              title: Text(o.name),
              subtitle: o.notes.isNotEmpty
                  ? Text(o.notes.join(' · '), style: t.textTheme.bodySmall)
                  : (o.reasonCodes.isEmpty
                      ? null
                      : Padding(padding: const EdgeInsets.only(top: 4), child: _ReasonChips(o.reasonCodes))),
              trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                Money(o.rewardPaise),
                PopupMenuButton<String>(
                  onSelected: (v) => v == 'paid'
                      ? onConfirm(o)
                      : Navigator.of(context).push(MaterialPageRoute(builder: (_) => CardDetailScreen(cardId: o.cardId))),
                  itemBuilder: (_) => [
                    PopupMenuItem(value: 'paid', enabled: !confirmed.contains(o.cardId), child: const Text('I paid with this')),
                    const PopupMenuItem(value: 'card', child: Text('Card details and sources')),
                  ],
                ),
              ]),
            ),
          ),
      ],
    ]);
  }
}

class _OfferCard extends StatelessWidget {
  final Offer o;
  const _OfferCard({required this.o});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = Theme.of(context);
    final s = t.colorScheme;
    final cards = o.cardIds.map(app.cardName).toList();
    final facts = <String>[
      if (o.minTxnPaise != null) 'min ${rupees(o.minTxnPaise!)}',
      if (o.validTo != null) 'till ${shortDate(o.validTo)}',
    ];
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(Icons.local_offer_outlined, size: 20, color: s.tertiary),
            const SizedBox(width: 10),
            Expanded(child: Text(o.title, style: t.textTheme.titleSmall)),
          ]),
          if (!o.isFact) const Padding(padding: EdgeInsets.only(top: 8), child: SpeculationPill()),
          const SizedBox(height: 6),
          if (cards.isNotEmpty) Text('With your ${cards.join(', ')}', style: t.textTheme.bodySmall),
          if (o.estSavingPaise != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Money(o.estSavingPaise!, suffix: ' off this payment (about)', style: t.textTheme.titleSmall),
            ),
          if (facts.isNotEmpty)
            Text(facts.join(' · '), style: t.textTheme.labelSmall?.copyWith(color: s.onSurfaceVariant)),
          if (o.source != null) SourceList(refs: [o.source!], label: o.isFact ? 'Source' : 'Reference'),
        ]),
      ),
    );
  }
}

class _ReasonChips extends StatelessWidget {
  final List<String> codes;
  const _ReasonChips(this.codes);
  @override
  Widget build(BuildContext context) {
    final meta = AppScope.of(context).meta;
    final s = Theme.of(context).colorScheme;
    return Wrap(spacing: 6, runSpacing: 4, children: [
      for (final c in codes)
        Pill(reasonLabel(c, meta: meta), icon: Icons.block, color: s.errorContainer.withValues(alpha: 0.7), onColor: s.onErrorContainer),
    ]);
  }
}
