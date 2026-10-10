"""Synthetic statement and credit-report PDFs for the capture tests. Every name, number
and value here is made up."""

from fpdf import FPDF
from fpdf.enums import EncryptionMethod


def _pdf() -> FPDF:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=9)
    return pdf


def _row(pdf: FPDF, cells: list[tuple[float, str]], h: float = 6) -> None:
    for w, text in cells:
        pdf.cell(w, h, text)
    pdf.ln(h)


def _out(pdf: FPDF, password: str | None) -> bytes:
    if password:
        pdf.set_encryption(owner_password="owner-" + password, user_password=password, encryption_method=EncryptionMethod.AES_128)
    return bytes(pdf.output())


def statement_pdf(password: str | None = "TEST1234", lines: list[tuple[str, str, str, str]] | None = None,
                  statement_date: str = "15/09/2026", last4: str = "4321", style: str = "box") -> bytes:
    """HDFC-like layout: masked card number, a two-row summary box (labels above values),
    then a transaction table whose credits carry a "Cr" suffix. style="inline" prints
    "Label : value" pairs instead (SBI/ICICI-like)."""
    lines = lines or [
        ("18/08/2026", "SWIGGY BANGALORE", "12", "1,250.00"),
        ("21/08/2026", "AMAZON PAY INDIA PVT LTD", "40", "4,000.00"),
        ("25/08/2026", "PAYMENT RECEIVED - NETBANKING THANK YOU", "", "10,000.00 Cr"),
        ("02/09/2026", "REFUND AMAZON PAY INDIA", "", "500.00 Cr"),
        ("05/09/2026", "SAMPLE FUEL STATION MUMBAI", "0", "2,000.00"),
        ("15/09/2026", "IGST-VPS2526000000-RATE 18.0 -27", "", "36.00"),
    ]
    pdf = _pdf()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "HDFC Bank Credit Card Statement", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    _row(pdf, [(0, "Name : TEST CARDHOLDER")])
    _row(pdf, [(0, "Address : 1 SAMPLE STREET, TESTNAGAR, 400001")])
    _row(pdf, [(0, f"Card No : 5522 60XX XXXX {last4}")])
    pdf.ln(3)
    if style == "box":
        _row(pdf, [(38, "Statement Date"), (38, "Payment Due Date"), (38, "Total Dues"), (38, "Minimum Amount Due")])
        _row(pdf, [(38, statement_date), (38, "05/10/2026"), (38, "36,786.00"), (38, "1,840.00")])
        pdf.ln(2)
        _row(pdf, [(50, "Credit Limit"), (50, "Available Credit Limit"), (50, "Available Cash Limit")])
        _row(pdf, [(50, "2,00,000.00"), (50, "1,63,214.00"), (50, "80,000.00")])
        pdf.ln(2)
        _row(pdf, [(38, "Opening Balance"), (38, "Payment/Credits"), (38, "Purchase/Debits"), (38, "Finance Charges"), (38, "Total Dues")])
        _row(pdf, [(38, "40,000.00"), (38, "10,500.00"), (38, "7,286.00"), (38, "0.00"), (38, "36,786.00")])
    else:
        _row(pdf, [(0, f"Statement Date : {statement_date}")])
        _row(pdf, [(0, "Payment Due Date : 05/10/2026")])
        _row(pdf, [(0, "Total Amount Due : Rs. 36,786.00")])
        _row(pdf, [(0, "Minimum Amount Due : Rs. 1,840.00")])
        _row(pdf, [(0, "Credit Limit : Rs. 2,00,000.00   Available Credit Limit : Rs. 1,63,214.00")])
        _row(pdf, [(0, "Opening Balance : 40,000.00")])
    pdf.ln(4)
    _row(pdf, [(30, "Date"), (100, "Transaction Description"), (25, "Reward Points"), (35, "Amount (in Rs.)")])
    for d, desc, pts, amt in lines:
        _row(pdf, [(30, d), (100, desc), (25, pts), (35, amt)])
    pdf.ln(4)
    _row(pdf, [(0, "Important: this is a synthetic statement for tests.")])
    return _out(pdf, password)


def credit_report_pdf(password: str | None = None) -> bytes:
    """CIBIL-like consumer report: score, personal details (must be dropped), credit-card
    accounts as label/value blocks, and an enquiries table."""
    pdf = _pdf()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "TransUnion CIBIL - CIBIL Score & Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    _row(pdf, [(0, "Date: 01/10/2026        Control Number: 1,234,567,890")])
    _row(pdf, [(0, "CIBIL SCORE 782")])
    pdf.ln(2)
    _row(pdf, [(0, "PERSONAL INFORMATION")])
    _row(pdf, [(0, "NAME: TEST PERSON   DATE OF BIRTH: 01/01/1990   GENDER: Male")])
    _row(pdf, [(0, "INCOME TAX ID NUMBER (PAN): ABCDE1234F")])
    _row(pdf, [(0, "TELEPHONE: 9876543210   EMAIL: test.person@example.com")])
    _row(pdf, [(0, "ADDRESS: 1 SAMPLE STREET, TESTNAGAR, MUMBAI 400001")])
    pdf.ln(2)
    _row(pdf, [(0, "ACCOUNT INFORMATION")])
    accounts = [
        ("HDFC BANK", "Credit Card", "XXXXXXXXXXXX4321", "15-03-2019", "2,00,000", "36,786", "000|000|000|000|000|000", "Active"),
        ("ICICI BANK", "Credit Card", "XXXXXXXXXXXX8765", "01-07-2021", "1,50,000", "12,000", "000|000|030|000|000|000", "Active"),
        ("SBI CARDS AND PAYMENT SERVICES", "Credit Card", "XXXXXXXXXXXX1111", "10-11-2017", "90,000", "0", "000|000|000|STD|STD|STD", "Closed"),
        ("BAJAJ FINANCE", "Consumer Loan", "XXXXXXXX9999", "05-05-2022", "60,000", "10,000", "000|000|000", "Active"),
    ]
    for lender, typ, acct, opened, limit, bal, dpd, status in accounts:
        pdf.ln(1)
        _row(pdf, [(0, f"MEMBER NAME: {lender}")])
        _row(pdf, [(0, f"ACCOUNT NUMBER: {acct}")])
        _row(pdf, [(0, f"TYPE: {typ}   OWNERSHIP: Individual")])
        _row(pdf, [(0, f"OPENED: {opened}   STATUS: {status}")])
        _row(pdf, [(0, f"CREDIT LIMIT: {limit}   SANCTIONED: {limit}   CURRENT BALANCE: {bal}")])
        _row(pdf, [(0, f"DAYS PAST DUE: {dpd}")])
    pdf.ln(2)
    _row(pdf, [(0, "ENQUIRY INFORMATION")])
    _row(pdf, [(60, "MEMBER"), (35, "ENQUIRY DATE"), (50, "ENQUIRY PURPOSE"), (35, "ENQUIRY AMOUNT")])
    _row(pdf, [(60, "AXIS BANK"), (35, "12-08-2026"), (50, "Credit Card"), (35, "1,00,000")])
    _row(pdf, [(60, "KOTAK MAHINDRA BANK"), (35, "02-06-2026"), (50, "Personal Loan"), (35, "3,00,000")])
    _row(pdf, [(0, "END OF REPORT")])
    return _out(pdf, password)
