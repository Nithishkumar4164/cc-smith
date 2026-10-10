/// Capture responses: statement and credit-report uploads (POST /me/capture/*). Pure Dart.
library;

import 'models.dart';

int? _i(Object? v) => v is num ? v.toInt() : null;
String? _s(Object? v) => v?.toString();
List<Json> _maps(Object? v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : <Json>[];

class StatementLine {
  final String? date, description, direction, kind;
  final int amountPaise;
  const StatementLine({this.date, this.description, this.direction, this.kind, required this.amountPaise});
  factory StatementLine.fromJson(Json j) => StatementLine(
    date: _s(j['date']),
    description: _s(j['description']),
    direction: _s(j['direction']),
    kind: _s(j['kind']),
    amountPaise: _i(j['amount_paise']) ?? 0,
  );
}

/// "Confirm what we read" for an uploaded statement.
class StatementResult {
  final String? issuerHint, last4, statementDate, dueDate, cardId, unmatchedReason;
  final int? totalDuePaise, minDuePaise, closingBalancePaise, creditLimitPaise, availableCreditPaise, paymentsPaise;
  final bool matched;
  final Map<String, Object?> updated;
  final Map<String, int> lineOutcomes; // recorded | duplicate | ...
  final List<StatementLine> lines;
  final List<String> warnings;
  const StatementResult({
    this.issuerHint,
    this.last4,
    this.statementDate,
    this.dueDate,
    this.cardId,
    this.unmatchedReason,
    this.totalDuePaise,
    this.minDuePaise,
    this.closingBalancePaise,
    this.creditLimitPaise,
    this.availableCreditPaise,
    this.paymentsPaise,
    required this.matched,
    this.updated = const {},
    this.lineOutcomes = const {},
    this.lines = const [],
    this.warnings = const [],
  });
  factory StatementResult.fromJson(Json j) {
    final r = Map<String, dynamic>.from(j['read'] as Map? ?? {});
    return StatementResult(
      issuerHint: _s(r['issuer_hint']),
      last4: _s(r['last4']),
      statementDate: _s(r['statement_date']),
      dueDate: _s(r['due_date']),
      totalDuePaise: _i(r['total_due_paise']),
      minDuePaise: _i(r['min_due_paise']),
      closingBalancePaise: _i(r['closing_balance_paise']),
      creditLimitPaise: _i(r['credit_limit_paise']),
      availableCreditPaise: _i(r['available_credit_paise']),
      paymentsPaise: _i(r['payments_paise']),
      lines: _maps(r['lines']).map(StatementLine.fromJson).toList(),
      warnings: (r['warnings'] as List? ?? []).map((e) => '$e').toList(),
      cardId: _s(j['card_id']),
      matched: j['matched'] == true,
      unmatchedReason: _s(j['unmatched_reason']),
      updated: Map<String, Object?>.from(j['updated'] as Map? ?? {}),
      lineOutcomes: (j['lines'] as Map? ?? {}).map((k, v) => MapEntry('$k', _i(v) ?? 0)),
    );
  }
}

class ReportAccount {
  final String? lender, issuerHint, accountType, last4, dpd, opened, closed, status, heldCardId;
  /// The exact product, when the bureau feed names it.
  final String? cardId, cardName;
  final int? creditLimitPaise, currentBalancePaise, overduePaise, maxDpdDays;
  const ReportAccount({
    this.lender,
    this.issuerHint,
    this.accountType,
    this.last4,
    this.dpd,
    this.opened,
    this.closed,
    this.status,
    this.heldCardId,
    this.cardId,
    this.cardName,
    this.creditLimitPaise,
    this.currentBalancePaise,
    this.overduePaise,
    this.maxDpdDays,
  });
  factory ReportAccount.fromJson(Json j) => ReportAccount(
    lender: _s(j['lender']),
    issuerHint: _s(j['issuer_hint']),
    accountType: _s(j['account_type']),
    last4: _s(j['last4']),
    dpd: _s(j['dpd']),
    opened: _s(j['opened']),
    closed: _s(j['closed']),
    status: _s(j['status']),
    heldCardId: _s(j['held_card_id']),
    cardId: _s(j['card_id']),
    cardName: _s(j['card_name']),
    creditLimitPaise: _i(j['credit_limit_paise']) ?? _i(j['sanctioned_paise']),
    currentBalancePaise: _i(j['current_balance_paise']),
    overduePaise: _i(j['overdue_paise']),
    maxDpdDays: _i(j['max_dpd_days']),
  );
  bool get isOpen => closed == null && (status == null || status!.toLowerCase() != 'closed');
}

class Enquiry {
  final String date;
  final String? lender, purpose;
  const Enquiry({required this.date, this.lender, this.purpose});
  factory Enquiry.fromJson(Json j) => Enquiry(date: '${j['date']}', lender: _s(j['lender']), purpose: _s(j['purpose']));
}

class CreditReportResult {
  final String? bureau, reportDate;
  final int? score;
  final int enquiries6m;
  final List<ReportAccount> accounts;
  final List<Enquiry> enquiries;
  final List<String> warnings;
  const CreditReportResult({
    this.bureau,
    this.reportDate,
    this.score,
    this.enquiries6m = 0,
    this.accounts = const [],
    this.enquiries = const [],
    this.warnings = const [],
  });
  factory CreditReportResult.fromJson(Json j) {
    final st = Map<String, dynamic>.from(j['stored'] as Map? ?? {});
    final r = Map<String, dynamic>.from(j['report'] as Map? ?? {});
    return CreditReportResult(
      bureau: _s(st['bureau'] ?? r['bureau']),
      reportDate: _s(st['report_date'] ?? r['report_date']),
      score: _i(st['score'] ?? r['score']),
      enquiries6m: _i(st['enquiries_6m']) ?? 0,
      accounts: _maps(r['accounts']).map(ReportAccount.fromJson).toList(),
      enquiries: _maps(r['enquiries']).map(Enquiry.fromJson).toList(),
      warnings: (r['warnings'] as List? ?? []).map((e) => '$e').toList(),
    );
  }
}

/// Words that pick an issuer's cards out of the catalogue for an issuer id.
const issuerWords = {
  'hdfc_bank': 'hdfc',
  'icici_bank': 'icici',
  'sbi_card': 'sbi',
  'axis_bank': 'axis',
  'hsbc_india': 'hsbc',
  'kotak_mahindra_bank': 'kotak',
  'idfc_first_bank': 'idfc',
  'yes_bank': 'yes',
  'au_small_finance_bank': 'au ',
};

/// Catalogue cards from the issuer an account (or statement) names.
List<CardSummary> cardsFromIssuer(String? issuerHint, String? lender, Iterable<CardSummary> catalogue) {
  final word = issuerWords[issuerHint] ?? lender?.toLowerCase().split(' ').first;
  if (word == null || word.isEmpty) return const [];
  return catalogue.where((c) => '${c.issuer.toLowerCase()} '.contains(word)).toList();
}
