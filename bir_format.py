# bir_format.py
"""BIR DAT file formatting utilities for Philippine tax compliance.

All functions are pure — no side effects, no Odoo calls.
Encoding note: DAT files use cp1252 with CRLF line endings.
"""

from __future__ import annotations


def clean_tin(raw: str | None) -> str:
    """Strip non-numeric chars, return exactly 9 digits (right-padded with 0)."""
    digits = "".join(c for c in str(raw or "") if c.isdigit())
    if not digits:
        return "000000000"
    return digits[:9].ljust(9, "0")


def clean_branch_code(raw: str | None) -> str:
    """Extract 4-digit branch code from VAT (digits 10-13).
    Philippine TIN format: NNN-NNN-NNN-BBBB — branch code follows the 9-digit TIN.
    Returns '0000' (head office) if not present.
    """
    digits = "".join(c for c in str(raw or "") if c.isdigit())
    bc = digits[9:13] if len(digits) >= 13 else ""
    return bc.ljust(4, "0") if bc else "0000"


def clean_str(raw: str | None, max_len: int = 50) -> str:
    """Uppercase, sanitize special chars, collapse whitespace, truncate.

    BIR validation module rejects periods, commas, and apostrophes.
    Mirrors the spreadsheet formula:
      UPPER(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(val,".",""),",",""),"&","AND"),"'",""))
    """
    s = str(raw or "").upper()
    s = s.replace("&", "AND")
    s = s.replace("\u00d1", "N").replace("\u00f1", "N")
    for ch in ".,'\u2018\u2019\u201c\u201d":
        s = s.replace(ch, "")
    s = " ".join(s.split())
    return s[:max_len]


def fmt_date_slsp(d: str) -> str:
    """'YYYY-MM-DD' -> 'MM/DD/YYYY' (SLSP DAT format)."""
    return f"{d[5:7]}/{d[8:10]}/{d[:4]}"


def fmt_date_qap(d: str) -> str:
    """'YYYY-MM-DD' -> 'MM/YYYY' (QAP DAT format)."""
    return f"{d[5:7]}/{d[:4]}"


def _q(s: str) -> str:
    """Quote a string field for DAT output."""
    return f'"{s}"'


def _n(v: float) -> str:
    """Format a numeric field — 2 decimal places."""
    return f"{v:.2f}"


def slp_dat_line(row: dict, filing_tin: str) -> str:
    """Build one SLP (Summary List of Purchases) DAT detail line."""
    parts = [
        "D",
        "P",
        _q(row["tin"]),
        _q(row["registered_name"]),
        _q(row.get("last_name", "")),
        _q(row.get("first_name", "")),
        _q(row.get("middle_name", "")),
        _q(row.get("street", "")),
        _q(row.get("city", "")),
        _n(row.get("exempt_amount", 0)),
        _n(row.get("zero_rated_amount", 0)),
        _n(row.get("services_amount", 0)),
        _n(row.get("capital_goods_amount", 0)),
        _n(row.get("other_goods_amount", 0)),
        _n(row.get("input_tax", 0)),
        filing_tin,
        row["date"],
    ]
    return ",".join(parts)


def sls_dat_line(row: dict, filing_tin: str) -> str:
    """Build one SLS (Summary List of Sales) DAT detail line."""
    parts = [
        "D",
        "S",
        _q(row["tin"]),
        _q(row["registered_name"]),
        _q(row.get("last_name", "")),
        _q(row.get("first_name", "")),
        _q(row.get("middle_name", "")),
        _q(row.get("street", "")),
        _q(row.get("city", "")),
        _n(row.get("exempt_amount", 0)),
        _n(row.get("zero_rated_amount", 0)),
        _n(row.get("taxable_amount", 0)),
        _n(row.get("tax_amount", 0)),
        filing_tin,
        row["date"],
    ]
    return ",".join(parts)


def sls_dat_header(company: dict, rows: list[dict], period: str) -> str:
    """Build the H record for SLS (Summary List of Sales).

    Columns (16): H,S,TIN,Name,First,Middle,Last,Name,Street,City,
                  ExemptTotal,ZeroTotal,TaxableTotal,VATTotal,RDO,Period
    company keys: tin, registered_name, first_name, middle_name, last_name,
                  street, city, rdo
    period: MM/DD/YYYY
    """
    tin = company.get("tin", "000000000")
    name = _q(clean_str(company.get("registered_name", ""), 50))
    first = _q(clean_str(company.get("first_name", ""), 50))
    middle = _q(clean_str(company.get("middle_name", ""), 50))
    last = _q(clean_str(company.get("last_name", ""), 50))
    street = _q(clean_str(company.get("street", ""), 50))
    city = _q(clean_str(company.get("city", ""), 50))
    rdo = str(company.get("rdo", "")).strip()
    parts = [
        "H", "S", tin,
        name, first, middle, last, name, street, city,
        _n(sum(r.get("exempt_amount", 0) for r in rows)),
        _n(sum(r.get("zero_rated_amount", 0) for r in rows)),
        _n(sum(r.get("taxable_amount", 0) for r in rows)),
        _n(sum(r.get("tax_amount", 0) for r in rows)),
        rdo, period,
    ]
    return ",".join(parts)


def slp_dat_header(company: dict, rows: list[dict], period: str) -> str:
    """Build the H record for SLP (Summary List of Purchases).

    Columns (20): H,P,TIN,Name,First,Middle,Last,Name,Street,City,
                  ExemptTotal,ZeroTotal,ServicesTotal,CapGoodsTotal,GoodsTotal,
                  VATTotal,VATTotal,0,RDO,Period
    The duplicate VATTotal and trailing 0 (importation placeholder) match
    the BIR-accepted spreadsheet format.
    """
    tin = company.get("tin", "000000000")
    name = _q(clean_str(company.get("registered_name", ""), 50))
    first = _q(clean_str(company.get("first_name", ""), 50))
    middle = _q(clean_str(company.get("middle_name", ""), 50))
    last = _q(clean_str(company.get("last_name", ""), 50))
    street = _q(clean_str(company.get("street", ""), 50))
    city = _q(clean_str(company.get("city", ""), 50))
    rdo = str(company.get("rdo", "")).strip()
    t_vat = _n(sum(r.get("input_tax", 0) for r in rows))
    parts = [
        "H", "P", tin,
        name, first, middle, last, name, street, city,
        _n(sum(r.get("exempt_amount", 0) for r in rows)),
        _n(sum(r.get("zero_rated_amount", 0) for r in rows)),
        _n(sum(r.get("services_amount", 0) for r in rows)),
        _n(sum(r.get("capital_goods_amount", 0) for r in rows)),
        _n(sum(r.get("other_goods_amount", 0) for r in rows)),
        t_vat, t_vat, "0",
        rdo, period,
    ]
    return ",".join(parts)


def qap_dat_line(row: dict, seq: int) -> str:
    """Build one QAP (Quarterly Alphalist of Payees) DAT detail line."""
    parts = [
        "D1",
        "1601EQ",
        str(seq),
        row["tin"],
        "0000",
        _q(row["registered_name"]),
        _q(row.get("last_name", "")),
        _q(row.get("first_name", "")),
        _q(row.get("middle_name", "")),
        row["date"],
        str(row.get("atc", "")),
        str(row.get("tax_rate", 0)),
        _n(row.get("gross_income", 0)),
        _n(row.get("tax_withheld", 0)),
    ]
    return ",".join(parts)

