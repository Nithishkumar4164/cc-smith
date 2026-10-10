import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
import '../capture.dart';
import '../state.dart';
import '../widgets.dart';
import 'capture.dart';

/// Find my cards via a SIMULATED credit-bureau fetch: phone + one-time code. The server
/// returns the demo code; it is shown and prefilled. Everything is labelled "Demo".
class BureauDiscoveryScreen extends StatefulWidget {
  const BureauDiscoveryScreen({super.key});
  @override
  State<BureauDiscoveryScreen> createState() => _BureauDiscoveryScreenState();
}

class _BureauDiscoveryScreenState extends State<BureauDiscoveryScreen> {
  final _phone = TextEditingController();
  final _otp = TextEditingController();
  bool _consent = false;
  bool _busy = false;
  String? _requestId, _demoOtp;

  @override
  void dispose() {
    _phone.dispose();
    _otp.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    if (!RegExp(r'^\d{10}$').hasMatch(_phone.text.trim())) {
      showError(context, const ApiException('Enter a 10-digit mobile number.'));
      return;
    }
    setState(() => _busy = true);
    try {
      final r = await AppScope.read(context).api.bureauStart(_phone.text.trim());
      setState(() {
        _requestId = '${r['request_id']}';
        _demoOtp = r['demo_otp']?.toString();
        _otp.text = _demoOtp ?? '';
      });
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    setState(() => _busy = true);
    try {
      final r = await AppScope.read(context).api.bureauVerify(_requestId!, _otp.text.trim());
      if (!mounted) return;
      await Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => CreditReportResultScreen(result: CreditReportResult.fromJson(r), demo: true)),
      );
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
      appBar: AppBar(title: const Text('Find my cards')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text('We look up the credit cards on your bureau record, so you don\'t have to search for each one.', style: t.textTheme.bodyMedium),
        const SizedBox(height: 16),
        TextField(
          controller: _phone,
          enabled: _requestId == null,
          keyboardType: TextInputType.phone,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(10)],
          decoration: const InputDecoration(labelText: 'Mobile number', prefixText: '+91 '),
        ),
        if (_requestId == null) ...[
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            value: _consent,
            onChanged: (v) => setState(() => _consent = v ?? false),
            controlAffinity: ListTileControlAffinity.leading,
            title: const Text('I consent to cc-smith fetching my credit-card accounts from the bureau for this purpose'),
          ),
          FilledButton(onPressed: _busy || !_consent ? null : _start, child: const Text('Send code')),
        ] else ...[
          const SizedBox(height: 12),
          Text('Code sent to +91 ${_phone.text}. Filled in automatically from the SMS.', style: t.textTheme.bodySmall),
          const SizedBox(height: 8),
          TextField(
            controller: _otp,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(6)],
            decoration: const InputDecoration(labelText: 'One-time code'),
          ),
          const SizedBox(height: 12),
          FilledButton(onPressed: _busy ? null : _verify, child: const Text('Verify and find my cards')),
        ],
      ]),
    );
  }
}
