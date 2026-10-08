import 'package:flutter/material.dart';

import '../api.dart';
import '../describe.dart';
import '../format.dart';
import '../models.dart';
import '../state.dart';
import '../widgets.dart';
import 'cards.dart';

class CardDetailScreen extends StatefulWidget {
  final String cardId;
  const CardDetailScreen({super.key, required this.cardId});
  @override
  State<CardDetailScreen> createState() => _CardDetailScreenState();
}

class _CardDetailScreenState extends State<CardDetailScreen> {
  late Future<CardDetail> _f;
  Future<AssessResult?>? _assess;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final app = AppScope.read(context);
    _f = app.api.card(widget.cardId);
    final held = app.me?.holdings.any((h) => h.cardId == widget.cardId) ?? false;
    _assess = held || (app.me?.spends.isEmpty ?? true) ? null : _fetchAssess(app.api);
  }

  Future<AssessResult?> _fetchAssess(Api api) async {
    try {
      return await api.assess(widget.cardId);
    } catch (_) {
      return null; // the gain line is a bonus; the facts still render
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Card')),
      body: FutureBuilder<CardDetail>(
        future: _f,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
          if (snap.hasError) return ErrorRetry(error: snap.error!, onRetry: () => setState(_load));
          return _DetailBody(d: snap.data!, assess: _assess, onReported: () => setState(_load));
        },
      ),
    );
  }
}

class _DetailBody extends StatelessWidget {
  final CardDetail d;
  final Future<AssessResult?>? assess;
  final VoidCallback onReported;
  const _DetailBody({required this.d, required this.assess, required this.onReported});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = Theme.of(context);
    final s = t.colorScheme;
    final c = d.summary;
    final desc = Describer(d.fields, meta: app.meta);
    final names = [...fieldOrder.where(d.fields.containsKey), ...(d.fields.keys.where((k) => !fieldOrder.contains(k)).toList()..sort())];
    return ListView(padding: const EdgeInsets.fromLTRB(16, 0, 16, 40), children: [
      Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          gradient: LinearGradient(colors: [s.primary, Color.lerp(s.primary, s.tertiary, 0.55)!], begin: Alignment.topLeft, end: Alignment.bottomRight),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(c.issuer.toUpperCase(), style: t.textTheme.labelMedium?.copyWith(color: s.onPrimary.withValues(alpha: 0.85), letterSpacing: 1.2)),
          const SizedBox(height: 6),
          Text(c.name, style: t.textTheme.headlineSmall?.copyWith(color: s.onPrimary, fontWeight: FontWeight.w700)),
          const SizedBox(height: 14),
          Wrap(spacing: 8, runSpacing: 6, children: [
            Pill(feeLabel(c.annualFeePaise), color: s.onPrimary.withValues(alpha: 0.18), onColor: s.onPrimary),
            if (c.currencyName != null) Pill(c.currencyName!, color: s.onPrimary.withValues(alpha: 0.18), onColor: s.onPrimary),
            Pill('Bank data as of ${shortDate(c.asOf)}', icon: Icons.verified_outlined, color: s.onPrimary.withValues(alpha: 0.18), onColor: s.onPrimary),
          ]),
        ]),
      ),
      if (assess != null)
        FutureBuilder<AssessResult?>(
          future: assess,
          builder: (context, snap) {
            final a = snap.data;
            if (a == null || !a.assessable) return const SizedBox.shrink();
            return Card(
              margin: const EdgeInsets.only(top: 12),
              child: ListTile(
                leading: Icon(a.gainPaise > 0 ? Icons.trending_up : Icons.trending_flat, color: a.gainPaise > 0 ? moneyColor(context) : s.onSurfaceVariant),
                title: Text(a.gainPaise > 0 ? 'Adds ${rupees(a.gainPaise)}/yr for you' : 'Would not add value on your spends (${rupees(a.gainPaise)}/yr)'),
                subtitle: const Text('Net of fees, alongside the cards you hold'),
              ),
            );
          },
        ),
      if (!c.assessable)
        Card(
          margin: const EdgeInsets.only(top: 12),
          child: ListTile(
            leading: const Icon(Icons.hourglass_empty),
            title: const Text('Not scored yet'),
            subtitle: const Text("We don't yet have enough facts from the bank's own pages to put this card in the rupee maths."),
          ),
        ),
      for (final f in names) _FieldSection(field: f, view: d.fields[f]!, desc: desc),
      if (d.speculation.isNotEmpty) ...[
        const SectionHeader('Reported, not confirmed by the bank'),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: s.tertiaryContainer.withValues(alpha: 0.45),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: s.tertiary.withValues(alpha: 0.5)),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('These come from news, forums, ads or user reports. They are never used in the rupee maths until the bank\'s own page confirms them.',
                style: t.textTheme.bodySmall),
            for (final sp in d.speculation) _SpeculationView(sp: sp, desc: desc),
          ]),
        ),
      ],
      if (d.changelog.isNotEmpty) ...[
        const SectionHeader('Changelog'),
        Card(
          child: Column(children: [for (final e in d.changelog.take(15)) _EventTile(e: e)]),
        ),
      ],
      const SizedBox(height: 16),
      OutlinedButton.icon(
        onPressed: () => _report(context),
        icon: const Icon(Icons.flag_outlined),
        label: const Text('Report wrong info'),
      ),
    ]);
  }

  Future<void> _report(BuildContext context) async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => _ReportSheet(card: d),
    );
    if (ok == true && context.mounted) {
      showInfo(context, 'Thanks. Shown as "reported, not confirmed by the bank" while we re-check the official page.');
      onReported();
    }
  }
}

class _FieldSection extends StatelessWidget {
  final String field;
  final FieldView view;
  final Describer desc;
  const _FieldSection({required this.field, required this.view, required this.desc});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final lines = desc.lines(field);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SectionHeader(fieldTitle(field), trailing: Text('as of ${shortDate(view.asOf)}', style: t.textTheme.labelSmall)),
      Card(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            for (final (i, l) in lines.indexed) ...[
              if (i > 0) const Divider(height: 16),
              Text(l.text, style: t.textTheme.bodyLarge),
              if (l.detail != null) Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text(l.detail!, style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
              ),
              SourceList(refs: l.sources.isNotEmpty ? l.sources : view.refs, asOf: view.asOf),
            ],
            if (lines.isEmpty) SourceList(refs: view.refs, asOf: view.asOf),
          ]),
        ),
      ),
    ]);
  }
}

class _SpeculationView extends StatelessWidget {
  final Speculation sp;
  final Describer desc;
  const _SpeculationView({required this.sp, required this.desc});
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final value = sp.value == null ? null : desc.describeValue(sp.field, sp.value).map((l) => l.text).join('; ');
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
          const SpeculationPill(),
          Text(fieldTitle(sp.field), style: t.textTheme.labelLarge),
        ]),
        const SizedBox(height: 4),
        if (value != null) Text(value, style: t.textTheme.bodyMedium),
        if (sp.reason != null) Text(sp.reason!, style: t.textTheme.bodySmall),
        Text('From ${_origin(sp.origin)} · reported ${shortDate(sp.openedAt)} · expires ${shortDate(sp.expiresAt)} unless confirmed',
            style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
        SourceList(refs: sp.refs, label: 'References'),
      ]),
    );
  }

  String _origin(String o) => switch (o) {
        'user_report' => 'a user report',
        'ai_mode' => 'AI search',
        'news' => 'news',
        'range_check' => 'an official page that failed checks',
        _ => o.replaceAll('_', ' '),
      };
}

class _EventTile extends StatelessWidget {
  final ChangeEvent e;
  const _EventTile({required this.e});
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final s = t.colorScheme;
    return ListTile(
      dense: true,
      leading: Icon(_icon(e.eventType), size: 20, color: e.tier == 'speculation' ? s.tertiary : s.primary),
      title: Text('${fieldTitle(e.field ?? 'card')} ${e.eventType.replaceAll('_', ' ')}'),
      subtitle: Text('${shortDate(e.at)}${e.tier != null ? ' · ${e.tier == 'fact' ? 'from bank page' : 'reported, not confirmed'}' : ''}'),
      trailing: e.largeChange ? Pill('Big change', color: s.errorContainer, onColor: s.onErrorContainer) : null,
    );
  }

  IconData _icon(String type) => switch (type) {
        'published' => Icons.check_circle_outline,
        'promoted' => Icons.upgrade,
        'speculation_added' => Icons.help_outline,
        'contradicted' || 'expired' => Icons.cancel_outlined,
        'demoted' || 'rolled_back' => Icons.undo,
        _ => Icons.history,
      };
}

class _ReportSheet extends StatefulWidget {
  final CardDetail card;
  const _ReportSheet({required this.card});
  @override
  State<_ReportSheet> createState() => _ReportSheetState();
}

class _ReportSheetState extends State<_ReportSheet> {
  late String _field;
  final _msg = TextEditingController();
  final _url = TextEditingController();
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _field = widget.card.fields.keys.isNotEmpty ? widget.card.fields.keys.first : 'other';
  }

  @override
  void dispose() {
    _msg.dispose();
    _url.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    if (_msg.text.trim().length < 3) {
      showError(context, const ApiException('Tell us what looks wrong.'));
      return;
    }
    setState(() => _busy = true);
    try {
      final app = AppScope.read(context);
      await app.ensureUser();
      await app.api.report(widget.card.summary.id, field: _field, message: _msg.text.trim(), evidenceUrl: _url.text.trim());
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final fields = {...widget.card.fields.keys, ...fieldOrder, 'other'}.toList();
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 0, 16, MediaQuery.of(context).viewInsets.bottom + 16),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text('Report wrong info', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 4),
        Text(widget.card.summary.name, style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          initialValue: _field,
          decoration: const InputDecoration(labelText: 'What is wrong'),
          items: [for (final f in fields) DropdownMenuItem(value: f, child: Text(f == 'other' ? 'Something else' : fieldTitle(f)))],
          onChanged: (v) => setState(() => _field = v ?? _field),
        ),
        const SizedBox(height: 12),
        TextField(controller: _msg, maxLines: 3, maxLength: 2000, decoration: const InputDecoration(labelText: 'What did you see?')),
        TextField(controller: _url, keyboardType: TextInputType.url, decoration: const InputDecoration(labelText: 'Link (optional)')),
        const SizedBox(height: 16),
        FilledButton(onPressed: _busy ? null : _send, child: const Text('Send report')),
      ]),
    );
  }
}
