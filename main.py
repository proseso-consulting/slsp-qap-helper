# main.py
"""Enhanced SLSP & QAP export service.

GET  /{token}/           -> renders the export form
GET  /{token}/companies  -> returns company list for a given db (AJAX)
POST /{token}/export     -> generates and returns XLSX or DAT file

All routes are guarded by ACCESS_TOKEN in the URL path.
Unknown tokens receive a 404 to avoid confirming service existence.
"""

from __future__ import annotations

import calendar
import io
import logging
import os
import re
import threading as _threading
import zipfile
from datetime import date
from datetime import date as date_type
from itertools import groupby
from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from bir_format import clean_branch_code, clean_str, clean_tin
from odoo_client import (
    OdooConnection,
    classify_purchase,
    connect,
    fetch_bill_lines_with_tax,
    fetch_client_tasks,
    fetch_company_profile,
    fetch_income_statement,
    fetch_journal_entries_with_wht,
    fetch_partner_details,
    fetch_partners_by_ids,
    fetch_posted_bills,
    fetch_tax_details,
    fetch_tax_lines_by_atc,
    fetch_vat_summary,
    get_companies,
    get_semaphore,
)
from qap_builder import build_qap_rows, write_qap_dat, write_qap_xlsx
from slsp_builder import aggregate_by_tin, build_slsp_rows, write_slsp_dat, write_slsp_xlsx

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Enhanced BIR Reports")
templates = Jinja2Templates(directory="templates")

_ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "")

if not _ACCESS_TOKEN:
    raise RuntimeError("ACCESS_TOKEN environment variable must be set")

for _var in ("SOURCE_BASE_URL", "SOURCE_DB", "SOURCE_LOGIN", "SOURCE_PASSWORD"):
    if not os.environ.get(_var):
        raise RuntimeError(f"{_var} environment variable must be set")


def _check_token(token: str):
    """Return 404 for unknown tokens — avoids confirming service existence."""
    if token != _ACCESS_TOKEN:
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return None


_SOURCE_CONN: OdooConnection | None = None
_CLIENTS_CACHE: list[dict] | None = None
_CLIENTS_LOCK = _threading.Lock()


def _get_source_conn() -> OdooConnection:
    global _SOURCE_CONN
    if _SOURCE_CONN is None:
        _SOURCE_CONN = connect(
            os.environ["SOURCE_BASE_URL"],
            os.environ["SOURCE_DB"],
            os.environ["SOURCE_LOGIN"],
            os.environ["SOURCE_PASSWORD"],
        )
    return _SOURCE_CONN


def _load_clients() -> list[dict]:
    """Load client list from source Odoo project.task records (cached per container lifetime)."""
    global _CLIENTS_CACHE
    if _CLIENTS_CACHE is not None:
        return _CLIENTS_CACHE
    with _CLIENTS_LOCK:
        if _CLIENTS_CACHE is not None:
            return _CLIENTS_CACHE
        try:
            source = _get_source_conn()
            clients = fetch_client_tasks(source)
            _CLIENTS_CACHE = clients
            return _CLIENTS_CACHE
        except Exception:
            log.exception("Failed to load client list from source Odoo")
            return []


def _default_quarter_dates() -> tuple[str, str]:
    """Return start/end of the current calendar quarter."""
    today = date.today()
    q_start_month = ((today.month - 1) // 3) * 3 + 1
    q_start = date(today.year, q_start_month, 1)
    q_end_month = q_start_month + 2
    q_end = date(today.year, q_end_month, calendar.monthrange(today.year, q_end_month)[1])
    return str(q_start), str(q_end)


def _line_gross(line: dict) -> float:
    """Return the base (pre-tax) amount for a move line.

    Bills populate ``price_subtotal``; journal-entry lines leave it at 0 and
    use ``debit``/``credit`` instead.  Fall back to the latter when the former
    is missing or zero.
    """
    subtotal = line.get("price_subtotal", 0)
    if subtotal:
        return abs(subtotal)
    return abs(line.get("debit", 0) - line.get("credit", 0))


def _extract_slsp_rows(conn, moves, report_type, source_label, partners_cache=None):
    """Convert fetched moves (bills or JEs) into cleaned SLSP rows."""
    rows = []
    for move in moves:
        lines = move.get("enriched_lines") or fetch_bill_lines_with_tax(conn, move["id"])
        for line in lines:
            partner_id = line.get("partner_id") or move.get("partner_id")
            if not partner_id:
                continue
            pid = partner_id[0] if isinstance(partner_id, list) else partner_id
            if partners_cache is not None and pid in partners_cache:
                partner = partners_cache[pid]
            else:
                partner = fetch_partner_details(conn, pid)
            tax_details = line.get("tax_details") or fetch_tax_details(conn, line.get("tax_ids", []))
            for tax in tax_details:
                use = tax.get("type_tax_use", "")
                if report_type == "purchases" and use != "purchase":
                    continue
                if report_type == "sales" and use != "sale":
                    continue
                # Skip EWT/FWT taxes — they have ATC codes and belong in QAP, not SLSP
                if tax.get("l10n_ph_atc"):
                    continue
                gross = _line_gross(line)
                tax_amt = round(gross * abs(tax.get("amount", 0)) / 100, 2)
                account_id_val = line.get("account_id")
                if report_type == "purchases":
                    if account_id_val and isinstance(account_id_val, list):
                        category = classify_purchase(conn, account_id_val[0])
                    else:
                        category = "other_than_capital_goods"
                else:
                    category = None
                row = {
                    "tin": clean_tin(partner.get("vat", "")),
                    "registered_name": clean_str(partner.get("name", ""), 50),
                    "last_name": clean_str(partner.get("last_name", ""), 30),
                    "first_name": clean_str(partner.get("first_name", ""), 30),
                    "middle_name": clean_str(partner.get("middle_name", ""), 30),
                    "street": clean_str(partner.get("street", ""), 30),
                    "city": clean_str(partner.get("city", ""), 30),
                    "date": move["date"],
                    "source": source_label,
                }
                if report_type == "purchases":
                    row.update(
                        {
                            "exempt_amount": 0,
                            "zero_rated_amount": 0,
                            "services_amount": gross if category == "services" else 0,
                            "capital_goods_amount": gross if category == "capital_goods" else 0,
                            "other_goods_amount": gross if category == "other_than_capital_goods" else 0,
                            "input_tax": tax_amt,
                        }
                    )
                else:
                    row.update(
                        {
                            "exempt_amount": 0,
                            "zero_rated_amount": 0,
                            "taxable_amount": gross,
                            "tax_amount": tax_amt,
                        }
                    )
                rows.append(row)
    return rows


def _extract_qap_rows(conn, moves, source_label, partners_cache=None):
    """Convert fetched moves (bills or JEs) into cleaned QAP rows."""
    rows = []
    for move in moves:
        lines = move.get("enriched_lines") or fetch_bill_lines_with_tax(conn, move["id"])
        for line in lines:
            partner_id = line.get("partner_id") or move.get("partner_id")
            if not partner_id:
                continue
            pid = partner_id[0] if isinstance(partner_id, list) else partner_id
            if partners_cache is not None and pid in partners_cache:
                partner = partners_cache[pid]
            else:
                partner = fetch_partner_details(conn, pid)
            tax_details = line.get("tax_details") or fetch_tax_details(conn, line.get("tax_ids", []))
            for tax in tax_details:
                atc = tax.get("l10n_ph_atc")
                if not atc or tax.get("type_tax_use") != "purchase":
                    continue
                gross = _line_gross(line)
                rows.append(
                    {
                        "tin": clean_tin(partner.get("vat", "")),
                        "registered_name": clean_str(partner.get("name", ""), 50),
                        "last_name": clean_str(partner.get("last_name", ""), 30),
                        "first_name": clean_str(partner.get("first_name", ""), 30),
                        "middle_name": clean_str(partner.get("middle_name", ""), 30),
                        "date": move["date"],
                        "atc": atc,
                        "tax_rate": abs(tax.get("amount", 0)),
                        "gross_income": gross,
                        "tax_withheld": round(gross * abs(tax["amount"]) / 100, 2),
                        "source": source_label,
                    }
                )
    return rows


@app.get("/{token}/", response_class=HTMLResponse)
def index(token: str, request: Request, db: str = Query(default="")):
    err = _check_token(token)
    if err:
        return err
    clients = _load_clients()
    today = date.today()
    default_period = f"{today.year}-{today.month:02d}"
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "clients": clients,
            "default_period": default_period,
            "locked_db": db,
        },
    )


@app.get("/{token}/companies")
def companies_endpoint(token: str, db: str = Query(...)):
    """AJAX endpoint — returns company list for the selected database.

    Each company includes fiscalyear_last_month (1-12, default 12 = calendar year).
    """
    err = _check_token(token)
    if err:
        return err
    clients = _load_clients()
    client = next((c for c in clients if c["db"] == db), None)
    if not client:
        return JSONResponse([], status_code=200)
    try:
        conn = connect(client["url"], client["db"], client["user"], client["api_key"])
        companies = get_companies(conn)
        # Enrich with fiscal year month (default 12 = calendar year Dec)
        for c in companies:
            c.setdefault("fiscalyear_last_month", 12)
        return companies
    except Exception:
        log.warning("Failed to load companies for db=%s", db, exc_info=True)
        return JSONResponse([], status_code=200)


@app.post("/{token}/export")
def export_report(
    token: str,
    report_type: str = Form(...),
    db_name: str = Form(...),
    company_id: int = Form(...),
    date_from: str = Form(...),
    date_to: str = Form(...),
    format: str = Form("xlsx"),
):
    err = _check_token(token)
    if err:
        return err

    try:
        date_type.fromisoformat(date_from)
        date_type.fromisoformat(date_to)
    except ValueError:
        return JSONResponse({"detail": "Invalid date format"}, status_code=400)

    safe_db = re.sub(r"[^a-zA-Z0-9_-]", "", db_name)

    clients = _load_clients()
    client = next((c for c in clients if c["db"] == db_name), None)
    if not client:
        return JSONResponse({"detail": "Database not found"}, status_code=400)

    try:
        conn = connect(client["url"], client["db"], client["user"], client["api_key"], company_id=company_id)
    except ConnectionError as e:
        return JSONResponse({"detail": str(e)}, status_code=502)

    companies = get_companies(conn)
    selected = next((c for c in companies if c["id"] == company_id), {})
    raw_vat = selected.get("vat", "")
    filing_tin = clean_tin(raw_vat)
    branch_code = clean_branch_code(raw_vat)
    company_dict = {
        "tin": filing_tin,
        "raw_vat": raw_vat,
        "registered_name": clean_str(selected.get("name", ""), 50),
        "first_name": "",
        "middle_name": "",
        "last_name": "",
        "street": clean_str(selected.get("street", ""), 50),
        "city": clean_str(selected.get("city", ""), 50),
        "rdo": selected.get("l10n_ph_rdo", ""),
    }

    with get_semaphore(client["db"]):
        try:
            if report_type in ("slsp_purchases", "slsp_sales"):
                slsp_type = "purchases" if report_type == "slsp_purchases" else "sales"
                move_types = ["in_invoice", "in_refund"] if slsp_type == "purchases" else ["out_invoice", "out_refund"]
                bills = fetch_posted_bills(conn, move_types, date_from, date_to)
                jes = fetch_journal_entries_with_wht(conn, date_from, date_to)
                _all_slsp_pids = set()
                for _m in bills + jes:
                    _pid = _m.get("partner_id")
                    if _pid:
                        _all_slsp_pids.add(_pid[0] if isinstance(_pid, list) else _pid)
                slsp_partners = fetch_partners_by_ids(conn, list(_all_slsp_pids))
                bill_rows = _extract_slsp_rows(conn, bills, slsp_type, "bill", slsp_partners)
                je_rows = _extract_slsp_rows(conn, jes, slsp_type, "journal_entry", slsp_partners)
                merged = build_slsp_rows(bill_rows, je_rows)

                summary = f"{len(bill_rows)} bills + {len(je_rows)} journal entries = {len(merged)} total"
                label = "SLP" if slsp_type == "purchases" else "SLS"
                type_char = "P" if slsp_type == "purchases" else "S"
                filename = f"{label}_{date_from}_to_{date_to}_{safe_db}"

                def _slsp_dat_filename(ym: str) -> str:
                    """BIR SLSP filename: <TIN><P|S><MMYYYY>.dat  e.g. 005302695P112025.dat"""
                    year, month = ym.split("-")
                    return f"{filing_tin}{type_char}{month}{year}.dat"

                if format == "dat":
                    # Group rows by month; if multi-month → ZIP, else single DAT
                    sorted_rows = sorted(merged, key=lambda r: r.get("date", "")[:7])
                    by_month = {ym: list(grp) for ym, grp in groupby(sorted_rows, key=lambda r: r.get("date", "")[:7])}
                    if len(by_month) > 1:
                        zip_buf = io.BytesIO()
                        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                            for ym, month_rows in by_month.items():
                                yr, mo = map(int, ym.split("-"))
                                period_end_ym = f"{yr}-{mo:02d}-{calendar.monthrange(yr, mo)[1]:02d}"
                                dat_content = write_slsp_dat(
                                    aggregate_by_tin(month_rows),
                                    report_type=slsp_type,
                                    filing_tin=filing_tin,
                                    period_end=period_end_ym,
                                    company=company_dict,
                                )
                                zf.writestr(_slsp_dat_filename(ym), dat_content.encode("cp1252", errors="replace"))
                        zip_buf.seek(0)
                        return StreamingResponse(
                            zip_buf,
                            media_type="application/zip",
                            headers={
                                "Content-Disposition": f'attachment; filename="{filename}.zip"',
                                "X-Export-Summary": quote(summary),
                            },
                        )
                    # Single month — period_end is date_to
                    ym_single = date_from[:7]
                    content = write_slsp_dat(
                        aggregate_by_tin(merged),
                        report_type=slsp_type,
                        filing_tin=filing_tin,
                        period_end=date_to,
                        company=company_dict,
                    )
                    return StreamingResponse(
                        io.BytesIO(content.encode("cp1252", errors="replace")),
                        media_type="application/octet-stream",
                        headers={
                            "Content-Disposition": f'attachment; filename="{_slsp_dat_filename(ym_single)}"',
                            "X-Export-Summary": quote(summary),
                        },
                    )
                buf = io.BytesIO()
                write_slsp_xlsx(merged, buf, report_type=slsp_type)
                buf.seek(0)
                return StreamingResponse(
                    buf,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}.xlsx"',
                        "X-Export-Summary": quote(summary),
                    },
                )

            elif report_type == "qap":
                bills = fetch_posted_bills(conn, ["in_invoice", "in_refund"], date_from, date_to)
                jes = fetch_journal_entries_with_wht(conn, date_from, date_to)
                _all_qap_pids = set()
                for _m in bills + jes:
                    _pid = _m.get("partner_id")
                    if _pid:
                        _all_qap_pids.add(_pid[0] if isinstance(_pid, list) else _pid)
                qap_partners = fetch_partners_by_ids(conn, list(_all_qap_pids))
                bill_rows = _extract_qap_rows(conn, bills, "bill", qap_partners)
                je_rows = _extract_qap_rows(conn, jes, "journal_entry", qap_partners)
                merged = build_qap_rows(bill_rows, je_rows)

                summary = f"{len(bill_rows)} bills + {len(je_rows)} journal entries = {len(merged)} total"
                filename = f"QAP_{date_from}_to_{date_to}_{safe_db}"

                if format == "dat":
                    # BIR filename: <TIN><BC><MMYYYY><FormType>.DAT  e.g. 005302695000003202 61601EQ.DAT
                    qap_year, qap_month = date_to[:4], date_to[5:7]
                    qap_dat_name = f"{filing_tin}{branch_code}{qap_month}{qap_year}1601EQ.DAT"
                    content = write_qap_dat(
                        merged,
                        company=company_dict,
                        period_end=date_to,
                    )
                    return StreamingResponse(
                        io.BytesIO(content.encode("cp1252", errors="replace")),
                        media_type="application/octet-stream",
                        headers={
                            "Content-Disposition": f'attachment; filename="{qap_dat_name}"',
                            "X-Export-Summary": quote(summary),
                        },
                    )
                buf = io.BytesIO()
                write_qap_xlsx(merged, buf)
                buf.seek(0)
                return StreamingResponse(
                    buf,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}.xlsx"',
                        "X-Export-Summary": quote(summary),
                    },
                )

            return JSONResponse({"detail": f"Unknown report type: {report_type}"}, status_code=400)

        except Exception:
            log.exception("Export failed for db=%s report=%s", db_name, report_type)
            return JSONResponse({"detail": "Export failed — check server logs"}, status_code=500)


@app.post("/{token}/ebirforms/generate")
def ebirforms_generate(
    token: str,
    form_number: str = Form(...),
    db_name: str = Form(...),
    company_id: int = Form(0),
    date_from: str = Form(...),
    date_to: str = Form(...),
):
    """Generate an eBIRForms XML file for a specific form and client."""
    err = _check_token(token)
    if err:
        return err

    from ebirforms.base import TaxpayerInfo
    from ebirforms.builder import build_form_xml, build_savefile_name
    from ebirforms.profile import build_profile_content, profile_filename

    clients = _load_clients()
    client = next((c for c in clients if c["db"] == db_name), None)
    if not client:
        raise HTTPException(404, f"Client database not found: {db_name}")

    conn = connect(client["url"], client["db"], client["user"], client["api_key"], company_id=company_id or None)

    company = fetch_company_profile(conn)
    vat = company.get("vat") or ""
    branch = company.get("branch_code") or "000"
    tin_raw = vat.replace("-", "").replace(" ", "")
    tin12 = f"{tin_raw}{branch}".ljust(12, "0")[:12]
    tin_formatted = f"{tin_raw[:3]}-{tin_raw[3:6]}-{tin_raw[6:9]}-{branch}"

    lob = client.get("line_of_business", "")
    taxpayer = TaxpayerInfo(
        tin=tin_formatted,
        rdo_code=company.get("l10n_ph_rdo") or "",
        name=company.get("name", ""),
        trade_name=company.get("name", ""),
        address=_build_address(company),
        zip_code=company.get("zip") or "",
        telephone=company.get("phone") or "",
        email=company.get("email") or "",
        line_of_business=lob,
    )

    import calendar as _cal

    EWT_FORMS = {"0619E", "0619F", "1601EQ", "1601FQ"}
    VAT_FORMS = {"2550M", "2550Q"}
    INCOME_FORMS = {"1702Q", "1702RT", "1702EX", "1702MX"}
    QUARTERLY_EWT_FORMS = {"1601EQ", "1601FQ"}

    with get_semaphore(db_name):
        monthly_totals = None

        if form_number in VAT_FORMS:
            raw_data = fetch_vat_summary(conn, date_from, date_to)
        elif form_number in INCOME_FORMS:
            raw_data = fetch_income_statement(conn, date_from, date_to)
        elif form_number in EWT_FORMS:
            raw_data = fetch_tax_lines_by_atc(conn, date_from, date_to)
            if form_number in QUARTERLY_EWT_FORMS:
                start_month = int(date_from[5:7])
                yr = int(date_from[:4])
                monthly_totals = []
                for m in range(start_month, start_month + 3):
                    m_start = f"{yr}-{m:02d}-01"
                    m_end = f"{yr}-{m:02d}-{_cal.monthrange(yr, m)[1]:02d}"
                    monthly_totals.append(fetch_tax_lines_by_atc(conn, m_start, m_end))
        else:
            raw_data = {}

    xml_content = build_form_xml(
        form_number, taxpayer, raw_data, date_from, date_to,
        monthly_raw=monthly_totals,
    )
    profile_content = build_profile_content(taxpayer)

    savefile_name = build_savefile_name(tin12, form_number, date_from, date_to)
    prof_name = profile_filename(taxpayer)

    return JSONResponse(
        {
            "savefile": {
                "name": savefile_name,
                "content": xml_content,
                "path": f"C:\\eBIRForms\\savefile\\{savefile_name}",
            },
            "profile": {"name": prof_name, "content": profile_content, "path": f"C:\\eBIRForms\\profile\\{prof_name}"},
            "warnings": _collect_warnings(company, taxpayer),
        }
    )


def _build_address(company: dict) -> str:
    """Build address string from Odoo company fields."""
    parts = [company.get("street") or "", company.get("street2") or "", company.get("city") or ""]
    return " ".join(p for p in parts if p).strip()


def _collect_warnings(company: dict, taxpayer) -> list[str]:
    """Collect data quality warnings."""
    warnings = []
    if not company.get("vat"):
        warnings.append("TIN not set in client Odoo. Set it in Settings > Companies.")
    if not company.get("l10n_ph_rdo"):
        warnings.append("RDO code not set. Set l10n_ph_rdo in Settings > Companies.")
    if not taxpayer.line_of_business:
        warnings.append("Line of business not set. Set x_studio_line_of_business in proseso-ventures.")
    return warnings


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
