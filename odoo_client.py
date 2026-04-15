# odoo_client.py
"""Odoo XML-RPC client for fetching SLSP and QAP data.

All Odoo interaction is encapsulated here. No formatting or
file-writing logic — that belongs in the builder modules.
"""

from __future__ import annotations

import logging
import threading
import xmlrpc.client
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

# Per-database semaphore — limits concurrent XML-RPC calls to same Odoo instance
_db_semaphores: dict[str, threading.Semaphore] = {}
_semaphore_lock = threading.Lock()

# Company list cache — populated on first request per DB, lives for container lifetime
_company_cache: dict[str, list[dict]] = {}
_cache_lock = threading.Lock()


def get_semaphore(db: str) -> threading.Semaphore:
    """Return (or create) a per-DB semaphore limiting to 3 concurrent requests."""
    if db not in _db_semaphores:
        with _semaphore_lock:
            if db not in _db_semaphores:
                _db_semaphores[db] = threading.Semaphore(3)
    return _db_semaphores[db]


@dataclass
class OdooConnection:
    url: str
    db: str
    uid: int
    api_key: str
    models: xmlrpc.client.ServerProxy
    company_id: int | None = field(default=None)


def connect(url: str, db: str, user: str, api_key: str, company_id: int | None = None) -> OdooConnection:
    """Authenticate and return a ready-to-use connection."""
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    try:
        uid = common.authenticate(db, user, api_key, {})
    except xmlrpc.client.Fault as e:
        raise ConnectionError(f"Odoo auth failed for {db}: {e.faultString[:200]}") from e
    if not uid:
        raise ConnectionError(f"Odoo auth returned uid=0 for {db} — check credentials")
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    return OdooConnection(url=url, db=db, uid=uid, api_key=api_key, models=models, company_id=company_id)


def _execute(conn: OdooConnection, model: str, method: str, args: list, call_kwargs: dict | None = None):
    """Shorthand for execute_kw. Automatically injects company context if set."""
    kw = dict(call_kwargs or {})
    if conn.company_id:
        ctx = dict(kw.get("context", {}))
        ctx["allowed_company_ids"] = [conn.company_id]
        kw["context"] = ctx
    return conn.models.execute_kw(conn.db, conn.uid, conn.api_key, model, method, args, kw)


def fetch_posted_bills(
    conn: OdooConnection,
    move_types: list[str],
    date_from: str,
    date_to: str,
) -> list[dict]:
    """Fetch posted invoices/bills/refunds within date range."""
    domain = [
        ("move_type", "in", move_types),
        ("state", "=", "posted"),
        ("date", ">=", date_from),
        ("date", "<=", date_to),
    ]
    fields = [
        "name",
        "date",
        "ref",
        "partner_id",
        "amount_total",
        "amount_untaxed",
        "line_ids",
    ]
    return _execute(conn, "account.move", "search_read", [domain], {"fields": fields})


def fetch_bill_lines_with_tax(conn: OdooConnection, move_id: int) -> list[dict]:
    """Fetch move lines that have taxes applied, for a given move."""
    domain = [
        ("move_id", "=", move_id),
        ("tax_ids", "!=", False),
        ("display_type", "=", "product"),
    ]
    fields = [
        "name",
        "debit",
        "credit",
        "partner_id",
        "account_id",
        "tax_ids",
        "price_subtotal",
    ]
    return _execute(conn, "account.move.line", "search_read", [domain], {"fields": fields})


def fetch_tax_details(conn: OdooConnection, tax_ids: list[int]) -> list[dict]:
    """Read tax records to get ATC code and rate."""
    if not tax_ids:
        return []
    fields = ["name", "amount", "l10n_ph_atc", "type_tax_use"]
    return _execute(conn, "account.tax", "read", [tax_ids], {"fields": fields})


def fetch_tax_lines_by_atc(conn: OdooConnection, date_from: str, date_to: str) -> list[dict]:
    """Fetch all posted AML tax lines that have a PH ATC code in the period.

    Returns list of dicts with: atc_code, tax_rate, tax_name, tax_base, tax_amount.
    """
    amls = _execute(
        conn,
        "account.move.line",
        "search_read",
        [
            [
                ("move_id.state", "=", "posted"),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
                ("tax_line_id", "!=", False),
            ],
        ],
        {"fields": ["tax_line_id", "tax_base_amount", "debit", "credit", "balance"]},
    )

    if not amls:
        return []

    tax_ids = list({aml["tax_line_id"][0] for aml in amls})
    taxes = _execute(
        conn,
        "account.tax",
        "read",
        [tax_ids],
        {
            "fields": ["l10n_ph_atc", "amount", "name"],
        },
    )
    tax_map = {t["id"]: t for t in taxes}

    result = []
    for aml in amls:
        tax_id = aml["tax_line_id"][0]
        tax = tax_map.get(tax_id, {})
        atc = tax.get("l10n_ph_atc")
        if not atc:
            continue
        result.append(
            {
                "atc_code": atc,
                "tax_rate": abs(tax.get("amount", 0)),
                "tax_name": tax.get("name", ""),
                "tax_base": aml["tax_base_amount"],
                "tax_amount": abs(aml["balance"]),
            }
        )
    return result


def fetch_journal_entries_with_wht(
    conn: OdooConnection,
    date_from: str,
    date_to: str,
) -> list[dict]:
    """Fetch posted JEs that have PH withholding taxes on their lines."""
    domain = [
        ("move_type", "=", "entry"),
        ("state", "=", "posted"),
        ("date", ">=", date_from),
        ("date", "<=", date_to),
        ("line_ids.tax_ids.l10n_ph_atc", "!=", False),
    ]
    fields = ["name", "date", "ref", "partner_id", "line_ids"]
    moves = _execute(conn, "account.move", "search_read", [domain], {"fields": fields})

    enriched = []
    for move in moves:
        lines = fetch_bill_lines_with_tax(conn, move["id"])
        for line in lines:
            line["tax_details"] = fetch_tax_details(conn, line.get("tax_ids", []))
        move["enriched_lines"] = lines
        enriched.append(move)

    return enriched


def fetch_partner_details(conn: OdooConnection, partner_id: int) -> dict:
    """Get TIN, name parts, and address for a partner."""
    fields = [
        "name",
        "vat",
        "first_name",
        "middle_name",
        "last_name",
        "street",
        "city",
    ]
    result = _execute(conn, "res.partner", "read", [[partner_id]], {"fields": fields})
    return result[0] if result else {}


def fetch_partners_by_ids(conn: OdooConnection, partner_ids: list[int]) -> dict[int, dict]:
    """Fetch multiple partners at once. Returns {id: partner_dict}."""
    if not partner_ids:
        return {}
    fields = ["id", "vat", "name", "last_name", "first_name", "middle_name", "street", "city"]
    results = _execute(conn, "res.partner", "read", [partner_ids], {"fields": fields})
    return {r["id"]: r for r in results}


def classify_purchase(conn: OdooConnection, account_id: int) -> str:
    """Map an account to SLSP purchase category based on account code prefix."""
    result = _execute(conn, "account.account", "read", [[account_id]], {"fields": ["code"]})
    code = result[0].get("code") or "" if result else ""
    if code.startswith("1"):
        return "capital_goods"
    elif code.startswith("6"):
        return "services"
    return "other_than_capital_goods"


def fetch_company_profile(conn: OdooConnection) -> dict:
    """Fetch the company's BIR profile data for eBIRForms.

    Returns dict with: name, vat, branch_code, l10n_ph_rdo, street, city, zip, phone, email.
    """
    companies = _execute(
        conn,
        "res.company",
        "search_read",
        [
            [("id", "=", conn.company_id)] if conn.company_id else [],
        ],
        {
            "fields": [
                "name",
                "vat",
                "branch_code",
                "l10n_ph_rdo",
                "street",
                "street2",
                "city",
                "zip",
                "phone",
                "email",
            ],
            "limit": 1,
        },
    )
    if not companies:
        raise ValueError("No company found")
    return companies[0]


def fetch_companies(conn: OdooConnection) -> list[dict]:
    """Fetch all companies accessible to the authenticated user."""
    fields = ["id", "name", "vat", "street", "city", "l10n_ph_rdo", "fiscalyear_last_month"]
    return _execute(conn, "res.company", "search_read", [[]], {"fields": fields})


def get_companies(conn: OdooConnection) -> list[dict]:
    """Cached fetch_companies — populated on first call, lives for container lifetime."""
    if conn.db not in _company_cache:
        with _cache_lock:
            if conn.db not in _company_cache:
                _company_cache[conn.db] = fetch_companies(conn)
    return _company_cache[conn.db]


def fetch_client_tasks(conn: OdooConnection) -> list[dict]:
    """Query project.task records from source Odoo to get target client databases.

    Returns list of dicts: {"name", "url", "db", "user", "api_key"}
    Includes any task that has accounting database, email, and API key populated.
    """
    fields = [
        "id",
        "project_id",
        "x_studio_accounting_database",
        "x_studio_email",
        "x_studio_api_key",
        "x_studio_line_of_business",
    ]
    domain = [
        ["x_studio_accounting_database", "!=", False],
        ["x_studio_email", "!=", False],
        ["x_studio_api_key", "!=", False],
    ]
    tasks = _execute(conn, "project.task", "search_read", [domain], {"fields": fields})
    clients = []
    for task in tasks:
        db_val = (task.get("x_studio_accounting_database") or "").strip()
        email = (task.get("x_studio_email") or "").strip()
        api_key = (task.get("x_studio_api_key") or "").strip()
        if not db_val or not email or not api_key:
            continue
        if db_val.startswith("http"):
            url = db_val.rstrip("/")
            # extract db name from subdomain: https://my-db.odoo.com -> my-db
            db = url.split("//")[-1].split(".")[0]
        else:
            db = db_val
            url = f"https://{db}.odoo.com"
        name_val = task.get("project_id")
        name = name_val[1] if isinstance(name_val, list) and len(name_val) > 1 else db
        lob = (task.get("x_studio_line_of_business") or "").strip()
        clients.append({"name": name, "url": url, "db": db, "user": email, "api_key": api_key, "line_of_business": lob})
    return clients
