import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
import '../capture.dart';
import '../format.dart';
import '../models.dart';
import '../state.dart';
import '../widgets.dart';

/// Picks one PDF and returns (bytes, name), or null if cancelled.
typedef PdfPicker = Future<(List<int>, String)?> Function();

Future<(List<int>, String)?> pickPdf() async {
  final files = await FilePicker.pickFiles(type: FileType.custom, allowedExtensions: ['pdf']);
  final f = files.firstOrNull;
  if (f == null) return null;
  return ((await f.readAsBytes()).toList(), f.name);
}

Future<String?> askPassword(BuildContext context, String title) {
  final ctrl = TextEditingController();
  return showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Banks usually lock statements with a password (often part of your name and date of birth). '
            'It is used once to open the file and not stored.',
          ),
          const SizedBox(height: 12),
          TextField(
            controller: ctrl,
            obscureText: true,
            autofocus: true,
            decoration: const InputDecoration(labelText: 'PDF password'),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
        FilledButton(onPressed: () => Navigator.pop(ctx, ctrl.text), child: const Text('Open')),
      ],
    ),
  );
}

/// Profile › Data sources: statements, credit report, phone notifications, Gmail.
class DataSourcesScreen extends StatefulWidget {
  final PdfPicker picker;
  const DataSourcesScreen({super.key, this.picker = pickPdf});
  @override
  State<DataSourcesScreen> createState() => _DataSourcesScreenState();
}

class _DataSourcesScreenState extends State<DataSourcesScreen> {
  Future<Json>? _status;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _status = AppScope.read(context).api.captureStatus();
  }

  void _reload() => setState(() => _status = AppScope.read(context).api.captureStatus());

  Future<void> _statement() async {
    final app = AppScope.read(context);
    final file = await widget.picker();
    if (file == null || !mounted) return;
    String? cardId;
    final held = app.me?.holdings ?? const <Holding>[];
    if (held.length > 1) {
      cardId = await showDialog<String>(
        context: context,
        builder: (ctx) => SimpleDialog(
          title: const Text('Which card is this statement for?'),
          children: [
            SimpleDialogOption(onPressed: () => Navigator.pop(ctx, ''), child: const Text('Work it out from the statement')),
            for (final h in held)
              SimpleDialogOption(onPressed: () => Navigator.pop(ctx, h.cardId), child: Text(app.cardName(h.cardId))),
          ],
        ),
      );
      if (cardId == null) return;
      if (cardId.isEmpty) cardId = null;
    } else if (held.length == 1) {
      cardId = held.first.cardId;
    }
    String? password;
    setState(() => _busy = true);
    try {
      while (true) {
        try {
          setState(() => _busy = true);
          final Json res;
          try {
            res = await app.api.uploadStatement(file.$1, file.$2, password: password, cardId: cardId);
          } finally {
            if (mounted) setState(() => _busy = false);
          }
          app.bumpData();
          await app.refreshUserData();
          if (!mounted) return;
          await Navigator.of(
            context,
          ).push(MaterialPageRoute(builder: (_) => StatementResultScreen(result: StatementResult.fromJson(res))));
          _reload();
          return;
        } on ApiException catch (e) {
          if (e.code != 'password_required' && e.code != 'wrong_password' && e.code != 'bad_password') rethrow;
          if (!mounted) return;
          password = await askPassword(context, password == null ? 'Statement password' : 'Wrong password, try again');
          if (password == null) return;
        }
      }
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _creditReport() async {
    final ok = await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => const CreditReportConsentScreen()));
    if (ok != true || !mounted) return;
    final app = AppScope.read(context);
    final file = await widget.picker();
    if (file == null || !mounted) return;
    String? password;
    setState(() => _busy = true);
    try {
      while (true) {
        try {
          setState(() => _busy = true);
          final Json res;
          try {
            res = await app.api.uploadCreditReport(file.$1, file.$2, password: password);
          } finally {
            if (mounted) setState(() => _busy = false);
          }
          if (!mounted) return;
          await Navigator.of(
            context,
          ).push(MaterialPageRoute(builder: (_) => CreditReportResultScreen(result: CreditReportResult.fromJson(res))));
          _reload();
          return;
        } on ApiException catch (e) {
          if (e.code != 'password_required' && e.code != 'wrong_password' && e.code != 'bad_password') rethrow;
          if (!mounted) return;
          password = await askPassword(context, password == null ? 'Report password' : 'Wrong password, try again');
          if (password == null) return;
        }
      }
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Data sources'),
        bottom: _busy ? const PreferredSize(preferredSize: Size.fromHeight(4), child: LinearProgressIndicator()) : null,
      ),
      body: FutureBuilder<Json>(
        future: _status,
        builder: (context, snap) {
          final st = snap.data ?? const <String, dynamic>{};
          Map src(String k) => (st[k] as Map?) ?? const {};
          String last(String k) {
            final at = src(k)['last_sync_at'];
            return at == null ? 'Never' : 'Last ${shortDate('$at')}';
          }

          final credit = (src('credit_report')['stored'] as Map?);
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
            children: [
              Text(
                'Everything below is optional. Files are read once and dropped; only the figures shown to you are kept.',
                style: t.textTheme.bodySmall,
              ),
              const SectionHeader('Card statement (PDF)'),
              Card(
                child: ListTile(
                  leading: const Icon(Icons.picture_as_pdf_outlined),
                  title: const Text('Upload a statement'),
                  subtitle: Text('Sets the outstanding, limit and statement day, and logs the purchases. ${last('statement')}'),
                  trailing: const Icon(Icons.upload_file),
                  onTap: _busy ? null : _statement,
                ),
              ),
              const SectionHeader('Credit report (PDF)'),
              Card(
                child: ListTile(
                  leading: const Icon(Icons.speed),
                  title: const Text('Upload a credit report'),
                  subtitle: Text(
                    credit == null
                        ? 'CIBIL / Experian / CRIF / Equifax: finds your cards and limits.'
                        : 'Score ${credit['score'] ?? '—'} (${'${credit['bureau'] ?? ''}'.toUpperCase()}), report of ${shortDate('${credit['report_date']}')}',
                  ),
                  trailing: const Icon(Icons.upload_file),
                  onTap: _busy ? null : _creditReport,
                ),
              ),
              const SectionHeader('Phone notifications (Android)'),
              NotificationSourceCard(
                lastSync: last('notification'),
                counts: Map<String, dynamic>.from(src('notification')['counts'] as Map? ?? {}),
              ),
              const SectionHeader('Gmail'),
              GmailCard(status: Map<String, dynamic>.from(src('gmail')), onChanged: _reload),
            ],
          );
        },
      ),
    );
  }
}

class StatementResultScreen extends StatelessWidget {
  final StatementResult result;
  const StatementResultScreen({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = Theme.of(context);
    final s = t.colorScheme;
    final r = result;
    final credit = r.cardId == null ? null : app.creditByCard[r.cardId];
    Widget row(String k, String? v) => v == null
        ? const SizedBox.shrink()
        : Padding(
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: Row(
              children: [
                Expanded(child: Text(k, style: t.textTheme.bodyMedium)),
                Text(v, style: t.textTheme.titleSmall),
              ],
            ),
          );
    String? money(int? p) => p == null ? null : rupees(p);
    return Scaffold(
      appBar: AppBar(title: const Text('Confirm what we read')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
        children: [
          Card(
            color: r.matched ? s.primaryContainer : s.errorContainer,
            child: ListTile(
              leading: Icon(r.matched ? Icons.check_circle : Icons.help_outline),
              title: Text(r.matched ? 'Applied to ${app.cardName(r.cardId!)}' : 'Not matched to a card you hold'),
              subtitle: Text(
                r.matched
                    ? 'Outstanding, limit and statement day updated. Check the figures below against your PDF.'
                    : 'Add the card in Profile, or upload again and pick the card. (${r.unmatchedReason ?? 'no match'})',
              ),
            ),
          ),
          const SectionHeader('From the statement'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  row('Card ending', r.last4),
                  row('Statement date', r.statementDate == null ? null : shortDate(r.statementDate)),
                  row('Payment due', r.dueDate == null ? null : shortDate(r.dueDate)),
                  row('Total due', money(r.totalDuePaise)),
                  row('Minimum due', money(r.minDuePaise)),
                  row('Credit limit', money(r.creditLimitPaise)),
                  row('Available credit', money(r.availableCreditPaise)),
                  row('Payments and credits', money(r.paymentsPaise)),
                ],
              ),
            ),
          ),
          if (credit != null) ...[
            const SectionHeader('Your credit now'),
            Card(
              child: ListTile(
                leading: const Icon(Icons.account_balance_wallet_outlined),
                title: Text(
                  credit.availablePaise == null
                      ? 'Owes ${rupees(credit.outstandingPaise)}'
                      : '${rupees(credit.availablePaise!)} available',
                ),
                subtitle: Text(
                  'Owes ${rupees(credit.outstandingPaise)}${credit.limitPaise != null ? ' of ${rupees(credit.limitPaise!)}' : ''}'
                  '${credit.utilisationBp != null ? ' · ${credit.utilisationBp! ~/ 100}% used' : ''}',
                ),
              ),
            ),
          ],
          if (r.lineOutcomes.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                r.lineOutcomes.entries.map((e) => '${e.value} ${e.key.replaceAll('_', ' ')}').join(' · '),
                style: t.textTheme.labelMedium,
              ),
            ),
          if (r.lines.isNotEmpty) ...[
            SectionHeader('Transactions (${r.lines.length})'),
            Card(
              child: Column(
                children: [
                  for (final l in r.lines)
                    ListTile(
                      dense: true,
                      title: Text(l.description ?? '—'),
                      subtitle: Text('${shortDate(l.date)} · ${(l.kind ?? '').replaceAll('_', ' ')}'),
                      trailing: Text(
                        '${l.direction == 'credit' ? '+' : ''}${rupees(l.amountPaise)}',
                        style: t.textTheme.labelLarge?.copyWith(color: l.direction == 'credit' ? moneyColor(context) : null),
                      ),
                    ),
                ],
              ),
            ),
          ],
          for (final w in r.warnings)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text('Note: $w', style: t.textTheme.bodySmall),
            ),
          const SizedBox(height: 16),
          FilledButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Looks right')),
        ],
      ),
    );
  }
}

class CreditReportConsentScreen extends StatefulWidget {
  const CreditReportConsentScreen({super.key});
  @override
  State<CreditReportConsentScreen> createState() => _CreditReportConsentScreenState();
}

class _CreditReportConsentScreenState extends State<CreditReportConsentScreen> {
  bool _agree = false;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    Widget point(IconData i, String s) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(i, size: 20),
          const SizedBox(width: 12),
          Expanded(child: Text(s)),
        ],
      ),
    );
    return Scaffold(
      appBar: AppBar(title: const Text('Your consent')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text('Analyse my credit report', style: t.textTheme.headlineSmall),
          const SizedBox(height: 12),
          point(
            Icons.search,
            'We read the PDF once to find your score, bureau, report date, credit-card accounts (lender, limit, balance, '
            'payment history) and recent enquiries.',
          ),
          point(
            Icons.delete_outline,
            'The file and its password are discarded as soon as it is read. We keep only the score, bureau, report '
            'date and counts of cards and enquiries (Digital Personal Data Protection Act, 2023: purpose-limited, minimum data).',
          ),
          point(
            Icons.credit_card,
            'Accounts are shown to you so you can add those cards and limits. Nothing is shared with any bank or lender.',
          ),
          point(Icons.undo, 'You can withdraw consent; ask us to delete the stored figures at any time.'),
          const SizedBox(height: 12),
          CheckboxListTile(
            value: _agree,
            onChanged: (v) => setState(() => _agree = v ?? false),
            title: const Text('I consent to cc-smith analysing my credit report for this purpose'),
            controlAffinity: ListTileControlAffinity.leading,
          ),
          const SizedBox(height: 12),
          FilledButton(onPressed: _agree ? () => Navigator.pop(context, true) : null, child: const Text('Choose the PDF')),
        ],
      ),
    );
  }
}

class CreditReportResultScreen extends StatefulWidget {
  final CreditReportResult result;

  /// Simulated bureau fetch: labelled "Demo" so nobody mistakes it for their real report.
  final bool demo;
  const CreditReportResultScreen({super.key, required this.result, this.demo = false});
  @override
  State<CreditReportResultScreen> createState() => _CreditReportResultScreenState();
}

/// Annual fee from the catalogue, GST included (the user can mark LTF/FYF or a custom fee later).
String _feeText(CardSummary? c) {
  final f = c?.annualFeePaise;
  if (f == null) return 'fee as per bank';
  return f == 0 ? 'no annual fee' : '${rupees(f * 118 ~/ 100)}/yr fee';
}

/// CRED-style card addition: the full number (checked on the phone: valid, ends in the
/// bureau's last 4), then a ₹1 check. Only the first 6 and last 4 digits go to the server.
class AddCardScreen extends StatefulWidget {
  final String lender, last4;
  const AddCardScreen({super.key, required this.lender, required this.last4});
  @override
  State<AddCardScreen> createState() => _AddCardScreenState();
}

class _AddCardScreenState extends State<AddCardScreen> {
  final _number = TextEditingController();
  String? _error;
  bool _busy = false;
  ({String id, String name})? _done;

  @override
  void dispose() {
    _number.dispose();
    super.dispose();
  }

  static bool _luhn(String n) {
    var sum = 0;
    for (var i = 0; i < n.length; i++) {
      var d = int.parse(n[n.length - 1 - i]) * (i.isOdd ? 2 : 1);
      sum += d > 9 ? d - 9 : d;
    }
    return sum % 10 == 0;
  }

  Future<void> _verify() async {
    final n = _number.text.replaceAll(RegExp(r'\D'), '');
    final err = n.length < 15 || n.length > 16
        ? 'Enter the full card number.'
        : !n.endsWith(widget.last4)
            ? 'This number doesn\'t end in ${widget.last4}.'
            : !_luhn(n)
                ? 'Check the number: it isn\'t a valid card number.'
                : null;
    setState(() => _error = err);
    if (err != null) return;
    setState(() => _busy = true);
    try {
      final r = await AppScope.read(context).api.cardCheck(widget.lender, widget.last4, n.substring(0, 6));
      // The ₹1 deposit takes a moment at a real bank.
      await Future<void>.delayed(const Duration(milliseconds: 1200));
      if (mounted) setState(() => _done = (id: '${r['card_id']}', name: '${r['card_name']}'));
    } catch (e) {
      if (mounted) setState(() => _error = e is ApiException ? e.message : '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final s = t.colorScheme;
    final done = _done;
    return Scaffold(
      appBar: AppBar(title: Text(RegExp(r'card$', caseSensitive: false).hasMatch(widget.lender) ? 'Add your ${widget.lender}' : 'Add your ${widget.lender} card')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (done == null) ...[
          Text('Enter the full number on your card ending ${widget.last4}. We never ask for the CVV or PIN.', style: t.textTheme.bodyMedium),
          const SizedBox(height: 16),
          TextField(
            controller: _number,
            enabled: !_busy,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(16), _CardNumberFormatter()],
            decoration: InputDecoration(
              labelText: 'Card number',
              hintText: 'XXXX XXXX XXXX ${widget.last4}',
              errorText: _error,
              prefixIcon: const Icon(Icons.credit_card),
            ),
          ),
          const SizedBox(height: 16),
          if (_busy)
            Row(children: [
              const SizedBox.square(dimension: 18, child: CircularProgressIndicator(strokeWidth: 2)),
              const SizedBox(width: 12),
              Expanded(child: Text('Verifying with ₹1…', style: t.textTheme.bodyMedium)),
            ])
          else
            FilledButton(onPressed: _verify, child: const Text('Verify card')),
        ] else ...[
          const SizedBox(height: 24),
          Icon(Icons.verified, size: 56, color: s.primary),
          const SizedBox(height: 12),
          Text(done.name, style: t.textTheme.titleLarge, textAlign: TextAlign.center),
          const SizedBox(height: 6),
          Text('Verified. We sent ₹1 to your card ending ${widget.last4} to confirm it\'s yours.',
              style: t.textTheme.bodyMedium, textAlign: TextAlign.center),
          const SizedBox(height: 24),
          FilledButton(onPressed: () => Navigator.pop(context, done), child: const Text('Done')),
        ],
      ]),
    );
  }
}

/// Groups digits in fours as the user types.
class _CardNumberFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(TextEditingValue oldValue, TextEditingValue newValue) {
    final d = newValue.text.replaceAll(' ', '');
    final b = StringBuffer();
    for (var i = 0; i < d.length; i++) {
      if (i > 0 && i % 4 == 0) b.write(' ');
      b.write(d[i]);
    }
    final text = b.toString();
    return TextEditingValue(text: text, selection: TextSelection.collapsed(offset: text.length));
  }
}

class _CreditReportResultScreenState extends State<CreditReportResultScreen> {
  /// account index -> the card its number identified (for accounts not yet in "your cards").
  final _verified = <int, ({String id, String name})>{};

  Future<void> _addCard(int i, ReportAccount a) async {
    final r = await Navigator.of(context).push<({String id, String name})>(
      MaterialPageRoute(builder: (_) => AddCardScreen(lender: a.lender ?? '', last4: a.last4 ?? '')),
    );
    if (r != null) setState(() => _verified[i] = r);
  }
  bool _busy = false;

  Future<void> _save({required bool addCards}) async {
    final app = AppScope.read(context);
    final held = {for (final h in app.me?.holdings ?? const <Holding>[]) h.cardId: h};
    var changed = 0;
    for (final (i, a) in widget.result.accounts.indexed) {
      final id = a.heldCardId ?? (addCards && a.isOpen ? (a.cardId ?? _verified[i]?.id) : null);
      if (id == null) continue;
      final h = held[id];
      if (h == null) {
        // The annual fee falls in the month the card was opened; the fee itself follows the catalogue.
        held[id] = Holding(
          cardId: id,
          creditLimitPaise: a.creditLimitPaise,
          last4: a.last4,
          renewalMonth: DateTime.tryParse(a.opened ?? '')?.month,
          balancePaise: a.currentBalancePaise,
        );
        changed++;
      } else if (!addCards && h.poolId == null && a.creditLimitPaise != null && h.creditLimitPaise != a.creditLimitPaise) {
        held[id] = h.copyWith(creditLimitPaise: a.creditLimitPaise);
        changed++;
      }
    }
    if (changed == 0) {
      showInfo(context, addCards ? 'Add each card with its number first.' : 'Your limits already match the report.');
      return;
    }
    setState(() => _busy = true);
    try {
      await app.saveHoldings(held.values.toList());
      if (mounted) {
        showInfo(context, addCards ? 'Added $changed ${plural(changed, 'card')}' : 'Updated $changed ${plural(changed, 'limit')}');
      }
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
    final s = t.colorScheme;
    final r = widget.result;
    final heldIds = {for (final h in app.me?.holdings ?? const <Holding>[]) h.cardId};
    return Scaffold(
      appBar: AppBar(title: Text(widget.demo ? 'Your cards' : 'Credit report')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
        children: [
          Card(
            color: s.primaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${(r.bureau ?? 'Credit').toUpperCase()} SCORE',
                    style: t.textTheme.labelMedium?.copyWith(color: s.onPrimaryContainer, letterSpacing: 1.2),
                  ),
                  Text(
                    '${r.score ?? '—'}',
                    style: t.textTheme.displaySmall?.copyWith(color: s.onPrimaryContainer, fontWeight: FontWeight.w800),
                  ),
                  Text(
                    'Report of ${shortDate(r.reportDate)} · ${r.enquiries6m} ${plural(r.enquiries6m, 'enquiry', 'enquiries')} in 6 months',
                    style: t.textTheme.bodySmall?.copyWith(color: s.onPrimaryContainer),
                  ),
                ],
              ),
            ),
          ),
          SectionHeader('Credit cards in the report (${r.accounts.length})'),
          for (final (i, a) in r.accounts.indexed)
            Card(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            _verified[i]?.name ?? a.cardName ?? '${a.lender ?? 'Lender'} ••${a.last4 ?? '••••'}',
                            style: t.textTheme.titleSmall,
                          ),
                        ),
                        if (!a.isOpen) Pill('Closed', color: s.surfaceContainerHighest, onColor: s.onSurfaceVariant),
                      ],
                    ),
                    Text(
                      [
                        if (_verified[i] != null || a.cardName != null)
                          '${a.lender ?? 'Card'} ••${a.last4 ?? '••••'}'
                        else
                          a.accountType ?? 'Credit card',
                        if (a.opened != null) 'since ${monthYear(a.opened!)}',
                        if (_verified[i] != null || a.cardId != null) _feeText(app.cardsById[_verified[i]?.id ?? a.cardId]),
                      ].join(' · '),
                      style: t.textTheme.bodySmall,
                    ),
                    Text(
                      [
                        if (a.creditLimitPaise != null) 'Limit ${rupees(a.creditLimitPaise!)}',
                        if (a.currentBalancePaise != null) 'balance ${rupees(a.currentBalancePaise!)}',
                        if (a.maxDpdDays != null) a.maxDpdDays == 0 ? 'always paid on time' : 'up to ${a.maxDpdDays} days late',
                      ].join(' · '),
                      style: t.textTheme.bodySmall,
                    ),
                    const SizedBox(height: 6),
                    if (a.heldCardId != null && heldIds.contains(a.heldCardId))
                      Pill('In your cards: ${app.cardName(a.heldCardId!)}', icon: Icons.check)
                    else if (_verified[i] != null)
                      Pill('Verified with ₹1', icon: Icons.verified)
                    else if (a.isOpen && a.cardId == null)
                      FilledButton.tonalIcon(
                        onPressed: () => _addCard(i, a),
                        icon: const Icon(Icons.add_card, size: 18),
                        label: const Text('Add card'),
                      ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.icon(
                onPressed: _busy ? null : () => _save(addCards: true),
                icon: const Icon(Icons.add_card),
                label: const Text('Add these cards'),
              ),
              OutlinedButton.icon(
                onPressed: _busy ? null : () => _save(addCards: false),
                icon: const Icon(Icons.sync),
                label: const Text('Use these limits'),
              ),
            ],
          ),
          if (r.enquiries.isNotEmpty) ...[
            SectionHeader('Enquiries (${r.enquiries.length})'),
            Card(
              child: Column(
                children: [
                  for (final e in r.enquiries)
                    ListTile(
                      dense: true,
                      title: Text(e.lender ?? 'Lender'),
                      subtitle: Text('${shortDate(e.date)} · ${e.purpose ?? ''}'),
                    ),
                ],
              ),
            ),
            Text(
              'Banks look at hard enquiries in the last 6 months; several close together can lower approval odds.',
              style: t.textTheme.bodySmall,
            ),
          ],
          for (final w in r.warnings)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text('Note: $w', style: t.textTheme.bodySmall),
            ),
        ],
      ),
    );
  }
}

/// Connect Gmail (installed-app flow: open the consent page, paste the code), sync, status.
class GmailCard extends StatefulWidget {
  final Map<String, dynamic> status;
  final VoidCallback onChanged;
  const GmailCard({super.key, required this.status, required this.onChanged});
  @override
  State<GmailCard> createState() => _GmailCardState();
}

class _GmailCardState extends State<GmailCard> {
  bool _busy = false;
  String? _message;

  Future<void> _run(Future<void> Function() f) async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      await f();
      widget.onChanged();
    } on ApiException catch (e) {
      setState(() => _message = e.status == 503 ? 'Gmail is not available yet: ${e.message}' : e.message);
    } catch (e) {
      setState(() => _message = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _connect() => _run(() async {
    final api = AppScope.read(context).api;
    final auth = await api.gmailAuthUrl();
    if (!mounted) return;
    await openUrl(context, '${auth['url']}');
    if (!mounted) return;
    final ctrl = TextEditingController();
    final code = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Paste the code from Google'),
        content: TextField(
          controller: ctrl,
          decoration: const InputDecoration(labelText: 'Authorisation code'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, ctrl.text.trim()), child: const Text('Connect')),
        ],
      ),
    );
    if (code == null || code.isEmpty) return;
    await api.gmailCallback(code, state: auth['state']?.toString());
    setState(() => _message = 'Gmail connected. Tap Sync now to read card alerts.');
  });

  Future<void> _sync() => _run(() async {
    final app = AppScope.read(context);
    final res = await app.api.gmailSync();
    app.bumpData();
    setState(
      () => _message =
          'Synced: ${res.entries.where((e) => e.value is num).map((e) => '${e.value} ${e.key.replaceAll('_', ' ')}').join(', ')}',
    );
  });

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final connected = widget.status['connected'] == true;
    final at = widget.status['last_sync_at'];
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              connected
                  ? 'Connected${at != null ? ' · last sync ${shortDate('$at')}' : ''}'
                  : 'Reads bank alert emails (read-only) to log card spends.',
              style: t.textTheme.bodyMedium,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                if (!connected)
                  FilledButton.icon(
                    onPressed: _busy ? null : _connect,
                    icon: const Icon(Icons.mail_outline),
                    label: const Text('Connect Gmail'),
                  ),
                if (connected)
                  FilledButton.icon(onPressed: _busy ? null : _sync, icon: const Icon(Icons.sync), label: const Text('Sync now')),
                if (connected)
                  TextButton(
                    onPressed: _busy ? null : () => _run(() => AppScope.read(context).api.gmailDisconnect()),
                    child: const Text('Disconnect'),
                  ),
              ],
            ),
            if (_message != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_message!, style: t.textTheme.bodySmall),
              ),
          ],
        ),
      ),
    );
  }
}

/// Toggle for reading bank / UPI app notifications on this phone (Android only).
class NotificationSourceCard extends StatefulWidget {
  final String lastSync;
  final Map<String, dynamic> counts;
  const NotificationSourceCard({super.key, required this.lastSync, required this.counts});
  @override
  State<NotificationSourceCard> createState() => _NotificationSourceCardState();
}

class _NotificationSourceCardState extends State<NotificationSourceCard> {
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = Theme.of(context);
    final capture = app.notificationCapture;
    final supported = !kIsWeb && defaultTargetPlatform == TargetPlatform.android;
    return Card(
      child: Column(
        children: [
          SwitchListTile(
            value: capture.enabled,
            onChanged: !supported
                ? null
                : (v) async {
                    if (v) {
                      final ok = await showDialog<bool>(context: context, builder: (_) => const NotificationDisclosure());
                      if (ok != true) return;
                      await capture.enable();
                      if (!await capture.hasAccess()) await capture.openAccessSettings();
                    } else {
                      await capture.disable();
                    }
                    if (mounted) setState(() {});
                  },
            title: const Text('Read bank and UPI notifications'),
            subtitle: Text(
              supported
                  ? 'Logs card spends from HDFC, ICICI, SBI Card, Axis, HSBC, Kotak, IDFC, YES/Kiwi, AU, GPay, PhonePe and Paytm alerts. ${widget.lastSync}'
                  : 'Available in the Android app.',
            ),
          ),
          if (capture.enabled)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      '${capture.sent} sent this session${widget.counts.isNotEmpty ? ' · ${widget.counts.entries.map((e) => '${e.value} ${e.key}').join(', ')}' : ''}',
                      style: t.textTheme.labelSmall,
                    ),
                  ),
                  TextButton(onPressed: capture.openAccessSettings, child: const Text('Notification access')),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

/// Prominent disclosure (Play policy) before asking for notification access.
class NotificationDisclosure extends StatelessWidget {
  const NotificationDisclosure({super.key});
  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Read payment notifications?'),
    content: const Text(
      'cc-smith will read notifications from your bank and UPI apps only, to log card spends and track caps and credit.\n\n'
      'The text is read on this phone. Only the amount, merchant, date, card ending and bank are sent to cc-smith — never '
      'the notification text, and never full card numbers. Other apps\' notifications are ignored.\n\n'
      'Next, Android will ask you to allow notification access for cc-smith. You can turn this off any time here or in Settings.',
    ),
    actions: [
      TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Not now')),
      FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Continue')),
    ],
  );
}
