from __future__ import annotations

import argparse
import base64
import calendar
import hashlib
import html
import json
import secrets
import sqlite3
import subprocess
from datetime import date, datetime, timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


import os

BACKEND_DIR = Path(__file__).resolve().parent
APP_ROOT = BACKEND_DIR.parent

# create folders automatically
(APP_ROOT / "database").mkdir(parents=True, exist_ok=True)
(APP_ROOT / "exports" / "generated_pdfs").mkdir(parents=True, exist_ok=True)

HTML_DIR = APP_ROOT / "frontend" / "html"
CSS_DIR = APP_ROOT / "frontend" / "css"
JS_DIR = APP_ROOT / "frontend" / "js"
ASSETS_DIR = APP_ROOT / "assets"

DATABASE_PATH = APP_ROOT / "database" / "quotations.db"
HR_DATABASE_PATH = APP_ROOT / "database" / "hr.db"
PDF_EXPORT_DIR = APP_ROOT / "exports" / "generated_pdfs"

HOST = "0.0.0.0"
import os
PORT = int(os.environ.get("PORT", 8765))


SESSION_COOKIE = "avc_session"
SESSION_TTL_HOURS = 12
SESSIONS: dict[str, dict[str, object]] = {}
EDGE_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]


DEFAULT_TERMS = (
    "Validity: This quotation is valid for 60 days from the date of issue.\n"
    "Delivery: Delivery schedule shall be as per Purchase Order (PO).\n"
    "Payment Terms: Payment shall be as per mutually agreed Purchase Order conditions.\n"
    "Taxes: GST, if applicable, shall be charged extra as per prevailing government regulations.\n"
    "Warranty: Warranty shall be as per the terms agreed in the Purchase Order.\n"
    "Confidentiality: The information contained in this quotation shall be confidential and shall not be disclosed to any third party without written consent."
)


DEFAULT_ITEMS = [
    {
        "description": "Aerospace and defence reliability engineering, review and technical advisory support",
        "sac": "Add SAC",
        "qty": 1,
        "rate": 18000,
        "tax": 18,
    },
    {
        "description": "ETO sterilizer validation and documentation support",
        "sac": "Add SAC",
        "qty": 1,
        "rate": 6500,
        "tax": 18,
    },
    {
        "description": "PLC, SCADA and HMI configuration / commissioning support",
        "sac": "Add SAC",
        "qty": 1,
        "rate": 12000,
        "tax": 18,
    },
    {
        "description": "Autoclave preventive maintenance, inspection and service support",
        "sac": "Add SAC",
        "qty": 1,
        "rate": 4500,
        "tax": 18,
    },
    {
        "description": "Custom requirement / special item / materials used as per customer demand",
        "sac": "Add SAC",
        "qty": 1,
        "rate": 0,
        "tax": 18,
    },
]


DEFAULT_QUOTE = {
    "id": None,
    "base_quote_number": "",
    "revision_number": 0,
    "display_number": "",
    "status": "DRAFT",
    "company_name": "AstroVolt Global LLP",
    "tagline": "Aerospace & Defence | Healthcare Sterilization | Industrial Automation",
    "company_address": "#7/31, 2nd Main Road, Domlur Layout, Bengaluru-560071.",
    "company_mobile": "+91 00000 00000",
    "company_email": "support@astrovoltglobal.com",
    "company_website": "www.astrovoltglobal.com",
    "company_gstin": "Add GST number",
    "company_pan": "ACNFA6723D",
    "company_tan": "BLRA60131B",
    "customer_name": "",
    "customer_contact": "",
    "customer_address": "",
    "customer_mobile": "",
    "customer_gstin": "",
    "quote_date": "",
    "valid_until": "",
    "reference": "Engineering systems supply, service, and customer-specific technical support",
    "payment_terms": "Payment shall be as per mutually agreed Purchase Order conditions.",
    "notes": DEFAULT_TERMS,
    "bank_account_name": "AstroVolt Global LLP",
    "bank_name": "Add bank name here",
    "bank_account_number": "000000000000",
    "bank_ifsc": "ABCD0000000",
    "bank_upi": "",
    "signatory_name": "Authorised Person",
    "signatory_designation": "Partner / Manager",
    "items": DEFAULT_ITEMS,
}

DEFAULT_INVOICE = json.loads(json.dumps(DEFAULT_QUOTE))


def utc_now_text() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def today_text() -> str:
    return date.today().isoformat()


def plus_days(date_text: str, days: int) -> str:
    base = date.fromisoformat(date_text) if date_text else date.today()
    return (base + timedelta(days=days)).isoformat()


def quote_display_number(base_quote_number: str, revision_number: int) -> str:
    return base_quote_number if revision_number == 0 else f"{base_quote_number}-R{revision_number}"


def to_float(value: object) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def db_connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def db_connect_hr() -> sqlite3.Connection:
    connection = sqlite3.connect(HR_DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    init_quotes_db()
    init_hr_db()


def init_quotes_db() -> None:
    with db_connect() as connection:
        connection.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base_quote_number TEXT NOT NULL,
                revision_number INTEGER NOT NULL DEFAULT 0,
                display_number TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('DRAFT', 'FINAL', 'CANCELLED')),
                is_locked INTEGER NOT NULL DEFAULT 0 CHECK (is_locked IN (0, 1)),
                company_name TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                quote_date TEXT NOT NULL,
                valid_until TEXT NOT NULL,
                subtotal REAL NOT NULL DEFAULT 0,
                cgst REAL NOT NULL DEFAULT 0,
                sgst REAL NOT NULL DEFAULT 0,
                grand_total REAL NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL,
                html_snapshot TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                finalised_at TEXT,
                parent_quote_id INTEGER,
                FOREIGN KEY(parent_quote_id) REFERENCES quotations(id)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS quotations_unique_revision
            ON quotations(base_quote_number, revision_number);

            CREATE INDEX IF NOT EXISTS quotations_updated_idx
            ON quotations(updated_at DESC);

            CREATE INDEX IF NOT EXISTS quotations_customer_idx
            ON quotations(customer_name);

            CREATE TABLE IF NOT EXISTS quotation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quotation_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(quotation_id) REFERENCES quotations(id)
            );

            CREATE TRIGGER IF NOT EXISTS protect_locked_quotation_update
            BEFORE UPDATE ON quotations
            WHEN OLD.is_locked = 1
            BEGIN
                SELECT RAISE(ABORT, 'Locked quotation cannot be modified');
            END;

            CREATE TRIGGER IF NOT EXISTS protect_locked_quotation_delete
            BEFORE DELETE ON quotations
            WHEN OLD.is_locked = 1
            BEGIN
                SELECT RAISE(ABORT, 'Locked quotation cannot be deleted');
            END;

            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base_invoice_number TEXT NOT NULL,
                revision_number INTEGER NOT NULL DEFAULT 0,
                display_number TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('DRAFT', 'FINAL', 'CANCELLED')),
                is_locked INTEGER NOT NULL DEFAULT 0 CHECK (is_locked IN (0, 1)),
                company_name TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                subtotal REAL NOT NULL DEFAULT 0,
                cgst REAL NOT NULL DEFAULT 0,
                sgst REAL NOT NULL DEFAULT 0,
                grand_total REAL NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL,
                html_snapshot TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                finalised_at TEXT,
                parent_invoice_id INTEGER,
                FOREIGN KEY(parent_invoice_id) REFERENCES invoices(id)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS invoices_unique_revision
            ON invoices(base_invoice_number, revision_number);

            CREATE INDEX IF NOT EXISTS invoices_updated_idx
            ON invoices(updated_at DESC);

            CREATE INDEX IF NOT EXISTS invoices_customer_idx
            ON invoices(customer_name);

            CREATE TABLE IF NOT EXISTS invoice_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id)
            );

            CREATE TRIGGER IF NOT EXISTS protect_locked_invoice_update
            BEFORE UPDATE ON invoices
            WHEN OLD.is_locked = 1
            BEGIN
                SELECT RAISE(ABORT, 'Locked invoice cannot be modified');
            END;

            CREATE TRIGGER IF NOT EXISTS protect_locked_invoice_delete
            BEFORE DELETE ON invoices
            WHEN OLD.is_locked = 1
            BEGIN
                SELECT RAISE(ABORT, 'Locked invoice cannot be deleted');
            END;
            """
        )


def init_hr_db() -> None:
    with db_connect_hr() as connection:
        connection.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_code TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                dob TEXT,
                gender TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                doj TEXT,
                department TEXT,
                designation TEXT,
                employment_type TEXT,
                status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'RESIGNED')),
                base_salary REAL NOT NULL DEFAULT 0,
                allowances REAL NOT NULL DEFAULT 0,
                pf_percent REAL NOT NULL DEFAULT 0,
                esi_percent REAL NOT NULL DEFAULT 0,
                overtime_rate REAL NOT NULL DEFAULT 0,
                pf_mode TEXT NOT NULL DEFAULT 'PERCENT' CHECK (pf_mode IN ('PERCENT', 'FIXED')),
                pf_fixed REAL NOT NULL DEFAULT 1800,
                bank_name TEXT,
                bank_account TEXT,
                bank_ifsc TEXT,
                emergency_contact_name TEXT,
                emergency_contact_phone TEXT,
                leave_balance REAL NOT NULL DEFAULT 0,
                week_off TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                work_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('PRESENT', 'ABSENT', 'HALF_DAY', 'LEAVE', 'HOLIDAY', 'WEEK_OFF', 'LWP')),
                overtime_hours REAL NOT NULL DEFAULT 0,
                note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(employee_id, work_date),
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            );

            CREATE TABLE IF NOT EXISTS salary_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                month TEXT NOT NULL,
                days_in_month INTEGER NOT NULL,
                present_days REAL NOT NULL,
                absent_days REAL NOT NULL,
                half_days REAL NOT NULL,
                overtime_hours REAL NOT NULL,
                base_salary REAL NOT NULL,
                allowances REAL NOT NULL,
                overtime_amount REAL NOT NULL,
                lop_amount REAL NOT NULL,
                pf_amount REAL NOT NULL,
                esi_amount REAL NOT NULL,
                other_deductions REAL NOT NULL,
                advance REAL NOT NULL,
                net_pay REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(employee_id, month),
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            );

            CREATE TABLE IF NOT EXISTS holidays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                holiday_date TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )

        ensure_employee_columns(connection)
        ensure_attendance_schema(connection)
        migrate_hr_from_quotes(connection)


def migrate_hr_from_quotes(connection: sqlite3.Connection) -> None:
    has_rows = connection.execute("SELECT COUNT(*) AS total FROM employees").fetchone()["total"]
    if has_rows:
        return
    connection.execute("ATTACH DATABASE ? AS qdb", (str(DATABASE_PATH),))
    try:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM qdb.sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for table in ["employees", "attendance", "salary_runs", "holidays"]:
            if table not in tables:
                continue
            cols = [
                row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
            ]
            q_cols = [
                row["name"] for row in connection.execute(f"PRAGMA qdb.table_info({table})").fetchall()
            ]
            common = [col for col in cols if col in q_cols]
            if not common:
                continue
            columns = ", ".join(common)
            connection.execute(
                f"INSERT OR IGNORE INTO {table} ({columns}) SELECT {columns} FROM qdb.{table}"
            )
        connection.commit()
    finally:
        connection.execute("DETACH DATABASE qdb")


def ensure_employee_columns(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(employees)").fetchall()}
    if "leave_balance" not in columns:
        connection.execute("ALTER TABLE employees ADD COLUMN leave_balance REAL NOT NULL DEFAULT 0")
    if "week_off" not in columns:
        connection.execute("ALTER TABLE employees ADD COLUMN week_off TEXT NOT NULL DEFAULT '[]'")
    if "pf_mode" not in columns:
        connection.execute("ALTER TABLE employees ADD COLUMN pf_mode TEXT NOT NULL DEFAULT 'PERCENT'")
    if "pf_fixed" not in columns:
        connection.execute("ALTER TABLE employees ADD COLUMN pf_fixed REAL NOT NULL DEFAULT 1800")


def ensure_attendance_schema(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance'"
    ).fetchone()
    if not row:
        return
    sql = row["sql"] or ""
    if "WEEK_OFF" in sql and "HOLIDAY" in sql and "LEAVE" in sql and "LWP" in sql:
        return

    connection.executescript(
        """
        ALTER TABLE attendance RENAME TO attendance_old;

        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('PRESENT', 'ABSENT', 'HALF_DAY', 'LEAVE', 'HOLIDAY', 'WEEK_OFF', 'LWP')),
            overtime_hours REAL NOT NULL DEFAULT 0,
            note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(employee_id, work_date),
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );

        INSERT INTO attendance(id, employee_id, work_date, status, overtime_hours, note, created_at, updated_at)
        SELECT id, employee_id, work_date, status, overtime_hours, note, created_at, updated_at
        FROM attendance_old;

        DROP TABLE attendance_old;
        """
    )


def get_setting(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        """
        INSERT INTO settings(key, value)
        VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def pin_configured(connection: sqlite3.Connection) -> bool:
    return bool(get_setting(connection, "admin_pin_hash") and get_setting(connection, "admin_pin_salt"))


def hash_pin(pin: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        bytes.fromhex(salt_hex),
        200_000,
    ).hex()


def set_admin_pin(connection: sqlite3.Connection, new_pin: str) -> None:
    salt_hex = secrets.token_hex(16)
    set_setting(connection, "admin_pin_salt", salt_hex)
    set_setting(connection, "admin_pin_hash", hash_pin(new_pin, salt_hex))


def verify_admin_pin(connection: sqlite3.Connection, pin: str) -> bool:
    salt_hex = get_setting(connection, "admin_pin_salt")
    saved_hash = get_setting(connection, "admin_pin_hash")
    if not salt_hex or not saved_hash:
        return False
    return secrets.compare_digest(saved_hash, hash_pin(pin, salt_hex))


def auth_configured(connection: sqlite3.Connection) -> bool:
    return bool(get_setting(connection, "admin_user") and get_setting(connection, "admin_pass_hash"))


def hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        240_000,
    ).hex()


def set_admin_user(connection: sqlite3.Connection, username: str, password: str) -> None:
    salt_hex = secrets.token_hex(16)
    set_setting(connection, "admin_user", username)
    set_setting(connection, "admin_pass_salt", salt_hex)
    set_setting(connection, "admin_pass_hash", hash_password(password, salt_hex))


def verify_admin_user(connection: sqlite3.Connection, username: str, password: str) -> bool:
    saved_user = get_setting(connection, "admin_user")
    salt_hex = get_setting(connection, "admin_pass_salt")
    saved_hash = get_setting(connection, "admin_pass_hash")
    if not saved_user or not salt_hex or not saved_hash:
        return False
    if saved_user != username:
        return False
    return secrets.compare_digest(saved_hash, hash_password(password, salt_hex))


def prune_sessions() -> None:
    now = datetime.utcnow()
    expired = [token for token, info in SESSIONS.items() if info["expires_at"] <= now]
    for token in expired:
        del SESSIONS[token]


def create_session(username: str) -> str:
    prune_sessions()
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {
        "username": username,
        "expires_at": datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS),
    }
    return token


def get_session(token: str | None) -> dict[str, object] | None:
    if not token:
        return None
    prune_sessions()
    return SESSIONS.get(token)


def clear_session(token: str | None) -> None:
    if not token:
        return
    SESSIONS.pop(token, None)


def next_base_quote_number(connection: sqlite3.Connection, quote_date: str | None = None) -> str:
    year = (quote_date or today_text())[:4]
    prefix = f"AVG-{year}-"
    rows = connection.execute(
        "SELECT DISTINCT base_quote_number FROM quotations WHERE base_quote_number LIKE ?",
        (f"{prefix}%",),
    ).fetchall()
    current_max = 0
    for row in rows:
        try:
            current_max = max(current_max, int(row["base_quote_number"].split("-")[-1]))
        except ValueError:
            continue
    return f"{prefix}{current_max + 1:03d}"


def next_base_invoice_number(connection: sqlite3.Connection, invoice_date: str | None = None) -> str:
    year = (invoice_date or today_text())[:4]
    prefix = f"AVG-INV-{year}-"
    rows = connection.execute(
        "SELECT DISTINCT base_invoice_number FROM invoices WHERE base_invoice_number LIKE ?",
        (f"{prefix}%",),
    ).fetchall()
    current_max = 0
    for row in rows:
        try:
            current_max = max(current_max, int(row["base_invoice_number"].split("-")[-1]))
        except ValueError:
            continue
    return f"{prefix}{current_max + 1:03d}"


def money_text(value: float) -> str:
    return f"{value:,.2f}"


def int_words_under_thousand(number: int) -> str:
    ones = [
        "",
        "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Six",
        "Seven",
        "Eight",
        "Nine",
        "Ten",
        "Eleven",
        "Twelve",
        "Thirteen",
        "Fourteen",
        "Fifteen",
        "Sixteen",
        "Seventeen",
        "Eighteen",
        "Nineteen",
    ]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    parts: list[str] = []
    hundred = number // 100
    rest = number % 100
    if hundred:
        parts.append(f"{ones[hundred]} Hundred")
    if rest:
        if rest < 20:
            parts.append(ones[rest])
        else:
            tens_part = tens[rest // 10]
            ones_part = ones[rest % 10]
            parts.append((tens_part + " " + ones_part).strip())
    return " ".join(parts).strip()


def number_to_words(value: float) -> str:
    whole = int(value)
    paise = int(round((value - whole) * 100))
    if whole == 0:
        words = "Zero"
    else:
        crore = whole // 10_000_000
        lakh = (whole % 10_000_000) // 100_000
        thousand = (whole % 100_000) // 1_000
        remainder = whole % 1_000
        pieces: list[str] = []
        if crore:
            pieces.append(f"{int_words_under_thousand(crore)} Crore")
        if lakh:
            pieces.append(f"{int_words_under_thousand(lakh)} Lakh")
        if thousand:
            pieces.append(f"{int_words_under_thousand(thousand)} Thousand")
        if remainder:
            pieces.append(int_words_under_thousand(remainder))
        words = " ".join(piece.strip() for piece in pieces if piece.strip())
    if paise:
        return f"{words} and {int_words_under_thousand(paise)} Paise Only"
    return f"{words} Only"


def quote_totals(items: list[dict[str, object]]) -> dict[str, float | str]:
    subtotal = 0.0
    tax_total = 0.0
    for item in items:
        qty = to_float(item.get("qty", 0))
        rate = to_float(item.get("rate", 0))
        tax = to_float(item.get("tax", 0))
        line_total = qty * rate
        line_tax = line_total * tax / 100.0
        subtotal += line_total
        tax_total += line_tax
    cgst = tax_total / 2.0
    sgst = tax_total / 2.0
    grand_total = subtotal + tax_total
    return {
        "subtotal": round(subtotal, 2),
        "cgst": round(cgst, 2),
        "sgst": round(sgst, 2),
        "grand_total": round(grand_total, 2),
        "amount_words": number_to_words(round(grand_total, 2)),
    }


def default_quote_payload(connection: sqlite3.Connection) -> dict[str, object]:
    payload = json.loads(json.dumps(DEFAULT_QUOTE))
    today = today_text()
    payload["quote_date"] = today
    payload["valid_until"] = plus_days(today, 60)
    payload["base_quote_number"] = next_base_quote_number(connection, today)
    payload["display_number"] = payload["base_quote_number"]
    payload["revision_number"] = 0
    payload["status"] = "DRAFT"
    return payload


def default_invoice_payload(connection: sqlite3.Connection) -> dict[str, object]:
    payload = json.loads(json.dumps(DEFAULT_INVOICE))
    today = today_text()
    payload["quote_date"] = today
    payload["valid_until"] = plus_days(today, 60)
    payload["base_quote_number"] = ""
    payload["base_invoice_number"] = next_base_invoice_number(connection, today)
    payload["display_number"] = payload["base_invoice_number"]
    payload["revision_number"] = 0
    payload["status"] = "DRAFT"
    return payload


def clean_text(value: object) -> str:
    return str(value or "").strip()


def normalized_items(items: object) -> list[dict[str, object]]:
    cleaned: list[dict[str, object]] = []
    if not isinstance(items, list):
        return json.loads(json.dumps(DEFAULT_ITEMS))
    for item in items:
        if not isinstance(item, dict):
            continue
        cleaned.append(
            {
                "description": clean_text(item.get("description")),
                "sac": clean_text(item.get("sac")),
                "qty": round(to_float(item.get("qty", 0)), 2),
                "rate": round(to_float(item.get("rate", 0)), 2),
                "tax": round(to_float(item.get("tax", 0)), 2),
            }
        )
    return cleaned


def normalize_payload(payload: dict[str, object], connection: sqlite3.Connection) -> dict[str, object]:
    base_quote_number = clean_text(payload.get("base_quote_number")) or next_base_quote_number(
        connection,
        clean_text(payload.get("quote_date")) or today_text(),
    )
    revision_number = int(to_float(payload.get("revision_number", 0)))
    quote_date = clean_text(payload.get("quote_date")) or today_text()
    valid_until = clean_text(payload.get("valid_until")) or plus_days(quote_date, 60)
    items = normalized_items(payload.get("items", []))
    totals = quote_totals(items)

    normalized = json.loads(json.dumps(DEFAULT_QUOTE))
    normalized.update(
        {
            "id": payload.get("id"),
            "base_quote_number": base_quote_number,
            "revision_number": revision_number,
            "display_number": quote_display_number(base_quote_number, revision_number),
            "status": "DRAFT",
            "company_name": DEFAULT_QUOTE["company_name"],
            "tagline": DEFAULT_QUOTE["tagline"],
            "company_address": DEFAULT_QUOTE["company_address"],
            "company_mobile": clean_text(payload.get("company_mobile")) or DEFAULT_QUOTE["company_mobile"],
            "company_email": DEFAULT_QUOTE["company_email"],
            "company_website": DEFAULT_QUOTE["company_website"],
            "company_gstin": clean_text(payload.get("company_gstin")) or DEFAULT_QUOTE["company_gstin"],
            "company_pan": DEFAULT_QUOTE["company_pan"],
            "company_tan": DEFAULT_QUOTE["company_tan"],
            "customer_name": clean_text(payload.get("customer_name")),
            "customer_contact": clean_text(payload.get("customer_contact")),
            "customer_address": clean_text(payload.get("customer_address")),
            "customer_mobile": clean_text(payload.get("customer_mobile")),
            "customer_gstin": clean_text(payload.get("customer_gstin")),
            "quote_date": quote_date,
            "valid_until": valid_until,
            "reference": clean_text(payload.get("reference")) or DEFAULT_QUOTE["reference"],
            "payment_terms": clean_text(payload.get("payment_terms")) or DEFAULT_QUOTE["payment_terms"],
            "notes": DEFAULT_QUOTE["notes"],
            "bank_account_name": clean_text(payload.get("bank_account_name")) or DEFAULT_QUOTE["bank_account_name"],
            "bank_name": clean_text(payload.get("bank_name")) or DEFAULT_QUOTE["bank_name"],
            "bank_account_number": clean_text(payload.get("bank_account_number")) or DEFAULT_QUOTE["bank_account_number"],
            "bank_ifsc": clean_text(payload.get("bank_ifsc")) or DEFAULT_QUOTE["bank_ifsc"],
            "bank_upi": clean_text(payload.get("bank_upi")) or DEFAULT_QUOTE["bank_upi"],
            "signatory_name": clean_text(payload.get("signatory_name")) or DEFAULT_QUOTE["signatory_name"],
            "signatory_designation": clean_text(payload.get("signatory_designation")) or DEFAULT_QUOTE["signatory_designation"],
            "items": items,
            "totals": totals,
        }
    )
    return normalized


def normalize_invoice_payload(payload: dict[str, object], connection: sqlite3.Connection) -> dict[str, object]:
    base_invoice_number = clean_text(payload.get("base_invoice_number")) or next_base_invoice_number(
        connection,
        clean_text(payload.get("quote_date")) or today_text(),
    )
    revision_number = int(to_float(payload.get("revision_number", 0)))
    invoice_date = clean_text(payload.get("quote_date")) or today_text()
    due_date = clean_text(payload.get("valid_until")) or plus_days(invoice_date, 60)
    items = normalized_items(payload.get("items", []))
    totals = quote_totals(items)

    normalized = json.loads(json.dumps(DEFAULT_INVOICE))
    normalized.update(
        {
            "id": payload.get("id"),
            "base_invoice_number": base_invoice_number,
            "revision_number": revision_number,
            "display_number": quote_display_number(base_invoice_number, revision_number),
            "status": "DRAFT",
            "company_name": DEFAULT_INVOICE["company_name"],
            "tagline": DEFAULT_INVOICE["tagline"],
            "company_address": DEFAULT_INVOICE["company_address"],
            "company_mobile": clean_text(payload.get("company_mobile")) or DEFAULT_INVOICE["company_mobile"],
            "company_email": DEFAULT_INVOICE["company_email"],
            "company_website": DEFAULT_INVOICE["company_website"],
            "company_gstin": clean_text(payload.get("company_gstin")) or DEFAULT_INVOICE["company_gstin"],
            "company_pan": DEFAULT_INVOICE["company_pan"],
            "company_tan": DEFAULT_INVOICE["company_tan"],
            "customer_name": clean_text(payload.get("customer_name")),
            "customer_contact": clean_text(payload.get("customer_contact")),
            "customer_address": clean_text(payload.get("customer_address")),
            "customer_mobile": clean_text(payload.get("customer_mobile")),
            "customer_gstin": clean_text(payload.get("customer_gstin")),
            "quote_date": invoice_date,
            "valid_until": due_date,
            "reference": clean_text(payload.get("reference")) or DEFAULT_INVOICE["reference"],
            "payment_terms": clean_text(payload.get("payment_terms")) or DEFAULT_INVOICE["payment_terms"],
            "notes": DEFAULT_INVOICE["notes"],
            "bank_account_name": clean_text(payload.get("bank_account_name")) or DEFAULT_INVOICE["bank_account_name"],
            "bank_name": clean_text(payload.get("bank_name")) or DEFAULT_INVOICE["bank_name"],
            "bank_account_number": clean_text(payload.get("bank_account_number")) or DEFAULT_INVOICE["bank_account_number"],
            "bank_ifsc": clean_text(payload.get("bank_ifsc")) or DEFAULT_INVOICE["bank_ifsc"],
            "bank_upi": clean_text(payload.get("bank_upi")) or DEFAULT_INVOICE["bank_upi"],
            "signatory_name": clean_text(payload.get("signatory_name")) or DEFAULT_INVOICE["signatory_name"],
            "signatory_designation": clean_text(payload.get("signatory_designation")) or DEFAULT_INVOICE["signatory_designation"],
            "items": items,
            "totals": totals,
        }
    )
    return normalized


def quote_row_to_dict(row: sqlite3.Row, include_payload: bool = False) -> dict[str, object]:
    data = {
        "id": row["id"],
        "base_quote_number": row["base_quote_number"],
        "revision_number": row["revision_number"],
        "display_number": row["display_number"],
        "status": row["status"],
        "is_locked": bool(row["is_locked"]),
        "company_name": row["company_name"],
        "customer_name": row["customer_name"],
        "quote_date": row["quote_date"],
        "valid_until": row["valid_until"],
        "subtotal": row["subtotal"],
        "cgst": row["cgst"],
        "sgst": row["sgst"],
        "grand_total": row["grand_total"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "finalised_at": row["finalised_at"],
        "parent_quote_id": row["parent_quote_id"],
    }
    if include_payload:
        payload = json.loads(row["payload_json"])
        payload["company_name"] = DEFAULT_QUOTE["company_name"]
        payload["tagline"] = DEFAULT_QUOTE["tagline"]
        payload["company_address"] = DEFAULT_QUOTE["company_address"]
        payload["company_email"] = DEFAULT_QUOTE["company_email"]
        payload["company_website"] = DEFAULT_QUOTE["company_website"]
        payload["company_pan"] = DEFAULT_QUOTE["company_pan"]
        payload["company_tan"] = DEFAULT_QUOTE["company_tan"]
        payload["company_mobile"] = clean_text(payload.get("company_mobile")) or DEFAULT_QUOTE["company_mobile"]
        payload["company_gstin"] = clean_text(payload.get("company_gstin")) or DEFAULT_QUOTE["company_gstin"]
        payload["notes"] = DEFAULT_QUOTE["notes"]
        payload["id"] = row["id"]
        payload["status"] = row["status"]
        payload["display_number"] = row["display_number"]
        payload["is_locked"] = bool(row["is_locked"])
        data["quotation"] = payload
        data["html_snapshot"] = row["html_snapshot"]
    return data


def invoice_row_to_dict(row: sqlite3.Row, include_payload: bool = False) -> dict[str, object]:
    data = {
        "id": row["id"],
        "base_invoice_number": row["base_invoice_number"],
        "revision_number": row["revision_number"],
        "display_number": row["display_number"],
        "status": row["status"],
        "is_locked": bool(row["is_locked"]),
        "company_name": row["company_name"],
        "customer_name": row["customer_name"],
        "invoice_date": row["invoice_date"],
        "due_date": row["due_date"],
        "quote_date": row["invoice_date"],
        "valid_until": row["due_date"],
        "subtotal": row["subtotal"],
        "cgst": row["cgst"],
        "sgst": row["sgst"],
        "grand_total": row["grand_total"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "finalised_at": row["finalised_at"],
        "parent_invoice_id": row["parent_invoice_id"],
    }
    if include_payload:
        payload = json.loads(row["payload_json"])
        payload["company_name"] = DEFAULT_INVOICE["company_name"]
        payload["tagline"] = DEFAULT_INVOICE["tagline"]
        payload["company_address"] = DEFAULT_INVOICE["company_address"]
        payload["company_email"] = DEFAULT_INVOICE["company_email"]
        payload["company_website"] = DEFAULT_INVOICE["company_website"]
        payload["company_pan"] = DEFAULT_INVOICE["company_pan"]
        payload["company_tan"] = DEFAULT_INVOICE["company_tan"]
        payload["company_mobile"] = clean_text(payload.get("company_mobile")) or DEFAULT_INVOICE["company_mobile"]
        payload["company_gstin"] = clean_text(payload.get("company_gstin")) or DEFAULT_INVOICE["company_gstin"]
        payload["notes"] = DEFAULT_INVOICE["notes"]
        payload["id"] = row["id"]
        payload["status"] = row["status"]
        payload["display_number"] = row["display_number"]
        payload["is_locked"] = bool(row["is_locked"])
        data["invoice"] = payload
    return data


def quote_summary(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT id, base_quote_number, revision_number, display_number, status, is_locked,
               company_name, customer_name, quote_date, valid_until,
               subtotal, cgst, sgst, grand_total,
               created_at, updated_at, finalised_at, parent_quote_id
        FROM quotations
        ORDER BY updated_at DESC, id DESC
        """
    ).fetchall()
    return [quote_row_to_dict(row, include_payload=False) for row in rows]


def invoice_summary(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT id, base_invoice_number, revision_number, display_number, status, is_locked,
               company_name, customer_name, invoice_date, due_date,
               subtotal, cgst, sgst, grand_total,
               created_at, updated_at, finalised_at, parent_invoice_id
        FROM invoices
        ORDER BY updated_at DESC, id DESC
        """
    ).fetchall()
    return [invoice_row_to_dict(row, include_payload=False) for row in rows]


def get_quote(connection: sqlite3.Connection, quote_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT id, base_quote_number, revision_number, display_number, status, is_locked,
               company_name, customer_name, quote_date, valid_until,
               subtotal, cgst, sgst, grand_total,
               payload_json, html_snapshot,
               created_at, updated_at, finalised_at, parent_quote_id
        FROM quotations
        WHERE id = ?
        """,
        (quote_id,),
    ).fetchone()


def get_invoice(connection: sqlite3.Connection, invoice_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT id, base_invoice_number, revision_number, display_number, status, is_locked,
               company_name, customer_name, invoice_date, due_date,
               subtotal, cgst, sgst, grand_total,
               payload_json, html_snapshot,
               created_at, updated_at, finalised_at, parent_invoice_id
        FROM invoices
        WHERE id = ?
        """,
        (invoice_id,),
    ).fetchone()


def record_event(connection: sqlite3.Connection, quotation_id: int, action: str, note: str = "") -> None:
    connection.execute(
        """
        INSERT INTO quotation_events(quotation_id, action, note, created_at)
        VALUES(?, ?, ?, ?)
        """,
        (quotation_id, action, note, utc_now_text()),
    )


def record_invoice_event(connection: sqlite3.Connection, invoice_id: int, action: str, note: str = "") -> None:
    connection.execute(
        """
        INSERT INTO invoice_events(invoice_id, action, note, created_at)
        VALUES(?, ?, ?, ?)
        """,
        (invoice_id, action, note, utc_now_text()),
    )


def line_totals(item: dict[str, object]) -> tuple[float, float]:
    qty = to_float(item.get("qty"))
    rate = to_float(item.get("rate"))
    tax = to_float(item.get("tax"))
    amount = qty * rate
    line_tax = amount * tax / 100.0
    return round(amount, 2), round(line_tax, 2)


def safe_filename(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in ("-", "_", ".") else "_" for char in clean_text(value))
    return cleaned.strip("._") or "quotation"


def preferred_browser_path() -> Path | None:
    for candidate in EDGE_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def logo_data_uri() -> str:
    logo_path = ASSETS_DIR / "logo.png"
    if not logo_path.exists():
        return ""
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def html_multiline(value: object) -> str:
    return "<br>".join(html.escape(line) for line in clean_text(value).splitlines() if line.strip()) or "&nbsp;"


def note_sections(value: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    for raw_line in clean_text(value).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line:
            title, body = line.split(":", 1)
            sections.append((title.strip(), body.strip()))
        else:
            sections.append(("Note", line))
    return sections


def quote_document_html(payload: dict[str, object]) -> str:
    totals = payload["totals"]
    items_html: list[str] = []
    for index, item in enumerate(payload["items"], start=1):
        amount, line_tax = line_totals(item)
        line_total = amount + line_tax
        items_html.append(
            "<tr>"
            f"<td class='text-center'>{index}</td>"
            f"<td>{html.escape(clean_text(item.get('description')))}</td>"
            f"<td>{html.escape(clean_text(item.get('sac')))}</td>"
            f"<td class='text-right'>{html.escape(str(item.get('qty')))}</td>"
            f"<td class='text-right'>{money_text(to_float(item.get('rate')))}</td>"
            f"<td class='text-right'>{html.escape(str(item.get('tax')))}%</td>"
            f"<td class='text-right'>{money_text(line_total)}</td>"
            "</tr>"
        )

    terms_html = "".join(
        "<div class='term-row'>"
        f"<div class='term-title'>{html.escape(title)}</div>"
        f"<div class='term-body'>{html.escape(body)}</div>"
        "</div>"
        for title, body in note_sections(str(payload.get("notes", "")))
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(clean_text(payload.get("display_number")))} PDF</title>
  <style>
    @page {{ size: A4; margin: 8mm; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Trebuchet MS", sans-serif;
      color: #13203c;
      background: #ffffff;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}
    .page {{
      width: 194mm;
      min-height: 279mm;
      margin: 0 auto;
      padding: 4mm 4mm 5mm;
    }}
    .page-break {{ break-before: page; page-break-before: always; }}
    .sheet-top-line {{
      height: 8px;
      border-radius: 999px;
      background: linear-gradient(90deg, #00032c, #15318f, #ef9562);
      margin-bottom: 10px;
    }}
    .brand-row {{
      display: grid;
      grid-template-columns: 54mm minmax(0, 1fr) 36mm;
      gap: 3mm;
      align-items: center;
    }}
    .quote-badge {{
      justify-self: end;
      background: #15318f;
      color: #fff;
      font-weight: 800;
      letter-spacing: 2.6px;
      text-transform: uppercase;
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 16px;
      margin-top: -148px;
    }}
    .logo-wrap {{
      display: flex;
      align-items: center;
      justify-content: flex-start;
      overflow: hidden;
    }}
    .logo-wrap img {{
      width: 32mm;
      object-fit: contain;
      display: block;
    }}
    .company-title {{
      font-size: 28px;
      font-weight: 800;
      line-height: 1.08;
      color: #15318f;
      margin: 0;
    }}
    .tagline {{
      margin-top: 4px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      color: #ef9562;
    }}
    .company-grid {{
      margin-top: 8px;
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) 68mm;
      gap: 3mm;
    }}
    .panel, .card, .totals-card, .table-wrap, .hero-strip, .quote-strip {{
      border: 1px solid rgba(21, 49, 143, 0.12);
      border-radius: 14px;
      background: #ffffff;
    }}
    .panel {{
      padding: 10px 12px;
    }}
    .contact-card {{
      padding: 10px 12px;
      background: linear-gradient(135deg, rgba(21,49,143,0.06), rgba(255,255,255,0.98));
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px 10px;
    }}
    .wide {{ grid-column: span 2; }}
    .label {{
      font-size: 9.5px;
      font-weight: 800;
      letter-spacing: 0.8px;
      text-transform: uppercase;
      color: #5d6781;
      margin-bottom: 3px;
    }}
    .value-box {{
      min-height: 30px;
      padding: 7px 8px;
      border: 1px solid rgba(21,49,143,0.12);
      border-radius: 10px;
      background: rgba(246,248,255,0.72);
      line-height: 1.35;
      overflow-wrap: anywhere;
      white-space: normal;
    }}
    .quote-strip {{
      margin-top: 8px;
      padding: 10px 12px;
      display: grid;
      grid-template-columns: 44mm minmax(0, 1fr);
      gap: 3mm;
      background: linear-gradient(135deg, rgba(237,241,255,0.92), rgba(255,255,255,0.98) 65%, rgba(255,242,235,0.72));
    }}
    .eyebrow {{
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 1.1px;
      text-transform: uppercase;
      color: #ef9562;
    }}
    .muted {{ color: #5d6781; line-height: 1.35; }}
    .quote-fields {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px 10px;
    }}
    .hero-strip {{
      margin-top: 10px;
      padding: 9px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      background: linear-gradient(135deg, #edf1ff, #ffffff 70%, #fff2eb);
    }}
    .hero-title {{ font-size: 12px; color: #5d6781; }}
    .quote-chip {{
      padding: 7px 10px;
      border-radius: 11px;
      border: 1px solid rgba(21,49,143,0.12);
      background: rgba(255,255,255,0.92);
      white-space: nowrap;
    }}
    .quote-chip strong {{ font-size: 14px; color: #00032c; }}
    .section {{
      margin-top: 10px;
    }}
    .section h3 {{
      margin: 0 0 8px;
      font-size: 12px;
      letter-spacing: 1px;
      text-transform: uppercase;
      color: #15318f;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th {{
      background: #15318f;
      color: #fff;
      padding: 9px 8px;
      font-size: 10px;
      letter-spacing: 0.8px;
      text-transform: uppercase;
      text-align: left;
    }}
    td {{
      padding: 8px;
      border-bottom: 1px solid #d5dcee;
      vertical-align: top;
      font-size: 11px;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    .text-right {{ text-align: right; }}
    .text-center {{ text-align: center; }}
    .summary-grid, .footer-grid {{
      margin-top: 10px;
      display: grid;
      grid-template-columns: 1.18fr 0.92fr;
      gap: 3mm;
    }}
    .card {{ padding: 12px; }}
    .note-box {{
      padding: 8px 10px;
      border-radius: 10px;
      border: 1px dashed rgba(21,49,143,0.24);
      background: rgba(237,241,255,0.78);
      color: #5d6781;
      line-height: 1.35;
      font-size: 10px;
    }}
    .amount-box {{
      margin-top: 10px;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px dashed rgba(21,49,143,0.24);
      background: #edf1ff;
    }}
    .totals-card {{
      overflow: hidden;
    }}
    .total-row {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 10px 12px;
      border-bottom: 1px solid #d5dcee;
      font-size: 11px;
    }}
    .total-row:last-child {{ border-bottom: 0; }}
    .total-row.grand {{
      background: #15318f;
      color: #fff;
      font-weight: 800;
      font-size: 13px;
    }}
    .seal {{
      margin: 8px 0 6px auto;
      width: 72px;
      height: 72px;
      border-radius: 50%;
      border: 1px dashed rgba(21,49,143,0.34);
      display: grid;
      place-items: center;
      text-align: center;
      color: #15318f;
      font-size: 10px;
      font-weight: 700;
    }}
    .terms-head h3 {{
      margin: 4px 0 6px;
      font-size: 20px;
      color: #00032c;
    }}
    .term-row {{
      margin-top: 8px;
      padding: 10px 12px;
      border: 1px solid rgba(21,49,143,0.1);
      border-radius: 12px;
      background: rgba(246,248,255,0.72);
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .term-title {{
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.9px;
      text-transform: uppercase;
      color: #15318f;
      margin-bottom: 4px;
    }}
    .term-body {{
      font-size: 11px;
      line-height: 1.45;
    }}
  </style>
</head>
<body>
  <section class="page">
    <div class="sheet-top-line"></div>
    <div class="brand-row">
      <div class="logo-wrap">{f"<img src='{logo_data_uri()}' alt='AstroVolt logo'>" if logo_data_uri() else ""}</div>
      <div>
        <div class="company-title">{html.escape(clean_text(payload.get("company_name")))}</div>
        <div class="tagline">{html.escape(clean_text(payload.get("tagline")))}</div>
      </div>
      <div class="quote-badge">QUOTATION</div>
    </div>

    <div class="company-grid">
      <div class="panel">
        <div class="meta-grid">
          <div class="wide">
            <div class="label">Address</div>
            <div class="value-box">{html_multiline(payload.get("company_address"))}</div>
          </div>
          <div>
            <div class="label">GSTIN</div>
            <div class="value-box">{html.escape(clean_text(payload.get("company_gstin"))) or "&nbsp;"}</div>
          </div>
          <div>
            <div class="label">PAN</div>
            <div class="value-box">{html.escape(clean_text(payload.get("company_pan")))}</div>
          </div>
          <div class="wide">
            <div class="label">TAN</div>
            <div class="value-box">{html.escape(clean_text(payload.get("company_tan")))}</div>
          </div>
        </div>
      </div>
      <div class="contact-card panel">
        <div>
          <div class="label">Phone</div>
          <div class="value-box">{html.escape(clean_text(payload.get("company_mobile"))) or "&nbsp;"}</div>
        </div>
        <div>
          <div class="label">Email</div>
          <div class="value-box">{html.escape(clean_text(payload.get("company_email")))}</div>
        </div>
        <div>
          <div class="label">Website</div>
          <div class="value-box">{html.escape(clean_text(payload.get("company_website")))}</div>
        </div>
      </div>
    </div>

    <div class="quote-strip">
      <div>
        <div class="eyebrow">Quotation Particulars</div>
        <div class="muted">Issue date and validity period</div>
      </div>
      <div class="quote-fields">
        <div>
          <div class="label">Quote Date</div>
          <div class="value-box">{html.escape(clean_text(payload.get("quote_date")))}</div>
        </div>
        <div>
          <div class="label">Valid Until</div>
          <div class="value-box">{html.escape(clean_text(payload.get("valid_until")))}</div>
        </div>
      </div>
    </div>

    <div class="hero-strip">
      <div>
        <div class="eyebrow">Quotation / Proforma</div>
        <div class="hero-title">Formal technical quotation with controlled revisions</div>
      </div>
      <div class="quote-chip"><span class="label">Number</span><br><strong>{html.escape(clean_text(payload.get("display_number")))}</strong></div>
    </div>

    <div class="section card">
      <h3>Customer Details</h3>
      <div class="meta-grid">
        <div>
          <div class="label">Customer Name</div>
          <div class="value-box">{html.escape(clean_text(payload.get("customer_name"))) or "&nbsp;"}</div>
        </div>
        <div>
          <div class="label">Contact Person</div>
          <div class="value-box">{html.escape(clean_text(payload.get("customer_contact"))) or "&nbsp;"}</div>
        </div>
        <div class="wide">
          <div class="label">Address</div>
          <div class="value-box">{html_multiline(payload.get("customer_address"))}</div>
        </div>
        <div>
          <div class="label">Mobile</div>
          <div class="value-box">{html.escape(clean_text(payload.get("customer_mobile"))) or "&nbsp;"}</div>
        </div>
        <div>
          <div class="label">GSTIN</div>
          <div class="value-box">{html.escape(clean_text(payload.get("customer_gstin"))) or "&nbsp;"}</div>
        </div>
      </div>
    </div>

    <div class="section table-wrap">
      <table>
        <thead>
          <tr>
            <th style="width:6%">Sl.</th>
            <th style="width:36%">Description</th>
            <th style="width:12%">HSN/SAC</th>
            <th style="width:9%">Qty</th>
            <th style="width:12%">Rate</th>
            <th style="width:10%">Tax %</th>
            <th style="width:15%">Line Total</th>
          </tr>
        </thead>
        <tbody>{"".join(items_html)}</tbody>
      </table>
    </div>

    <div class="summary-grid">
      <div class="card">
        <h3>Commercial Summary</h3>
        <div class="note-box">Detailed commercial conditions are attached automatically on the following page.</div>
        <div class="amount-box">
          <div class="eyebrow">Quoted Value in Words</div>
          <div style="margin-top:6px; line-height:1.45;">{html.escape(str(totals["amount_words"]))}</div>
        </div>
      </div>
      <div class="totals-card">
        <div class="total-row"><span>Taxable Value</span><strong>{money_text(float(totals["subtotal"]))}</strong></div>
        <div class="total-row"><span>CGST</span><strong>{money_text(float(totals["cgst"]))}</strong></div>
        <div class="total-row"><span>SGST</span><strong>{money_text(float(totals["sgst"]))}</strong></div>
        <div class="total-row grand"><span>Total Payable</span><strong>{money_text(float(totals["grand_total"]))}</strong></div>
      </div>
    </div>

    <div class="footer-grid">
      <div class="card">
        <h3>Bank Details</h3>
        <div class="meta-grid">
          <div>
            <div class="label">Account Name</div>
            <div class="value-box">{html.escape(clean_text(payload.get("bank_account_name")))}</div>
          </div>
          <div>
            <div class="label">Bank Name</div>
            <div class="value-box">{html.escape(clean_text(payload.get("bank_name")))}</div>
          </div>
          <div>
            <div class="label">Account Number</div>
            <div class="value-box">{html.escape(clean_text(payload.get("bank_account_number")))}</div>
          </div>
          <div>
            <div class="label">IFSC</div>
            <div class="value-box">{html.escape(clean_text(payload.get("bank_ifsc")))}</div>
          </div>
        </div>
      </div>
      <div class="card">
        <h3>Authorised Signatory</h3>
        <div class="seal">Company Seal</div>
        <div class="meta-grid" style="grid-template-columns:1fr;">
          <div>
            <div class="label">Name</div>
            <div class="value-box">{html.escape(clean_text(payload.get("signatory_name"))) or "&nbsp;"}</div>
          </div>
          <div>
            <div class="label">Designation</div>
            <div class="value-box">{html.escape(clean_text(payload.get("signatory_designation"))) or "&nbsp;"}</div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="page page-break">
    <div class="terms-head">
      <div class="eyebrow">Quotation Annexure</div>
      <h3>Commercial Conditions</h3>
      <div class="muted">These standard commercial conditions form part of this quotation.</div>
    </div>
    {terms_html}
  </section>
</body>
</html>"""


def html_snapshot(payload: dict[str, object]) -> str:
    totals = payload["totals"]
    item_rows = []
    for index, item in enumerate(payload["items"], start=1):
        amount, _line_tax = line_totals(item)
        item_rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{html.escape(clean_text(item.get('description')))}</td>"
            f"<td>{html.escape(clean_text(item.get('sac')))}</td>"
            f"<td>{html.escape(str(item.get('qty')))}</td>"
            f"<td>{money_text(to_float(item.get('rate')))}</td>"
            f"<td>{money_text(amount)}</td>"
            "</tr>"
        )
    return (
        "<html><body>"
        f"<h1>{html.escape(payload['company_name'])}</h1>"
        f"<h2>{html.escape(payload['display_number'])}</h2>"
        f"<p>Customer: {html.escape(payload['customer_name'])}</p>"
        f"<p>Date: {html.escape(payload['quote_date'])}</p>"
        f"<table border='1' cellspacing='0' cellpadding='6'>"
        "<tr><th>Sl.</th><th>Description</th><th>HSN/SAC</th><th>Qty</th><th>Rate</th><th>Amount</th></tr>"
        + "".join(item_rows)
        + "</table>"
        f"<p>Grand Total: {money_text(float(totals['grand_total']))}</p>"
        f"<p>Amount in words: {html.escape(str(totals['amount_words']))}</p>"
        "</body></html>"
    )


def export_quote_pdf(quote_id: int, display_number: str, payload: dict[str, object]) -> Path:
    browser_paths = [candidate for candidate in EDGE_CANDIDATES if candidate.exists()]
    if not browser_paths:
        raise FileNotFoundError("Microsoft Edge or Google Chrome was not found for PDF export")

    PDF_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PDF_EXPORT_DIR / f"{safe_filename(display_number)}.pdf"
    html_text = quote_document_html(payload)
    temp_html = PDF_EXPORT_DIR / f"quotation-{quote_id}.html"
    temp_html.write_text(html_text, encoding="utf-8")
    export_url = temp_html.resolve().as_uri()
    last_error = "PDF export failed"
    for browser_path in browser_paths:
        if output_path.exists():
            output_path.unlink()
        command = [
            str(browser_path),
            "--headless=new",
            "--disable-gpu",
            "--run-all-compositor-stages-before-draw",
            "--print-to-pdf-no-header",
            "--virtual-time-budget=5000",
            f"--print-to-pdf={output_path}",
            export_url,
        ]
        result = subprocess.run(command, check=False, capture_output=True, timeout=120)
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
        stderr_text = result.stderr.decode("utf-8", errors="ignore").strip()
        last_error = stderr_text or f"PDF export failed using {browser_path.name}"
    raise RuntimeError(last_error)


def export_invoice_pdf(invoice_id: int, display_number: str, payload: dict[str, object]) -> Path:
    browser_paths = [candidate for candidate in EDGE_CANDIDATES if candidate.exists()]
    if not browser_paths:
        raise FileNotFoundError("Microsoft Edge or Google Chrome was not found for PDF export")

    PDF_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PDF_EXPORT_DIR / f"{safe_filename(display_number)}.pdf"
    html_text = invoice_document_html(payload)
    temp_html = PDF_EXPORT_DIR / f"invoice-{invoice_id}.html"
    temp_html.write_text(html_text, encoding="utf-8")
    export_url = temp_html.resolve().as_uri()
    last_error = "PDF export failed"
    for browser_path in browser_paths:
        if output_path.exists():
            output_path.unlink()
        command = [
            str(browser_path),
            "--headless=new",
            "--disable-gpu",
            "--run-all-compositor-stages-before-draw",
            "--print-to-pdf-no-header",
            "--virtual-time-budget=5000",
            f"--print-to-pdf={output_path}",
            export_url,
        ]
        result = subprocess.run(command, check=False, capture_output=True, timeout=120)
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
        stderr_text = result.stderr.decode("utf-8", errors="ignore").strip()
        last_error = stderr_text or f"PDF export failed using {browser_path.name}"
    raise RuntimeError(last_error)


def export_salary_pdf(run_id: int, row: sqlite3.Row) -> Path:
    browser_paths = [candidate for candidate in EDGE_CANDIDATES if candidate.exists()]
    if not browser_paths:
        raise FileNotFoundError("Microsoft Edge or Google Chrome was not found for PDF export")

    PDF_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    filename = safe_filename(f"SALARY-{row['employee_code']}-{row['month']}")
    output_path = PDF_EXPORT_DIR / f"{filename}.pdf"
    logo_file = ASSETS_DIR / "logo.png"
    logo_src = None
    if logo_file.exists():
        encoded = base64.b64encode(logo_file.read_bytes()).decode("ascii")
        logo_src = f"data:image/png;base64,{encoded}"
    html_text = salary_slip_html(row, logo_src=logo_src)
    temp_html = PDF_EXPORT_DIR / f"salary-slip-{run_id}.html"
    temp_html.write_text(html_text, encoding="utf-8")
    export_url = temp_html.resolve().as_uri()
    last_error = "PDF export failed"
    for browser_path in browser_paths:
        if output_path.exists():
            output_path.unlink()
        command = [
            str(browser_path),
            "--headless=new",
            "--disable-gpu",
            "--run-all-compositor-stages-before-draw",
            "--print-to-pdf-no-header",
            "--virtual-time-budget=5000",
            f"--print-to-pdf={output_path}",
            export_url,
        ]
        result = subprocess.run(command, check=False, capture_output=True, timeout=120)
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
        stderr_text = result.stderr.decode("utf-8", errors="ignore").strip()
        last_error = stderr_text or f"PDF export failed using {browser_path.name}"
    raise RuntimeError(last_error)


def save_draft(connection: sqlite3.Connection, payload: dict[str, object]) -> dict[str, object]:
    normalized = normalize_payload(payload, connection)
    now = utc_now_text()
    serialized = json.dumps(normalized)

    if normalized.get("id"):
        row = get_quote(connection, int(normalized["id"]))
        if row is None:
            raise KeyError("Quotation not found")
        if row["status"] != "DRAFT" or row["is_locked"]:
            raise PermissionError("Final quotations are locked and cannot be changed")
        connection.execute(
            """
            UPDATE quotations
            SET company_name = ?, customer_name = ?, quote_date = ?, valid_until = ?,
                subtotal = ?, cgst = ?, sgst = ?, grand_total = ?,
                payload_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                normalized["company_name"],
                normalized["customer_name"],
                normalized["quote_date"],
                normalized["valid_until"],
                normalized["totals"]["subtotal"],
                normalized["totals"]["cgst"],
                normalized["totals"]["sgst"],
                normalized["totals"]["grand_total"],
                serialized,
                now,
                int(normalized["id"]),
            ),
        )
        quote_id = int(normalized["id"])
        record_event(connection, quote_id, "SAVE_DRAFT", "Draft updated")
    else:
        connection.execute(
            """
            INSERT INTO quotations(
                base_quote_number, revision_number, display_number, status, is_locked,
                company_name, customer_name, quote_date, valid_until,
                subtotal, cgst, sgst, grand_total,
                payload_json, created_at, updated_at, parent_quote_id
            )
            VALUES(?, ?, ?, 'DRAFT', 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized["base_quote_number"],
                normalized["revision_number"],
                normalized["display_number"],
                normalized["company_name"],
                normalized["customer_name"],
                normalized["quote_date"],
                normalized["valid_until"],
                normalized["totals"]["subtotal"],
                normalized["totals"]["cgst"],
                normalized["totals"]["sgst"],
                normalized["totals"]["grand_total"],
                serialized,
                now,
                now,
                payload.get("parent_quote_id"),
            ),
        )
        quote_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
        record_event(connection, quote_id, "SAVE_DRAFT", "Draft created")

    row = get_quote(connection, quote_id)
    return quote_row_to_dict(row, include_payload=True)


def finalize_quote(connection: sqlite3.Connection, quote_id: int, pin: str) -> dict[str, object]:
    if not pin_configured(connection):
        raise PermissionError("Set the admin PIN before finalising quotations")
    if not verify_admin_pin(connection, pin):
        raise PermissionError("Invalid admin PIN")

    row = get_quote(connection, quote_id)
    if row is None:
        raise KeyError("Quotation not found")
    if row["status"] != "DRAFT" or row["is_locked"]:
        raise PermissionError("Only draft quotations can be finalised")

    payload = json.loads(row["payload_json"])
    payload["status"] = "FINAL"
    payload["display_number"] = row["display_number"]
    payload["id"] = row["id"]
    payload["is_locked"] = True
    finalised_at = utc_now_text()

    connection.execute(
        """
        UPDATE quotations
        SET status = 'FINAL',
            is_locked = 1,
            payload_json = ?,
            html_snapshot = ?,
            updated_at = ?,
            finalised_at = ?
        WHERE id = ?
        """,
        (
            json.dumps(payload),
            html_snapshot(payload),
            finalised_at,
            finalised_at,
            quote_id,
        ),
    )
    record_event(connection, quote_id, "FINALISE", "Quotation locked as final")
    return quote_row_to_dict(get_quote(connection, quote_id), include_payload=True)


def create_revision(connection: sqlite3.Connection, quote_id: int, pin: str) -> dict[str, object]:
    if not pin_configured(connection):
        raise PermissionError("Set the admin PIN before creating revisions")
    if not verify_admin_pin(connection, pin):
        raise PermissionError("Invalid admin PIN")

    source_row = get_quote(connection, quote_id)
    if source_row is None:
        raise KeyError("Quotation not found")
    if source_row["status"] != "FINAL":
        raise PermissionError("Only final quotations can create revisions")

    max_revision_row = connection.execute(
        "SELECT MAX(revision_number) AS max_revision FROM quotations WHERE base_quote_number = ?",
        (source_row["base_quote_number"],),
    ).fetchone()
    next_revision = int(max_revision_row["max_revision"] or 0) + 1

    payload = json.loads(source_row["payload_json"])
    payload["id"] = None
    payload["revision_number"] = next_revision
    payload["display_number"] = quote_display_number(source_row["base_quote_number"], next_revision)
    payload["status"] = "DRAFT"
    payload["quote_date"] = today_text()
    payload["valid_until"] = plus_days(payload["quote_date"], 60)
    normalized = normalize_payload(payload, connection)

    now = utc_now_text()
    connection.execute(
        """
        INSERT INTO quotations(
            base_quote_number, revision_number, display_number, status, is_locked,
            company_name, customer_name, quote_date, valid_until,
            subtotal, cgst, sgst, grand_total,
            payload_json, created_at, updated_at, parent_quote_id
        )
        VALUES(?, ?, ?, 'DRAFT', 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            normalized["base_quote_number"],
            normalized["revision_number"],
            normalized["display_number"],
            normalized["company_name"],
            normalized["customer_name"],
            normalized["quote_date"],
            normalized["valid_until"],
            normalized["totals"]["subtotal"],
            normalized["totals"]["cgst"],
            normalized["totals"]["sgst"],
            normalized["totals"]["grand_total"],
            json.dumps(normalized),
            now,
            now,
            quote_id,
        ),
    )
    new_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
    record_event(connection, new_id, "CREATE_REVISION", f"Revision created from quotation {quote_id}")
    return quote_row_to_dict(get_quote(connection, new_id), include_payload=True)


def save_invoice_draft(connection: sqlite3.Connection, payload: dict[str, object]) -> dict[str, object]:
    normalized = normalize_invoice_payload(payload, connection)
    now = utc_now_text()
    serialized = json.dumps(normalized)

    if normalized.get("id"):
        row = get_invoice(connection, int(normalized["id"]))
        if row is None:
            raise KeyError("Invoice not found")
        if row["status"] != "DRAFT" or row["is_locked"]:
            raise PermissionError("Final invoices are locked and cannot be changed")
        connection.execute(
            """
            UPDATE invoices
            SET company_name = ?, customer_name = ?, invoice_date = ?, due_date = ?,
                subtotal = ?, cgst = ?, sgst = ?, grand_total = ?,
                payload_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                normalized["company_name"],
                normalized["customer_name"],
                normalized["quote_date"],
                normalized["valid_until"],
                normalized["totals"]["subtotal"],
                normalized["totals"]["cgst"],
                normalized["totals"]["sgst"],
                normalized["totals"]["grand_total"],
                serialized,
                now,
                int(normalized["id"]),
            ),
        )
        invoice_id = int(normalized["id"])
        record_invoice_event(connection, invoice_id, "SAVE_DRAFT", "Draft updated")
    else:
        connection.execute(
            """
            INSERT INTO invoices(
                base_invoice_number, revision_number, display_number, status, is_locked,
                company_name, customer_name, invoice_date, due_date,
                subtotal, cgst, sgst, grand_total,
                payload_json, created_at, updated_at, parent_invoice_id
            )
            VALUES(?, ?, ?, 'DRAFT', 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized["base_invoice_number"],
                normalized["revision_number"],
                normalized["display_number"],
                normalized["company_name"],
                normalized["customer_name"],
                normalized["quote_date"],
                normalized["valid_until"],
                normalized["totals"]["subtotal"],
                normalized["totals"]["cgst"],
                normalized["totals"]["sgst"],
                normalized["totals"]["grand_total"],
                serialized,
                now,
                now,
                payload.get("parent_invoice_id"),
            ),
        )
        invoice_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
        record_invoice_event(connection, invoice_id, "SAVE_DRAFT", "Draft created")

    row = get_invoice(connection, invoice_id)
    return invoice_row_to_dict(row, include_payload=True)


def finalize_invoice(connection: sqlite3.Connection, invoice_id: int, pin: str) -> dict[str, object]:
    if not pin_configured(connection):
        raise PermissionError("Set the admin PIN before finalising invoices")
    if not verify_admin_pin(connection, pin):
        raise PermissionError("Invalid admin PIN")

    row = get_invoice(connection, invoice_id)
    if row is None:
        raise KeyError("Invoice not found")
    if row["status"] != "DRAFT" or row["is_locked"]:
        raise PermissionError("Only draft invoices can be finalised")

    payload = json.loads(row["payload_json"])
    payload["status"] = "FINAL"
    payload["display_number"] = row["display_number"]
    payload["id"] = row["id"]
    payload["is_locked"] = True
    finalised_at = utc_now_text()

    connection.execute(
        """
        UPDATE invoices
        SET status = 'FINAL',
            is_locked = 1,
            payload_json = ?,
            html_snapshot = ?,
            updated_at = ?,
            finalised_at = ?
        WHERE id = ?
        """,
        (
            json.dumps(payload),
            html_snapshot(payload),
            finalised_at,
            finalised_at,
            invoice_id,
        ),
    )
    record_invoice_event(connection, invoice_id, "FINALISE", "Invoice locked as final")
    return invoice_row_to_dict(get_invoice(connection, invoice_id), include_payload=True)


def create_invoice_revision(connection: sqlite3.Connection, invoice_id: int, pin: str) -> dict[str, object]:
    if not pin_configured(connection):
        raise PermissionError("Set the admin PIN before creating revisions")
    if not verify_admin_pin(connection, pin):
        raise PermissionError("Invalid admin PIN")

    source_row = get_invoice(connection, invoice_id)
    if source_row is None:
        raise KeyError("Invoice not found")
    if source_row["status"] != "FINAL":
        raise PermissionError("Only final invoices can create revisions")

    max_revision_row = connection.execute(
        "SELECT MAX(revision_number) AS max_revision FROM invoices WHERE base_invoice_number = ?",
        (source_row["base_invoice_number"],),
    ).fetchone()
    next_revision = int(max_revision_row["max_revision"] or 0) + 1

    payload = json.loads(source_row["payload_json"])
    payload["id"] = None
    payload["revision_number"] = next_revision
    payload["display_number"] = quote_display_number(source_row["base_invoice_number"], next_revision)
    payload["status"] = "DRAFT"
    payload["quote_date"] = today_text()
    payload["valid_until"] = plus_days(payload["quote_date"], 60)
    normalized = normalize_invoice_payload(payload, connection)

    now = utc_now_text()
    connection.execute(
        """
        INSERT INTO invoices(
            base_invoice_number, revision_number, display_number, status, is_locked,
            company_name, customer_name, invoice_date, due_date,
            subtotal, cgst, sgst, grand_total,
            payload_json, created_at, updated_at, parent_invoice_id
        )
        VALUES(?, ?, ?, 'DRAFT', 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            normalized["base_invoice_number"],
            normalized["revision_number"],
            normalized["display_number"],
            normalized["company_name"],
            normalized["customer_name"],
            normalized["quote_date"],
            normalized["valid_until"],
            normalized["totals"]["subtotal"],
            normalized["totals"]["cgst"],
            normalized["totals"]["sgst"],
            normalized["totals"]["grand_total"],
            json.dumps(normalized),
            now,
            now,
            invoice_id,
        ),
    )
    new_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
    record_invoice_event(connection, new_id, "CREATE_REVISION", f"Revision created from invoice {invoice_id}")
    return invoice_row_to_dict(get_invoice(connection, new_id), include_payload=True)


def next_employee_code(connection: sqlite3.Connection) -> str:
    rows = connection.execute("SELECT employee_code FROM employees WHERE employee_code LIKE 'AVG%'").fetchall()
    current_max = 0
    for row in rows:
        code = row["employee_code"]
        digits = "".join(ch for ch in code if ch.isdigit())
        if digits:
            current_max = max(current_max, int(digits))
    return f"AVG{current_max + 1:05d}"


def employee_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    week_off = []
    try:
        week_off = json.loads(row["week_off"] or "[]")
    except json.JSONDecodeError:
        week_off = []
    return {
        "id": row["id"],
        "employee_code": row["employee_code"],
        "full_name": row["full_name"],
        "dob": row["dob"],
        "gender": row["gender"],
        "phone": row["phone"],
        "email": row["email"],
        "address": row["address"],
        "doj": row["doj"],
        "department": row["department"],
        "designation": row["designation"],
        "employment_type": row["employment_type"],
        "status": row["status"],
        "base_salary": row["base_salary"],
        "allowances": row["allowances"],
        "pf_percent": row["pf_percent"],
        "esi_percent": row["esi_percent"],
        "overtime_rate": row["overtime_rate"],
        "pf_mode": row["pf_mode"] if "pf_mode" in row.keys() else "PERCENT",
        "pf_fixed": row["pf_fixed"] if "pf_fixed" in row.keys() else 1800,
        "bank_name": row["bank_name"],
        "bank_account": row["bank_account"],
        "bank_ifsc": row["bank_ifsc"],
        "emergency_contact_name": row["emergency_contact_name"],
        "emergency_contact_phone": row["emergency_contact_phone"],
        "leave_balance": row["leave_balance"],
        "week_off": week_off,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def normalize_employee_payload(payload: dict[str, object], connection: sqlite3.Connection) -> dict[str, object]:
    employee_code = clean_text(payload.get("employee_code")) or next_employee_code(connection)
    week_off = payload.get("week_off", [])
    if not isinstance(week_off, list):
        week_off = []
    pf_mode = clean_text(payload.get("pf_mode")).upper() or "PERCENT"
    if pf_mode not in ("PERCENT", "FIXED"):
        pf_mode = "PERCENT"
    return {
        "employee_code": employee_code,
        "full_name": clean_text(payload.get("full_name")),
        "dob": clean_text(payload.get("dob")),
        "gender": clean_text(payload.get("gender")),
        "phone": clean_text(payload.get("phone")),
        "email": clean_text(payload.get("email")),
        "address": clean_text(payload.get("address")),
        "doj": clean_text(payload.get("doj")),
        "department": clean_text(payload.get("department")),
        "designation": clean_text(payload.get("designation")),
        "employment_type": clean_text(payload.get("employment_type")),
        "status": clean_text(payload.get("status")) or "ACTIVE",
        "base_salary": to_float(payload.get("base_salary", 0)),
        "allowances": to_float(payload.get("allowances", 0)),
        "pf_percent": to_float(payload.get("pf_percent", 0)),
        "esi_percent": to_float(payload.get("esi_percent", 0)),
        "overtime_rate": to_float(payload.get("overtime_rate", 0)),
        "pf_mode": pf_mode,
        "pf_fixed": to_float(payload.get("pf_fixed", 1800)),
        "bank_name": clean_text(payload.get("bank_name")),
        "bank_account": clean_text(payload.get("bank_account")),
        "bank_ifsc": clean_text(payload.get("bank_ifsc")),
        "emergency_contact_name": clean_text(payload.get("emergency_contact_name")),
        "emergency_contact_phone": clean_text(payload.get("emergency_contact_phone")),
        "leave_balance": to_float(payload.get("leave_balance", 0)),
        "week_off": json.dumps(week_off),
    }


def list_employees(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        "SELECT * FROM employees ORDER BY updated_at DESC, id DESC"
    ).fetchall()
    return [employee_row_to_dict(row) for row in rows]


def get_employee(connection: sqlite3.Connection, employee_id: int) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()


def save_employee(connection: sqlite3.Connection, payload: dict[str, object]) -> dict[str, object]:
    normalized = normalize_employee_payload(payload, connection)
    now = utc_now_text()
    if payload.get("id"):
        employee_id = int(payload["id"])
        connection.execute(
            """
            UPDATE employees
            SET employee_code = ?, full_name = ?, dob = ?, gender = ?, phone = ?, email = ?, address = ?,
                doj = ?, department = ?, designation = ?, employment_type = ?, status = ?,
                base_salary = ?, allowances = ?, pf_percent = ?, esi_percent = ?, overtime_rate = ?,
                pf_mode = ?, pf_fixed = ?,
                bank_name = ?, bank_account = ?, bank_ifsc = ?,
                emergency_contact_name = ?, emergency_contact_phone = ?, leave_balance = ?, week_off = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                normalized["employee_code"],
                normalized["full_name"],
                normalized["dob"],
                normalized["gender"],
                normalized["phone"],
                normalized["email"],
                normalized["address"],
                normalized["doj"],
                normalized["department"],
                normalized["designation"],
                normalized["employment_type"],
                normalized["status"],
                normalized["base_salary"],
                normalized["allowances"],
                normalized["pf_percent"],
                normalized["esi_percent"],
                normalized["overtime_rate"],
                normalized["pf_mode"],
                normalized["pf_fixed"],
                normalized["bank_name"],
                normalized["bank_account"],
                normalized["bank_ifsc"],
                normalized["emergency_contact_name"],
                normalized["emergency_contact_phone"],
                normalized["leave_balance"],
                normalized["week_off"],
                now,
                employee_id,
            ),
        )
    else:
        connection.execute(
            """
            INSERT INTO employees(
                employee_code, full_name, dob, gender, phone, email, address,
                doj, department, designation, employment_type, status,
                base_salary, allowances, pf_percent, esi_percent, overtime_rate,
                pf_mode, pf_fixed,
                bank_name, bank_account, bank_ifsc,
                emergency_contact_name, emergency_contact_phone, leave_balance, week_off,
                created_at, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized["employee_code"],
                normalized["full_name"],
                normalized["dob"],
                normalized["gender"],
                normalized["phone"],
                normalized["email"],
                normalized["address"],
                normalized["doj"],
                normalized["department"],
                normalized["designation"],
                normalized["employment_type"],
                normalized["status"],
                normalized["base_salary"],
                normalized["allowances"],
                normalized["pf_percent"],
                normalized["esi_percent"],
                normalized["overtime_rate"],
                normalized["pf_mode"],
                normalized["pf_fixed"],
                normalized["bank_name"],
                normalized["bank_account"],
                normalized["bank_ifsc"],
                normalized["emergency_contact_name"],
                normalized["emergency_contact_phone"],
                normalized["leave_balance"],
                normalized["week_off"],
                now,
                now,
            ),
        )
        employee_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])

    row = get_employee(connection, employee_id)
    if row is None:
        raise KeyError("Employee not found")
    return employee_row_to_dict(row)


def attendance_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "employee_id": row["employee_id"],
        "work_date": row["work_date"],
        "status": row["status"],
        "overtime_hours": row["overtime_hours"],
        "note": row["note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def attendance_for_month(connection: sqlite3.Connection, employee_id: int, month: str) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT * FROM attendance
        WHERE employee_id = ? AND work_date LIKE ?
        ORDER BY work_date ASC
        """,
        (employee_id, f"{month}-%"),
    ).fetchall()
    return [attendance_row_to_dict(row) for row in rows]


def holidays_for_month(connection: sqlite3.Connection, month: str) -> list[dict[str, object]]:
    rows = connection.execute(
        "SELECT holiday_date, title FROM holidays WHERE holiday_date LIKE ? ORDER BY holiday_date ASC",
        (f"{month}-%",),
    ).fetchall()
    return [{"holiday_date": row["holiday_date"], "title": row["title"]} for row in rows]


def week_off_dates(month: str, week_off: list[str]) -> list[str]:
    if not week_off:
        return []
    mapping = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
    normalized = {mapping.get(day.strip().upper()[:3]) for day in week_off}
    normalized.discard(None)
    year, month_number = month.split("-")
    days_in_month = calendar.monthrange(int(year), int(month_number))[1]
    results: list[str] = []
    for day in range(1, days_in_month + 1):
        current = date(int(year), int(month_number), day)
        if current.weekday() in normalized:
            results.append(current.isoformat())
    return results


def effective_attendance_entries(
    connection: sqlite3.Connection,
    employee: dict[str, object],
    month: str,
) -> list[dict[str, object]]:
    entries = attendance_for_month(connection, employee["id"], month)
    by_date = {entry["work_date"]: entry for entry in entries}
    holidays = holidays_for_month(connection, month)
    for holiday in holidays:
        if holiday["holiday_date"] not in by_date:
            by_date[holiday["holiday_date"]] = {
                "id": None,
                "employee_id": employee["id"],
                "work_date": holiday["holiday_date"],
                "status": "HOLIDAY",
                "overtime_hours": 0,
                "note": holiday["title"],
                "created_at": "",
                "updated_at": "",
            }
    for off_date in week_off_dates(month, employee.get("week_off", [])):
        if off_date not in by_date:
            by_date[off_date] = {
                "id": None,
                "employee_id": employee["id"],
                "work_date": off_date,
                "status": "WEEK_OFF",
                "overtime_hours": 0,
                "note": "Weekly off",
                "created_at": "",
                "updated_at": "",
            }
    return sorted(by_date.values(), key=lambda item: item["work_date"])


def attendance_summary(entries: list[dict[str, object]]) -> dict[str, float]:
    present = 0.0
    absent = 0.0
    half = 0.0
    leave = 0.0
    holiday = 0.0
    week_off = 0.0
    lwp = 0.0
    overtime = 0.0
    for entry in entries:
        status = entry.get("status")
        if status == "PRESENT":
            present += 1
        elif status == "ABSENT":
            absent += 1
        elif status == "HALF_DAY":
            half += 1
        elif status == "LEAVE":
            leave += 1
        elif status == "HOLIDAY":
            holiday += 1
        elif status == "WEEK_OFF":
            week_off += 1
        elif status == "LWP":
            lwp += 1
        overtime += to_float(entry.get("overtime_hours", 0))
    return {
        "present_days": present,
        "absent_days": absent,
        "half_days": half,
        "leave_days": leave,
        "holiday_days": holiday,
        "week_off_days": week_off,
        "lwp_days": lwp,
        "overtime_hours": overtime,
    }


def save_attendance(connection: sqlite3.Connection, payload: dict[str, object]) -> dict[str, object]:
    employee_id = int(payload.get("employee_id", 0))
    work_date = clean_text(payload.get("work_date"))
    status = clean_text(payload.get("status")) or "PRESENT"
    overtime_hours = to_float(payload.get("overtime_hours", 0))
    note = clean_text(payload.get("note"))
    now = utc_now_text()
    if not employee_id or not work_date:
        raise ValueError("employee_id and work_date are required")
    if status == "LEAVE":
        employee_row = get_employee(connection, employee_id)
        if employee_row is None:
            raise KeyError("Employee not found")
        employee = employee_row_to_dict(employee_row)
        year = work_date[:4]
        leave_used = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM attendance
            WHERE employee_id = ? AND status = 'LEAVE' AND work_date LIKE ?
            """,
            (employee_id, f"{year}-%"),
        ).fetchone()["total"]
        # If this date already marked as LEAVE, don't double count.
        existing = connection.execute(
            "SELECT status FROM attendance WHERE employee_id = ? AND work_date = ?",
            (employee_id, work_date),
        ).fetchone()
        if existing and existing["status"] == "LEAVE":
            leave_used -= 1
        if leave_used + 1 > to_float(employee.get("leave_balance", 0)):
            raise PermissionError("Leave balance exhausted. Use LWP for unpaid leave.")
    connection.execute(
        """
        INSERT INTO attendance(employee_id, work_date, status, overtime_hours, note, created_at, updated_at)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(employee_id, work_date) DO UPDATE SET
            status = excluded.status,
            overtime_hours = excluded.overtime_hours,
            note = excluded.note,
            updated_at = excluded.updated_at
        """,
        (employee_id, work_date, status, overtime_hours, note, now, now),
    )
    row = connection.execute(
        "SELECT * FROM attendance WHERE employee_id = ? AND work_date = ?",
        (employee_id, work_date),
    ).fetchone()
    if row is None:
        raise KeyError("Attendance not saved")
    return attendance_row_to_dict(row)


def salary_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "employee_id": row["employee_id"],
        "month": row["month"],
        "days_in_month": row["days_in_month"],
        "present_days": row["present_days"],
        "absent_days": row["absent_days"],
        "half_days": row["half_days"],
        "overtime_hours": row["overtime_hours"],
        "base_salary": row["base_salary"],
        "allowances": row["allowances"],
        "overtime_amount": row["overtime_amount"],
        "lop_amount": row["lop_amount"],
        "pf_amount": row["pf_amount"],
        "esi_amount": row["esi_amount"],
        "other_deductions": row["other_deductions"],
        "advance": row["advance"],
        "net_pay": row["net_pay"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def calculate_salary(
    employee: dict[str, object],
    month: str,
    summary: dict[str, float],
    other_deductions: float,
    advance: float,
) -> dict[str, float | int | str]:
    year, month_number = month.split("-")
    days_in_month = calendar.monthrange(int(year), int(month_number))[1]
    base_salary = to_float(employee.get("base_salary", 0))
    allowances = to_float(employee.get("allowances", 0))
    overtime_rate = to_float(employee.get("overtime_rate", 0))
    pf_percent = to_float(employee.get("pf_percent", 0))
    esi_percent = to_float(employee.get("esi_percent", 0))
    pf_mode = (employee.get("pf_mode") or "PERCENT").upper()
    pf_fixed = to_float(employee.get("pf_fixed", 1800))
    present_days = summary["present_days"] + summary["half_days"] * 0.5
    accounted = (
        summary["present_days"]
        + summary["absent_days"]
        + summary["half_days"]
        + summary.get("leave_days", 0)
        + summary.get("holiday_days", 0)
        + summary.get("week_off_days", 0)
        + summary.get("lwp_days", 0)
    )
    missing = max(0.0, days_in_month - accounted)
    lop_days = summary["absent_days"] + summary["half_days"] * 0.5 + summary.get("lwp_days", 0) + missing
    overtime_hours = summary["overtime_hours"]
    per_day_rate = base_salary / days_in_month if days_in_month else 0
    overtime_amount = overtime_hours * overtime_rate
    lop_amount = lop_days * per_day_rate
    if pf_mode == "FIXED":
        pf_amount = pf_fixed
    else:
        pf_amount = base_salary * pf_percent / 100.0
    esi_amount = base_salary * esi_percent / 100.0
    net_pay = base_salary + allowances + overtime_amount - lop_amount - pf_amount - esi_amount - other_deductions - advance
    return {
        "month": month,
        "days_in_month": days_in_month,
        "present_days": round(present_days, 2),
        "absent_days": round(summary["absent_days"], 2),
        "half_days": round(summary["half_days"], 2),
        "leave_days": round(summary.get("leave_days", 0), 2),
        "holiday_days": round(summary.get("holiday_days", 0), 2),
        "week_off_days": round(summary.get("week_off_days", 0), 2),
        "lwp_days": round(summary.get("lwp_days", 0), 2),
        "missing_days": round(missing, 2),
        "overtime_hours": round(overtime_hours, 2),
        "base_salary": round(base_salary, 2),
        "allowances": round(allowances, 2),
        "overtime_amount": round(overtime_amount, 2),
        "lop_amount": round(lop_amount, 2),
        "pf_amount": round(pf_amount, 2),
        "esi_amount": round(esi_amount, 2),
        "other_deductions": round(other_deductions, 2),
        "advance": round(advance, 2),
        "net_pay": round(net_pay, 2),
    }


def salary_slip_html(row: sqlite3.Row, logo_src: str | None = None) -> str:
    def fmt(value: object) -> str:
        try:
            return money_text(float(value))
        except (TypeError, ValueError):
            return "0.00"

    def text(value: object) -> str:
        return html.escape("" if value is None else str(value))

    def month_label(month_text: str) -> str:
        parts = (month_text or "").split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            year = parts[0]
            month_idx = int(parts[1])
            if 1 <= month_idx <= 12:
                return f"{calendar.month_name[month_idx]} {year}"
        return month_text or ""

    gross_earnings = (
        float(row["base_salary"])
        + float(row["allowances"])
        + float(row["overtime_amount"])
    )
    gross_deductions = (
        float(row["lop_amount"])
        + float(row["pf_amount"])
        + float(row["esi_amount"])
        + float(row["other_deductions"])
        + float(row["advance"])
    )

    logo_path = logo_src or "/logo.png"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Salary Slip - {html.escape(row['employee_code'])}</title>
  <style>
    body {{
      font-family: "Times New Roman", serif;
      margin: 24px;
      color: #111;
    }}
    .page {{
      max-width: 880px;
      margin: 0 auto;
      border: 1px solid #333;
      padding: 16px 18px;
    }}
    .header {{
      border-bottom: 1px solid #333;
      padding-bottom: 10px;
      margin-bottom: 12px;
    }}
    .header-top {{
      display: grid;
      grid-template-columns: 70px 1fr;
      align-items: center;
      gap: 8px;
    }}
    .title-wrap {{
      text-align: center;
    }}
    .header h1 {{
      margin: 0;
      font-size: 18px;
      letter-spacing: 0.2px;
    }}
    .header .sub {{
      font-size: 12px;
      margin-top: 4px;
    }}
    .salary-logo {{
      height: 64px;
      width: auto;
      object-fit: contain;
    }}
    .header .meta {{
      margin-top: 10px;
      font-size: 12px;
      font-weight: 600;
    }}
    .info-table {{
      width: 100%;
      border: 1px solid #333;
      border-collapse: collapse;
      margin-bottom: 10px;
    }}
    .info-table td {{
      vertical-align: top;
      padding: 6px 8px;
      border-right: 1px solid #333;
      width: 50%;
    }}
    .info-table td:last-child {{
      border-right: none;
    }}
    .kv {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }}
    .kv td {{
      padding: 2px 0;
    }}
    .kv td.key {{
      width: 42%;
      font-weight: 600;
    }}
    .kv td.sep {{
      width: 4%;
      text-align: center;
    }}
    .pay-table {{
      width: 100%;
      border: 1px solid #333;
      border-collapse: collapse;
      font-size: 12px;
    }}
    .pay-table th,
    .pay-table td {{
      border: 1px solid #333;
      padding: 4px 6px;
      text-align: right;
    }}
    .pay-table th {{
      background: #f2f2f2;
      text-align: center;
      font-weight: 700;
    }}
    .pay-table td.label {{
      text-align: left;
    }}
    .section-title {{
      text-align: center;
      font-weight: 700;
      background: #f2f2f2;
    }}
    .netpay {{
      border: 1px solid #333;
      border-top: none;
      padding: 8px 10px;
      font-size: 13px;
      font-weight: 700;
      text-align: center;
    }}
    .amount-words {{
      font-weight: 600;
    }}
    .small {{
      font-size: 11px;
    }}
    @media print {{
      body {{
        margin: 0;
      }}
      .page {{
        border: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <div class="header-top">
        <img src="{html.escape(logo_path)}" alt="Company logo" class="salary-logo">
        <div class="title-wrap">
          <h1>{html.escape(DEFAULT_QUOTE["company_name"])}</h1>
          <div class="sub">{html.escape(DEFAULT_QUOTE["company_address"])}</div>
          <div class="meta">Pay Slip for the month of {html.escape(month_label(row["month"]))}</div>
          <div class="small">All amounts are in INR</div>
        </div>
      </div>
    </div>

    <table class="info-table">
      <tr>
        <td>
          <table class="kv">
            <tr><td class="key">Emp Code</td><td class="sep">:</td><td>{text(row["employee_code"])}</td></tr>
            <tr><td class="key">Emp Name</td><td class="sep">:</td><td>{text(row["full_name"])}</td></tr>
            <tr><td class="key">Department</td><td class="sep">:</td><td>{text(row["department"])}</td></tr>
            <tr><td class="key">Designation</td><td class="sep">:</td><td>{text(row["designation"])}</td></tr>
            <tr><td class="key">Payable Days</td><td class="sep">:</td><td>{fmt(row["present_days"])}</td></tr>
            <tr><td class="key">Month Days</td><td class="sep">:</td><td>{fmt(row["days_in_month"])}</td></tr>
            <tr><td class="key">Overtime Hours</td><td class="sep">:</td><td>{fmt(row["overtime_hours"])}</td></tr>
          </table>
        </td>
        <td>
          <table class="kv">
            <tr><td class="key">Bank Name</td><td class="sep">:</td><td>{text(row["bank_name"])}</td></tr>
            <tr><td class="key">Bank A/c No.</td><td class="sep">:</td><td>{text(row["bank_account"])}</td></tr>
            <tr><td class="key">PF Amount</td><td class="sep">:</td><td>{fmt(row["pf_amount"])}</td></tr>
            <tr><td class="key">ESI Amount</td><td class="sep">:</td><td>{fmt(row["esi_amount"])}</td></tr>
            <tr><td class="key">LOP Amount</td><td class="sep">:</td><td>{fmt(row["lop_amount"])}</td></tr>
            <tr><td class="key">Other Deductions</td><td class="sep">:</td><td>{fmt(row["other_deductions"])}</td></tr>
            <tr><td class="key">Advance</td><td class="sep">:</td><td>{fmt(row["advance"])}</td></tr>
          </table>
        </td>
      </tr>
    </table>

    <table class="pay-table">
      <tr>
        <th colspan="5">Earnings</th>
        <th colspan="2">Deductions</th>
      </tr>
      <tr>
        <th>Description</th>
        <th>Rate</th>
        <th>Monthly</th>
        <th>Arrear</th>
        <th>Total</th>
        <th>Description</th>
        <th>Amount</th>
      </tr>
      <tr>
        <td class="label">Basic</td>
        <td>{fmt(row["base_salary"])}</td>
        <td>{fmt(row["base_salary"])}</td>
        <td>{fmt(0)}</td>
        <td>{fmt(row["base_salary"])}</td>
        <td class="label">PF</td>
        <td>{fmt(row["pf_amount"])}</td>
      </tr>
      <tr>
        <td class="label">Allowances</td>
        <td>{fmt(row["allowances"])}</td>
        <td>{fmt(row["allowances"])}</td>
        <td>{fmt(0)}</td>
        <td>{fmt(row["allowances"])}</td>
        <td class="label">ESI</td>
        <td>{fmt(row["esi_amount"])}</td>
      </tr>
      <tr>
        <td class="label">Overtime</td>
        <td>{fmt(row["overtime_amount"])}</td>
        <td>{fmt(row["overtime_amount"])}</td>
        <td>{fmt(0)}</td>
        <td>{fmt(row["overtime_amount"])}</td>
        <td class="label">LOP</td>
        <td>{fmt(row["lop_amount"])}</td>
      </tr>
      <tr>
        <td class="label">Special Allowance</td>
        <td>{fmt(0)}</td>
        <td>{fmt(0)}</td>
        <td>{fmt(0)}</td>
        <td>{fmt(0)}</td>
        <td class="label">Other Deductions</td>
        <td>{fmt(row["other_deductions"])}</td>
      </tr>
      <tr>
        <td class="label">Arrears</td>
        <td>{fmt(0)}</td>
        <td>{fmt(0)}</td>
        <td>{fmt(0)}</td>
        <td>{fmt(0)}</td>
        <td class="label">Advance</td>
        <td>{fmt(row["advance"])}</td>
      </tr>
      <tr>
        <td class="label section-title" colspan="4">GROSS EARNINGS</td>
        <td>{fmt(gross_earnings)}</td>
        <td class="label section-title">GROSS DEDUCTIONS</td>
        <td>{fmt(gross_deductions)}</td>
      </tr>
    </table>

    <div class="netpay">
      Net Pay : {fmt(row["net_pay"])} <span class="amount-words">({html.escape(number_to_words(float(row["net_pay"])))})</span>
    </div>
  </div>
</body>
</html>
""".strip()


def invoice_document_html(payload: dict[str, object]) -> str:
    html_text = quote_document_html(payload)
    replacements = [
        ("Quotation Particulars", "Invoice Particulars"),
        ("Quotation / Proforma", "Invoice / Tax Invoice"),
        ("Formal technical quotation with controlled revisions", "Standard tax invoice with controlled records"),
        ("Quotation Annexure", "Invoice Annexure"),
        (
            "These standard commercial conditions form part of this quotation and print automatically as the next page.",
            "These standard conditions form part of this invoice and print automatically as the next page.",
        ),
        ("Quoted Value in Words", "Invoice Value in Words"),
        ("Quotation Number", "Invoice Number"),
        ("Quotation", "Invoice"),
        ("quotation", "invoice"),
        ("QUOTATION", "INVOICE"),
    ]
    for old, new in replacements:
        html_text = html_text.replace(old, new)
    html_text = html_text.replace(
        '<div class="quote-badge">INVOICE</div>',
        '<div class="invoice-badge">INVOICE</div>',
    )
    html_text = html_text.replace(
        '<div class="quote-badge">QUOTATION</div>',
        '<div class="invoice-badge">INVOICE</div>',
    )
    html_text = html_text.replace(
        "</style>",
        """
    .quote-badge {
      display: none;
    }
    .invoice-badge {
      justify-self: end;
      background: #15318f;
      color: #fff;
      font-weight: 800;
      letter-spacing: 2.6px;
      text-transform: uppercase;
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 16px;
      margin-top: -148px;
    }
  </style>
""",
    )
    return html_text


class QuotationHandler(BaseHTTPRequestHandler):
    server_version = "AstroVoltQuotationServer/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/login"):
            if self.is_authenticated():
                self.redirect("/home")
                return
            self.serve_file(HTML_DIR / "login.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/home":
            if not self.require_auth():
                return
            self.serve_file(HTML_DIR / "home.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/quotation":
            if not self.require_auth():
                return
            self.serve_file(HTML_DIR / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/invoice":
            if not self.require_auth():
                return
            self.serve_file(HTML_DIR / "invoice.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/employees":
            if not self.require_auth():
                return
            self.serve_file(HTML_DIR / "employees.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/attendance":
            if not self.require_auth():
                return
            self.serve_file(HTML_DIR / "attendance.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/holidays":
            if not self.require_auth():
                return
            self.serve_file(HTML_DIR / "holidays.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/salary":
            if not self.require_auth():
                return
            self.serve_file(HTML_DIR / "salary.html", "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/salary-slip/"):
            if not self.require_auth():
                return
            self.handle_salary_slip(parsed.path)
            return
        if parsed.path == "/app.css":
            self.serve_file(CSS_DIR / "app.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self.serve_file(JS_DIR / "app.js", "application/javascript; charset=utf-8")
            return
        if parsed.path.startswith("/js/"):
            self.serve_file(JS_DIR / parsed.path.replace("/js/", ""), "application/javascript; charset=utf-8")
            return
        if parsed.path == "/logo.png":
            self.serve_file(ASSETS_DIR / "logo.png", "image/png")
            return
        if parsed.path == "/api/auth/bootstrap":
            self.handle_auth_bootstrap()
            return
        if parsed.path == "/api/bootstrap":
            if not self.require_auth(for_api=True):
                return
            self.handle_bootstrap()
            return
        if parsed.path == "/api/invoices/bootstrap":
            if not self.require_auth(for_api=True):
                return
            self.handle_invoice_bootstrap()
            return
        if parsed.path == "/api/template":
            if not self.require_auth(for_api=True):
                return
            self.handle_template()
            return
        if parsed.path == "/api/invoices/template":
            if not self.require_auth(for_api=True):
                return
            self.handle_invoice_template()
            return
        if parsed.path.startswith("/print/quotations/"):
            if not self.require_auth():
                return
            self.handle_print_view(parsed.path)
            return
        if parsed.path.startswith("/print/invoices/"):
            if not self.require_auth():
                return
            self.handle_invoice_print_view(parsed.path)
            return
        if parsed.path.startswith("/api/quotations/") and parsed.path.endswith("/export-pdf"):
            if not self.require_auth(for_api=True):
                return
            self.handle_export_pdf(parsed.path)
            return
        if parsed.path.startswith("/api/invoices/") and parsed.path.endswith("/export-pdf"):
            if not self.require_auth(for_api=True):
                return
            self.handle_invoice_export_pdf(parsed.path)
            return
        if parsed.path.startswith("/api/salary/") and parsed.path.endswith("/export-pdf"):
            if not self.require_auth(for_api=True):
                return
            self.handle_salary_export_pdf(parsed.path)
            return
        if parsed.path.startswith("/api/quotations/"):
            if not self.require_auth(for_api=True):
                return
            self.handle_get_quotation(parsed.path)
            return
        if parsed.path.startswith("/api/invoices/"):
            if not self.require_auth(for_api=True):
                return
            self.handle_get_invoice(parsed.path)
            return
        if parsed.path == "/api/employees":
            if not self.require_auth(for_api=True):
                return
            self.handle_employees(parsed)
            return
        if parsed.path.startswith("/api/employees/"):
            if not self.require_auth(for_api=True):
                return
            self.handle_employee_by_id(parsed.path)
            return
        if parsed.path == "/api/attendance":
            if not self.require_auth(for_api=True):
                return
            self.handle_attendance(parsed)
            return
        if parsed.path == "/api/holidays":
            if not self.require_auth(for_api=True):
                return
            self.handle_holidays()
            return
        if parsed.path == "/api/salary":
            if not self.require_auth(for_api=True):
                return
            self.handle_salary_list(parsed)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/auth/setup":
            self.handle_auth_setup()
            return
        if parsed.path == "/api/auth/login":
            self.handle_auth_login()
            return
        if parsed.path == "/api/auth/logout":
            self.handle_auth_logout()
            return
        if parsed.path == "/api/quotations/save-draft":
            if not self.require_auth(for_api=True):
                return
            self.handle_save_draft()
            return
        if parsed.path == "/api/invoices/save-draft":
            if not self.require_auth(for_api=True):
                return
            self.handle_invoice_save_draft()
            return
        if parsed.path == "/api/security/pin":
            if not self.require_auth(for_api=True):
                return
            self.handle_set_pin()
            return
        if parsed.path.startswith("/api/quotations/") and parsed.path.endswith("/finalize"):
            if not self.require_auth(for_api=True):
                return
            self.handle_finalize(parsed.path)
            return
        if parsed.path.startswith("/api/invoices/") and parsed.path.endswith("/finalize"):
            if not self.require_auth(for_api=True):
                return
            self.handle_invoice_finalize(parsed.path)
            return
        if parsed.path.startswith("/api/quotations/") and parsed.path.endswith("/revise"):
            if not self.require_auth(for_api=True):
                return
            self.handle_revise(parsed.path)
            return
        if parsed.path.startswith("/api/invoices/") and parsed.path.endswith("/revise"):
            if not self.require_auth(for_api=True):
                return
            self.handle_invoice_revise(parsed.path)
            return
        if parsed.path == "/api/employees":
            if not self.require_auth(for_api=True):
                return
            self.handle_save_employee()
            return
        if parsed.path == "/api/attendance":
            if not self.require_auth(for_api=True):
                return
            self.handle_save_attendance()
            return
        if parsed.path == "/api/holidays":
            if not self.require_auth(for_api=True):
                return
            self.handle_save_holiday()
            return
        if parsed.path == "/api/holidays/delete":
            if not self.require_auth(for_api=True):
                return
            self.handle_delete_holiday()
            return
        if parsed.path == "/api/salary/generate":
            if not self.require_auth(for_api=True):
                return
            self.handle_salary_generate()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.end_headers()

    def parse_cookies(self) -> dict[str, str]:
        raw = self.headers.get("Cookie", "")
        cookie = SimpleCookie()
        cookie.load(raw)
        return {key: morsel.value for key, morsel in cookie.items()}

    def is_authenticated(self) -> bool:
        token = self.parse_cookies().get(SESSION_COOKIE)
        return get_session(token) is not None

    def require_auth(self, for_api: bool = False) -> bool:
        if self.is_authenticated():
            return True
        if for_api:
            self.write_json(HTTPStatus.UNAUTHORIZED, {"error": "Login required"})
        else:
            self.redirect("/login")
        return False

    def read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def write_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(body)

    def write_html(self, status: int, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(data)

    def write_pdf(self, filename: str, data: bytes) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'inline; filename="{filename}"')
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(data)

    def write_pdf_download(self, filename: str, data: bytes) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(data)

    def serve_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(data)

    def handle_auth_bootstrap(self) -> None:
        with db_connect() as connection:
            self.write_json(HTTPStatus.OK, {"configured": auth_configured(connection)})

    def handle_auth_setup(self) -> None:
        try:
            body = self.read_json()
            username = clean_text(body.get("username"))
            password = clean_text(body.get("password"))
            if not username or not password:
                raise ValueError("Username and password are required")
            if len(password) < 6:
                raise ValueError("Password must be at least 6 characters")
            with db_connect() as connection:
                if auth_configured(connection):
                    raise PermissionError("Admin user already configured")
                set_admin_user(connection, username, password)
                connection.commit()
            self.write_json(HTTPStatus.OK, {"message": "Admin user created"})
        except PermissionError as error:
            self.write_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except ValueError as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def handle_auth_login(self) -> None:
        try:
            body = self.read_json()
            username = clean_text(body.get("username"))
            password = clean_text(body.get("password"))
            with db_connect() as connection:
                if not verify_admin_user(connection, username, password):
                    raise PermissionError("Invalid username or password")
            token = create_session(username)
            body = json.dumps({"message": "Login successful"}).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header(
                "Set-Cookie",
                f"{SESSION_COOKIE}={token}; HttpOnly; SameSite=Lax; Path=/",
            )
            self.end_headers()
            self.wfile.write(body)
        except PermissionError as error:
            self.write_json(HTTPStatus.UNAUTHORIZED, {"error": str(error)})

    def handle_auth_logout(self) -> None:
        token = self.parse_cookies().get(SESSION_COOKIE)
        clear_session(token)
        body = json.dumps({"message": "Logged out"}).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE}=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/",
        )
        self.end_headers()
        self.wfile.write(body)

    def handle_bootstrap(self) -> None:
        with db_connect() as connection:
            self.write_json(
                HTTPStatus.OK,
                {
                    "records": quote_summary(connection),
                    "pin_configured": pin_configured(connection),
                    "database_path": str(DATABASE_PATH),
                },
            )

    def handle_template(self) -> None:
        with db_connect() as connection:
            self.write_json(
                HTTPStatus.OK,
                {
                    "quotation": default_quote_payload(connection),
                    "pin_configured": pin_configured(connection),
                },
            )

    def handle_invoice_bootstrap(self) -> None:
        with db_connect() as connection:
            self.write_json(
                HTTPStatus.OK,
                {
                    "records": invoice_summary(connection),
                    "pin_configured": pin_configured(connection),
                    "database_path": str(DATABASE_PATH),
                    "quotations": quote_summary(connection),
                },
            )

    def handle_invoice_template(self) -> None:
        with db_connect() as connection:
            self.write_json(
                HTTPStatus.OK,
                {
                    "invoice": default_invoice_payload(connection),
                    "pin_configured": pin_configured(connection),
                },
            )

    def handle_get_quotation(self, path: str) -> None:
        try:
            quote_id = int(path.rstrip("/").split("/")[-1])
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid quotation id")
            return
        with db_connect() as connection:
            row = get_quote(connection, quote_id)
            if row is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Quotation not found")
                return
            self.write_json(HTTPStatus.OK, quote_row_to_dict(row, include_payload=True))

    def handle_get_invoice(self, path: str) -> None:
        try:
            invoice_id = int(path.rstrip("/").split("/")[-1])
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid invoice id")
            return
        with db_connect() as connection:
            row = get_invoice(connection, invoice_id)
            if row is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Invoice not found")
                return
            self.write_json(HTTPStatus.OK, invoice_row_to_dict(row, include_payload=True))

    def handle_print_view(self, path: str) -> None:
        try:
            quote_id = int(path.rstrip("/").split("/")[-1])
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid quotation id")
            return
        with db_connect() as connection:
            row = get_quote(connection, quote_id)
            if row is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Quotation not found")
                return
            payload = quote_row_to_dict(row, include_payload=True)["quotation"]
            self.write_html(HTTPStatus.OK, quote_document_html(payload))

    def handle_invoice_print_view(self, path: str) -> None:
        try:
            invoice_id = int(path.rstrip("/").split("/")[-1])
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid invoice id")
            return
        with db_connect() as connection:
            row = get_invoice(connection, invoice_id)
            if row is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Invoice not found")
                return
            payload = invoice_row_to_dict(row, include_payload=True)["invoice"]
            self.write_html(HTTPStatus.OK, invoice_document_html(payload))

    def handle_export_pdf(self, path: str) -> None:
        try:
            quote_id = int(path.rstrip("/").split("/")[-2])
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid quotation id")
            return
        try:
            with db_connect() as connection:
                row = get_quote(connection, quote_id)
                if row is None:
                    self.send_error(HTTPStatus.NOT_FOUND, "Quotation not found")
                    return
                payload = quote_row_to_dict(row, include_payload=True)["quotation"]
                pdf_path = export_quote_pdf(
                    quote_id,
                    row["display_number"],
                    payload,
                )
                record_event(connection, quote_id, "EXPORT_PDF", str(pdf_path))
                connection.commit()
            self.write_pdf(pdf_path.name, pdf_path.read_bytes())
        except FileNotFoundError as error:
            self.write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})
        except subprocess.CalledProcessError as error:
            message = error.stderr.decode("utf-8", errors="ignore").strip() or "PDF export command failed"
            self.write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": message})
        except (OSError, RuntimeError) as error:
            self.write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})

    def handle_invoice_export_pdf(self, path: str) -> None:
        try:
            invoice_id = int(path.rstrip("/").split("/")[-2])
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid invoice id")
            return
        try:
            with db_connect() as connection:
                row = get_invoice(connection, invoice_id)
                if row is None:
                    self.send_error(HTTPStatus.NOT_FOUND, "Invoice not found")
                    return
                payload = invoice_row_to_dict(row, include_payload=True)["invoice"]
                pdf_path = export_invoice_pdf(
                    invoice_id,
                    row["display_number"],
                    payload,
                )
                record_invoice_event(connection, invoice_id, "EXPORT_PDF", str(pdf_path))
                connection.commit()
            self.write_pdf(pdf_path.name, pdf_path.read_bytes())
        except FileNotFoundError as error:
            self.write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})
        except subprocess.CalledProcessError as error:
            message = error.stderr.decode("utf-8", errors="ignore").strip() or "PDF export command failed"
            self.write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": message})
        except (OSError, RuntimeError) as error:
            self.write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})

    def handle_save_draft(self) -> None:
        try:
            body = self.read_json()
            quotation = body.get("quotation", {})
            if not isinstance(quotation, dict):
                raise ValueError("Quotation payload must be an object")
            with db_connect() as connection:
                saved = save_draft(connection, quotation)
                connection.commit()
                self.write_json(
                    HTTPStatus.OK,
                    {
                        "message": "Draft saved",
                        "record": saved,
                        "records": quote_summary(connection),
                    },
                )
        except PermissionError as error:
            self.write_json(HTTPStatus.CONFLICT, {"error": str(error)})
        except (KeyError, ValueError, sqlite3.IntegrityError) as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def handle_invoice_save_draft(self) -> None:
        try:
            body = self.read_json()
            invoice = body.get("invoice", {})
            if not isinstance(invoice, dict):
                raise ValueError("Invoice payload must be an object")
            with db_connect() as connection:
                saved = save_invoice_draft(connection, invoice)
                connection.commit()
                self.write_json(
                    HTTPStatus.OK,
                    {
                        "message": "Draft saved",
                        "record": saved,
                        "records": invoice_summary(connection),
                    },
                )
        except PermissionError as error:
            self.write_json(HTTPStatus.CONFLICT, {"error": str(error)})
        except (KeyError, ValueError, sqlite3.IntegrityError) as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def handle_finalize(self, path: str) -> None:
        try:
            quote_id = int(path.rstrip("/").split("/")[-2])
            body = self.read_json()
            pin = clean_text(body.get("pin"))
            with db_connect() as connection:
                saved = finalize_quote(connection, quote_id, pin)
                connection.commit()
                self.write_json(
                    HTTPStatus.OK,
                    {
                        "message": "Quotation finalised and locked",
                        "record": saved,
                        "records": quote_summary(connection),
                    },
                )
        except PermissionError as error:
            self.write_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except (KeyError, ValueError, sqlite3.IntegrityError) as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def handle_invoice_finalize(self, path: str) -> None:
        try:
            invoice_id = int(path.rstrip("/").split("/")[-2])
            body = self.read_json()
            pin = clean_text(body.get("pin"))
            with db_connect() as connection:
                saved = finalize_invoice(connection, invoice_id, pin)
                connection.commit()
                self.write_json(
                    HTTPStatus.OK,
                    {
                        "message": "Invoice finalised and locked",
                        "record": saved,
                        "records": invoice_summary(connection),
                    },
                )
        except PermissionError as error:
            self.write_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except (KeyError, ValueError, sqlite3.IntegrityError) as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def handle_revise(self, path: str) -> None:
        try:
            quote_id = int(path.rstrip("/").split("/")[-2])
            body = self.read_json()
            pin = clean_text(body.get("pin"))
            with db_connect() as connection:
                saved = create_revision(connection, quote_id, pin)
                connection.commit()
                self.write_json(
                    HTTPStatus.OK,
                    {
                        "message": "Revision draft created",
                        "record": saved,
                        "records": quote_summary(connection),
                    },
                )
        except PermissionError as error:
            self.write_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except (KeyError, ValueError, sqlite3.IntegrityError) as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def handle_invoice_revise(self, path: str) -> None:
        try:
            invoice_id = int(path.rstrip("/").split("/")[-2])
            body = self.read_json()
            pin = clean_text(body.get("pin"))
            with db_connect() as connection:
                saved = create_invoice_revision(connection, invoice_id, pin)
                connection.commit()
                self.write_json(
                    HTTPStatus.OK,
                    {
                        "message": "Revision draft created",
                        "record": saved,
                        "records": invoice_summary(connection),
                    },
                )
        except PermissionError as error:
            self.write_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except (KeyError, ValueError, sqlite3.IntegrityError) as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def handle_set_pin(self) -> None:
        try:
            body = self.read_json()
            current_pin = clean_text(body.get("current_pin"))
            new_pin = clean_text(body.get("new_pin"))
            if len(new_pin) < 4:
                raise ValueError("PIN must be at least 4 characters")
            with db_connect() as connection:
                if pin_configured(connection):
                    if not current_pin:
                        raise PermissionError("Current PIN is required")
                    if not verify_admin_pin(connection, current_pin):
                        raise PermissionError("Current PIN is incorrect")
                set_admin_pin(connection, new_pin)
                connection.commit()
                self.write_json(
                    HTTPStatus.OK,
                    {
                        "message": "Admin PIN saved",
                        "pin_configured": True,
                    },
                )
        except PermissionError as error:
            self.write_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except ValueError as error:
                self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def handle_employees(self, parsed) -> None:
        with db_connect_hr() as connection:
            records = list_employees(connection)
            self.write_json(
                HTTPStatus.OK,
                {
                    "records": records,
                    "next_employee_code": next_employee_code(connection),
                },
            )

    def handle_employee_by_id(self, path: str) -> None:
        try:
            employee_id = int(path.rstrip("/").split("/")[-1])
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid employee id")
            return
        with db_connect_hr() as connection:
            row = get_employee(connection, employee_id)
            if row is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Employee not found")
                return
            self.write_json(HTTPStatus.OK, {"employee": employee_row_to_dict(row)})

    def handle_save_employee(self) -> None:
        try:
            body = self.read_json()
            employee = body.get("employee", {})
            if not isinstance(employee, dict):
                raise ValueError("Employee payload must be an object")
            with db_connect_hr() as connection:
                saved = save_employee(connection, employee)
                connection.commit()
                self.write_json(
                    HTTPStatus.OK,
                    {
                        "message": "Employee saved",
                        "employee": saved,
                        "records": list_employees(connection),
                    },
                )
        except PermissionError as error:
            self.write_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except (ValueError, sqlite3.IntegrityError) as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def handle_attendance(self, parsed) -> None:
        params = parse_qs(parsed.query)
        try:
            employee_id = int(params.get("employee_id", ["0"])[0])
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid employee id")
            return
        month = clean_text(params.get("month", [""])[0])
        if not employee_id or not month:
            self.send_error(HTTPStatus.BAD_REQUEST, "employee_id and month are required")
            return
        with db_connect_hr() as connection:
            employee_row = get_employee(connection, employee_id)
            if employee_row is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Employee not found")
                return
            employee = employee_row_to_dict(employee_row)
            entries = effective_attendance_entries(connection, employee, month)
            summary = attendance_summary(entries)
            leave_balance = to_float(employee.get("leave_balance", 0))
            leave_used = summary.get("leave_days", 0)
            self.write_json(
                HTTPStatus.OK,
                {
                    "entries": entries,
                    "summary": summary,
                    "leave_balance": leave_balance,
                    "leave_used": leave_used,
                    "leave_remaining": round(leave_balance - leave_used, 2),
                },
            )

    def handle_save_attendance(self) -> None:
        try:
            body = self.read_json()
            entry = body.get("attendance", {})
            if not isinstance(entry, dict):
                raise ValueError("Attendance payload must be an object")
            with db_connect_hr() as connection:
                saved = save_attendance(connection, entry)
                connection.commit()
                self.write_json(HTTPStatus.OK, {"attendance": saved})
        except PermissionError as error:
            self.write_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except (ValueError, sqlite3.IntegrityError) as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def handle_salary_list(self, parsed) -> None:
        params = parse_qs(parsed.query)
        month = clean_text(params.get("month", [""])[0])
        sort_key = clean_text(params.get("sort", ["name"])[0]) or "name"
        if sort_key not in ("name", "code"):
            sort_key = "name"
        with db_connect_hr() as connection:
            if month:
                rows = connection.execute(
                    """
                    SELECT s.*, e.full_name, e.employee_code
                    FROM salary_runs s
                    JOIN employees e ON e.id = s.employee_id
                    WHERE s.month = ?
                    ORDER BY CASE WHEN ? = 'code' THEN e.employee_code ELSE e.full_name END ASC
                    """,
                    (month, sort_key),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT s.*, e.full_name, e.employee_code
                    FROM salary_runs s
                    JOIN employees e ON e.id = s.employee_id
                    ORDER BY CASE WHEN ? = 'code' THEN e.employee_code ELSE e.full_name END ASC
                    """,
                    (sort_key,),
                ).fetchall()
            records = []
            for row in rows:
                item = salary_row_to_dict(row)
                item["employee_name"] = row["full_name"]
                item["employee_code"] = row["employee_code"]
                records.append(item)
            self.write_json(HTTPStatus.OK, {"records": records})

    def handle_salary_generate(self) -> None:
        try:
            body = self.read_json()
            employee_id = int(body.get("employee_id", 0))
            month = clean_text(body.get("month"))
            other_deductions = to_float(body.get("other_deductions", 0))
            advance = to_float(body.get("advance", 0))
            if not employee_id or not month:
                raise ValueError("employee_id and month are required")
            with db_connect_hr() as connection:
                employee_row = get_employee(connection, employee_id)
                if employee_row is None:
                    raise KeyError("Employee not found")
                employee = employee_row_to_dict(employee_row)
                entries = effective_attendance_entries(connection, employee, month)
                summary = attendance_summary(entries)
                computed = calculate_salary(employee, month, summary, other_deductions, advance)
                now = utc_now_text()
                connection.execute(
                    """
                    INSERT INTO salary_runs(
                        employee_id, month, days_in_month, present_days, absent_days, half_days, overtime_hours,
                        base_salary, allowances, overtime_amount, lop_amount, pf_amount, esi_amount,
                        other_deductions, advance, net_pay, created_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(employee_id, month) DO UPDATE SET
                        days_in_month = excluded.days_in_month,
                        present_days = excluded.present_days,
                        absent_days = excluded.absent_days,
                        half_days = excluded.half_days,
                        overtime_hours = excluded.overtime_hours,
                        base_salary = excluded.base_salary,
                        allowances = excluded.allowances,
                        overtime_amount = excluded.overtime_amount,
                        lop_amount = excluded.lop_amount,
                        pf_amount = excluded.pf_amount,
                        esi_amount = excluded.esi_amount,
                        other_deductions = excluded.other_deductions,
                        advance = excluded.advance,
                        net_pay = excluded.net_pay,
                        updated_at = excluded.updated_at
                    """,
                    (
                        employee_id,
                        computed["month"],
                        computed["days_in_month"],
                        computed["present_days"],
                        computed["absent_days"],
                        computed["half_days"],
                        computed["overtime_hours"],
                        computed["base_salary"],
                        computed["allowances"],
                        computed["overtime_amount"],
                        computed["lop_amount"],
                        computed["pf_amount"],
                        computed["esi_amount"],
                        computed["other_deductions"],
                        computed["advance"],
                        computed["net_pay"],
                        now,
                        now,
                    ),
                )
                row = connection.execute(
                    "SELECT id FROM salary_runs WHERE employee_id = ? AND month = ?",
                    (employee_id, computed["month"]),
                ).fetchone()
                connection.commit()
                self.write_json(HTTPStatus.OK, {"salary": computed, "salary_run_id": row["id"]})
        except (ValueError, KeyError, sqlite3.IntegrityError) as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def handle_salary_slip(self, path: str) -> None:
        try:
            run_id = int(path.rstrip("/").split("/")[-1])
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid salary run id")
            return
        with db_connect_hr() as connection:
            row = connection.execute(
                """
                SELECT s.*, e.full_name, e.employee_code, e.department, e.designation, e.bank_name, e.bank_account
                FROM salary_runs s
                JOIN employees e ON e.id = s.employee_id
                WHERE s.id = ?
                """,
                (run_id,),
            ).fetchone()
            if row is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Salary run not found")
                return
            html_body = salary_slip_html(row)
            self.write_html(HTTPStatus.OK, html_body)

    def handle_salary_export_pdf(self, path: str) -> None:
        try:
            run_id = int(path.rstrip("/").split("/")[-2])
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid salary run id")
            return
        try:
            with db_connect_hr() as connection:
                row = connection.execute(
                    """
                    SELECT s.*, e.full_name, e.employee_code, e.department, e.designation, e.bank_name, e.bank_account
                    FROM salary_runs s
                    JOIN employees e ON e.id = s.employee_id
                    WHERE s.id = ?
                    """,
                    (run_id,),
                ).fetchone()
                if row is None:
                    self.send_error(HTTPStatus.NOT_FOUND, "Salary run not found")
                    return
                pdf_path = export_salary_pdf(run_id, row)
            self.write_pdf_download(pdf_path.name, pdf_path.read_bytes())
        except FileNotFoundError as error:
            self.write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})
        except subprocess.CalledProcessError as error:
            message = error.stderr.decode("utf-8", errors="ignore").strip() or "PDF export command failed"
            self.write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": message})
        except (OSError, RuntimeError) as error:
            self.write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})

    def handle_holidays(self) -> None:
        with db_connect_hr() as connection:
            rows = connection.execute(
                "SELECT * FROM holidays ORDER BY holiday_date ASC"
            ).fetchall()
            records = []
            for row in rows:
                records.append(
                    {
                        "id": row["id"],
                        "holiday_date": row["holiday_date"],
                        "title": row["title"],
                        "created_at": row["created_at"],
                    }
                )
            self.write_json(HTTPStatus.OK, {"records": records})

    def handle_save_holiday(self) -> None:
        try:
            body = self.read_json()
            holiday = body.get("holiday", {})
            if not isinstance(holiday, dict):
                raise ValueError("Holiday payload must be an object")
            holiday_date = clean_text(holiday.get("holiday_date"))
            title = clean_text(holiday.get("title"))
            if not holiday_date or not title:
                raise ValueError("holiday_date and title are required")
            now = utc_now_text()
            with db_connect_hr() as connection:
                connection.execute(
                    """
                    INSERT INTO holidays(holiday_date, title, created_at)
                    VALUES(?, ?, ?)
                    ON CONFLICT(holiday_date) DO UPDATE SET title = excluded.title
                    """,
                    (holiday_date, title, now),
                )
                connection.commit()
                self.write_json(HTTPStatus.OK, {"message": "Holiday saved"})
        except (ValueError, sqlite3.IntegrityError) as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def handle_delete_holiday(self) -> None:
        try:
            body = self.read_json()
            holiday_id = int(body.get("holiday_id", 0))
            if not holiday_id:
                raise ValueError("holiday_id is required")
            with db_connect_hr() as connection:
                connection.execute("DELETE FROM holidays WHERE id = ?", (holiday_id,))
                connection.commit()
            self.write_json(HTTPStatus.OK, {"message": "Holiday deleted"})
        except (ValueError, sqlite3.IntegrityError) as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AstroVolt quotation management server")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    init_db()
    server = ThreadingHTTPServer((args.host, args.port), QuotationHandler)
    print(f"AstroVolt quotation server running at http://{args.host}:{args.port}")
    print(f"SQLite database: {DATABASE_PATH}")
    print(f"HR database: {HR_DATABASE_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    main()
