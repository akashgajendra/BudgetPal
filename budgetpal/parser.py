import io
import re
from dataclasses import dataclass
from datetime import datetime

import pdfplumber

DATE_PATTERNS = [
    r"\d{1,2}/\d{1,2}/\d{2,4}",
    r"\d{4}-\d{2}-\d{2}",
    r"\d{1,2} [A-Za-z]{3} \d{4}",
    r"[A-Za-z]{3} \d{1,2},? \d{4}",
    r"\d{1,2}/\d{1,2}",
]
DATE_RE = re.compile(r"^(" + "|".join(DATE_PATTERNS) + r")\s+(.*)$")
YEAR_HINT_RE = re.compile(
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+(\d{4})", re.IGNORECASE
)
AMOUNT_RE = re.compile(r"(-?\(?\$?-?[\d,]+\.\d{2}\)?\s*(?:CR|DR)?)\s*$", re.IGNORECASE)
AMOUNT_ALL_RE = re.compile(r"(-?\(?\$?-?[\d,]+\.\d{2}\)?)\s*(?:CR|DR)?", re.IGNORECASE)
CREDIT_HINTS = (
    "direct dep", "transfer from", "interest payment", "interest earned",
    "mobile deposit", "atm deposit", "cash deposit", "ach credit",
    "deposit", "refund", "reversal", "payroll", "reimbursement",
)
SKIP_HINTS = ("balance", "total", "subtotal", "beginning balance", "ending balance",
              "average ledger", "average balance", "interest paid", "overdraft protection",
              "continued on", "transaction history", "activity summary", "page ",
              "internet payment - thank you", "payment thank you", "payment - thank you",
              "e-payment", "epay", "credit crd epay", "mahadevaiah")
DESC_NOISE_RE = re.compile(r"\s*-?\s*\d{4}\s+merch\s+id\s+\d+\s*", re.IGNORECASE)

PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    re.compile(r"\baccount\s*#?\s*:?\s*\d{4,}\b", re.IGNORECASE),
    re.compile(r"\bacct\s*#?\s*:?\s*\d{4,}\b", re.IGNORECASE),
    re.compile(r"\brouting\s*#?\s*:?\s*\d{9}\b", re.IGNORECASE),
]
PII_LINE_HINTS = (
    "account holder", "account owner", "customer name", "statement for",
    "member name", "primary account", "social security",
)


@dataclass
class Transaction:
    date: datetime
    description: str
    amount: float  # spending is negative, money in is positive


def _is_pii_line(line: str) -> bool:
    lower = line.lower()
    if any(hint in lower for hint in PII_LINE_HINTS):
        return True
    return any(p.search(line) for p in PII_PATTERNS)


def extract_lines(pdf_bytes: bytes) -> list[str]:
    lines = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                stripped = line.strip()
                if stripped and not _is_pii_line(stripped):
                    lines.append(stripped)
    return lines


def _parse_date(raw: str) -> datetime | None:
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d %b %Y", "%b %d %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    parts = raw.split("/")
    if len(parts) == 2:
        try:
            month, day = int(parts[0]), int(parts[1])
            return datetime(2000, month, day)
        except ValueError:
            pass
    return None


def _parse_amount(raw: str) -> float | None:
    cleaned = raw.upper().replace("$", "").replace(",", "").strip()
    is_credit = cleaned.endswith("CR")
    is_debit = cleaned.endswith("DR")
    cleaned = cleaned.replace("CR", "").replace("DR", "").strip()
    negative = cleaned.startswith("-") or (cleaned.startswith("(") and cleaned.endswith(")"))
    cleaned = cleaned.strip("()-").strip()
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if is_credit:
        return value
    if is_debit or negative:
        return -value
    return -value


def parse_lines(lines: list[str]) -> list[Transaction]:
    transactions = []
    for line in lines:
        match = DATE_RE.match(line)
        if not match:
            continue
        date_raw, rest = match.groups()
        all_amounts = list(AMOUNT_ALL_RE.finditer(rest))
        if not all_amounts:
            continue
        if len(all_amounts) >= 2:
            amount_match = all_amounts[-2]
        else:
            amount_match = all_amounts[0]
        amount = _parse_amount(amount_match.group(1))
        date = _parse_date(date_raw)
        if amount is None or date is None:
            continue
        description = rest[: amount_match.start()].strip(" -")
        description = DESC_NOISE_RE.sub(" ", description).strip(" -")
        if not description or any(h in description.lower() for h in SKIP_HINTS):
            continue
        if amount_match.group(1).upper().endswith("CR") or any(h in description.lower() for h in CREDIT_HINTS):
            amount = abs(amount)
        transactions.append(Transaction(date=date, description=description, amount=amount))
    return transactions


def _extract_year(lines: list[str]) -> int | None:
    for line in lines[:30]:
        m = YEAR_HINT_RE.search(line)
        if m:
            return int(m.group(1))
    return None


def parse_statement(pdf_bytes: bytes) -> tuple[list[Transaction], int]:
    lines = extract_lines(pdf_bytes)
    year = _extract_year(lines)
    transactions = parse_lines(lines)

    if year:
        for t in transactions:
            if t.date.year == 2000:
                t.date = t.date.replace(year=year)
    return transactions, len(lines)
