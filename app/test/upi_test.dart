import 'package:app/upi.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('full merchant QR with name, MCC and amount', () {
    final u = parseUpi('upi://pay?pa=swiggy.food@icici&pn=Swiggy%20Limited&mc=5812&am=349.50&cu=INR&tr=ABC123')!;
    expect(u.payeeAddress, 'swiggy.food@icici');
    expect(u.payeeName, 'Swiggy Limited');
    expect(u.merchant, 'Swiggy Limited');
    expect(u.mcc, '5812');
    expect(u.amountPaise, 34950);
  });

  test('plus-encoded spaces, uppercase keys, no amount', () {
    final u = parseUpi('UPI://pay?PA=sharmakirana@okaxis&PN=Sharma+Kirana+Store&MC=5411')!;
    expect(u.merchant, 'Sharma Kirana Store');
    expect(u.mcc, '5411');
    expect(u.amountPaise, isNull);
  });

  test('personal QR: mc 0000 is ignored and VPA handle is the merchant fallback', () {
    final u = parseUpi('upi://pay?pa=ravi.k@ybl&mc=0000&am=0')!;
    expect(u.mcc, isNull);
    expect(u.amountPaise, isNull);
    expect(u.payeeName, isNull);
    expect(u.merchant, 'ravi.k');
  });

  test('raw spaces in pn are tolerated', () {
    final u = parseUpi('upi://pay?pa=a@b&pn=Cafe Coffee Day&am=120')!;
    expect(u.merchant, 'Cafe Coffee Day');
    expect(u.amountPaise, 12000);
  });

  test('rejects non-UPI payloads', () {
    expect(parseUpi('https://example.com'), isNull);
    expect(parseUpi('upi://mandate?pa=a@b'), isNull);
    expect(parseUpi('upi://pay?pn=NoAddress'), isNull);
    expect(parseUpi(''), isNull);
  });
}
