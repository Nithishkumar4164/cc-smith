import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../upi.dart';

/// Scans a UPI QR and pops with the parsed [UpiPayment]. A paste box covers
/// emulators without a camera and printed `upi://` links.
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});
  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final _controller = MobileScannerController(formats: const [BarcodeFormat.qrCode]);
  final _paste = TextEditingController();
  bool _done = false;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    _paste.dispose();
    super.dispose();
  }

  void _handle(String raw) {
    if (_done) return;
    final upi = parseUpi(raw);
    if (upi == null) {
      setState(() => _error = 'That is not a UPI payment QR.');
      return;
    }
    _done = true;
    Navigator.of(context).pop(upi);
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Scan UPI QR')),
      body: Column(children: [
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: Stack(fit: StackFit.expand, children: [
              MobileScanner(
                controller: _controller,
                onDetect: (capture) {
                  for (final b in capture.barcodes) {
                    final v = b.rawValue;
                    if (v != null) {
                      _handle(v);
                      break;
                    }
                  }
                },
                errorBuilder: (context, error) => Container(
                  color: t.colorScheme.surfaceContainerHighest,
                  alignment: Alignment.center,
                  padding: const EdgeInsets.all(24),
                  child: Text('Camera unavailable (${error.errorCode.name}). Paste the UPI link below instead.',
                      textAlign: TextAlign.center),
                ),
              ),
              IgnorePointer(
                child: Center(
                  child: Container(
                    width: 240,
                    height: 240,
                    decoration: BoxDecoration(
                      border: Border.all(color: t.colorScheme.primaryContainer, width: 3),
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                ),
              ),
            ]),
          ),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              if (_error != null) Text(_error!, style: TextStyle(color: t.colorScheme.error)),
              const SizedBox(height: 8),
              TextField(
                controller: _paste,
                decoration: InputDecoration(
                  hintText: 'or paste upi://pay?pa=…',
                  suffixIcon: IconButton(icon: const Icon(Icons.arrow_forward), onPressed: () => _handle(_paste.text)),
                ),
                onSubmitted: _handle,
              ),
            ]),
          ),
        ),
      ]),
    );
  }
}
