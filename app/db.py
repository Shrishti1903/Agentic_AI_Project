"""SQLite storage and persistence layer for expense receipts.

Provides:
- Schema initialization (receipts and receipt_items tables)
- Receipt persistence with full structured JSON payload
- 24-hour duplicate transaction detection
- Employee expense history and lookup
"""
import os
import json
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

DEFAULT_DB_PATH = "expenses.db"


def get_db_path(db_path: Optional[str] = None) -> str:
    """Resolve database path from argument, environment variable, or default."""
    if db_path:
        return db_path
    return os.environ.get("EXPENSE_DB_PATH", DEFAULT_DB_PATH)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and configure a SQLite connection with Row factory."""
    resolved_path = get_db_path(db_path)
    conn = sqlite3.connect(resolved_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite database schema."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                department_id TEXT NOT NULL,
                vendor TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT,
                category TEXT,
                confidence REAL,
                recommendation TEXT,
                status TEXT,
                raw_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_receipts_employee ON receipts(employee_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_receipts_vendor_amount ON receipts(vendor, amount);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_receipts_created_at ON receipts(created_at);
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receipt_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id TEXT NOT NULL,
                name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                price REAL NOT NULL,
                FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id) ON DELETE CASCADE
            );
        """)
        conn.commit()


def save_receipt(
    receipt_data: Dict[str, Any],
    employee_id: str,
    department_id: str,
    db_path: Optional[str] = None
) -> str:
    """Persist receipt data and items into SQLite.
    
    Returns the receipt_id.
    """
    init_db(db_path)
    receipt_id = receipt_data.get("receiptId", "rcpt_demo_001")
    extraction = receipt_data.get("extraction", {})
    categorization = receipt_data.get("categorization", {})
    compliance = receipt_data.get("compliance", {})
    approval = receipt_data.get("approval", {})

    vendor = extraction.get("vendor", "Unknown")
    amount = float(extraction.get("amount", 0.0) or 0.0)
    currency = extraction.get("currency", "USD")
    date_str = extraction.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
    time_str = extraction.get("time")
    category = categorization.get("category", extraction.get("category", "Other"))
    confidence = float(extraction.get("confidence", 0.0) or 0.0)
    recommendation = approval.get("recommendation", "NEEDS_REVIEW")
    status = compliance.get("status", "NEEDS_REVIEW")
    raw_json = json.dumps(receipt_data)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO receipts (
                receipt_id, employee_id, department_id, vendor, amount,
                currency, date, time, category, confidence, recommendation,
                status, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            receipt_id, employee_id, department_id, vendor, amount,
            currency, date_str, time_str, category, confidence,
            recommendation, status, raw_json
        ))

        # Remove existing items if replacing
        cursor.execute("DELETE FROM receipt_items WHERE receipt_id = ?", (receipt_id,))

        items = extraction.get("items", [])
        for itm in items:
            name = itm.get("name", "")
            qty = itm.get("quantity", 1) or 1
            price = float(itm.get("price", 0.0) or 0.0)
            cursor.execute("""
                INSERT INTO receipt_items (receipt_id, name, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (receipt_id, name, qty, price))

        conn.commit()

    return receipt_id


def check_duplicate_receipt(
    employee_id: str,
    vendor: str,
    amount: float,
    receipt_date: Optional[str] = None,
    hours_window: int = 24,
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Check if the employee submitted a duplicate receipt within `hours_window` or on the same date.
    
    A duplicate is defined as identical employee, vendor (case-insensitive), and amount.
    Returns the matching receipt record if detected, else None.
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Query receipts matching employee, vendor and amount
        cursor.execute("""
            SELECT receipt_id, employee_id, department_id, vendor, amount,
                   date, time, category, recommendation, status, created_at
            FROM receipts
            WHERE employee_id = ?
              AND LOWER(vendor) = LOWER(?)
              AND ABS(amount - ?) < 0.01
            ORDER BY created_at DESC
        """, (employee_id, vendor.strip(), amount))

        rows = cursor.fetchall()
        for row in rows:
            created_at_str = row["created_at"]
            is_within_window = False
            if created_at_str:
                try:
                    # SQLite CURRENT_TIMESTAMP is in UTC format YYYY-MM-DD HH:MM:SS
                    created_dt = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
                    if datetime.utcnow() - created_dt <= timedelta(hours=hours_window):
                        is_within_window = True
                except Exception:
                    pass

            # Also check if same date string
            if receipt_date and row["date"] and row["date"] == receipt_date:
                is_within_window = True

            if is_within_window or not created_at_str:
                return dict(row)

    return None


def get_receipt(receipt_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve receipt details and full parsed JSON by receipt_id."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT receipt_id, employee_id, department_id, vendor, amount,
                   currency, date, time, category, confidence, recommendation,
                   status, raw_json, created_at
            FROM receipts
            WHERE receipt_id = ?
        """, (receipt_id,))
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        try:
            data["parsed_response"] = json.loads(data["raw_json"])
        except Exception:
            data["parsed_response"] = None
        return data


def get_employee_history(
    employee_id: str,
    limit: int = 50,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve expense history for a given employee."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT receipt_id, employee_id, department_id, vendor, amount,
                   currency, date, time, category, confidence, recommendation,
                   status, created_at
            FROM receipts
            WHERE employee_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (employee_id, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_all_receipts(
    limit: int = 100,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve recent receipts across the organization."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT receipt_id, employee_id, department_id, vendor, amount,
                   currency, date, time, category, confidence, recommendation,
                   status, created_at
            FROM receipts
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_analytics_summary(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Compute overall expense metrics, approval rates, and anomaly statistics."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM receipts")
        total_receipts = cursor.fetchone()[0] or 0

        if total_receipts == 0:
            return {
                "totalReceipts": 0,
                "todayExpenses": 0.0,
                "thisMonthExpenses": 0.0,
                "averageApprovalTime": "2 min",
                "anomalyRate": "0.0%",
                "approvalRate": "100.0%"
            }

        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0.0) FROM receipts
            WHERE date(created_at) = date('now')
               OR date = strftime('%Y-%m-%d', 'now')
        """)
        today_expenses = cursor.fetchone()[0] or 0.0

        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0.0) FROM receipts
            WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
               OR strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
        """)
        month_expenses = cursor.fetchone()[0] or 0.0

        cursor.execute("""
            SELECT COUNT(*) FROM receipts
            WHERE recommendation = 'AUTO_APPROVE' AND status = 'APPROVED'
        """)
        approved_count = cursor.fetchone()[0] or 0
        flagged_count = total_receipts - approved_count

        anomaly_rate = (flagged_count / total_receipts) * 100.0
        approval_rate = (approved_count / total_receipts) * 100.0

        return {
            "totalReceipts": total_receipts,
            "todayExpenses": round(float(today_expenses), 2),
            "thisMonthExpenses": round(float(month_expenses), 2),
            "averageApprovalTime": "2 min",
            "anomalyRate": f"{anomaly_rate:.1f}%",
            "approvalRate": f"{approval_rate:.1f}%"
        }


def get_analytics_trends(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Compute spending breakdown by category, department, and employee."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT category, COUNT(*) as count, COALESCE(SUM(amount), 0.0) as total
            FROM receipts
            GROUP BY category
            ORDER BY total DESC
        """)
        by_category = [
            {"category": row["category"] or "Other", "count": row["count"], "total": round(float(row["total"]), 2)}
            for row in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT department_id, COUNT(*) as count, COALESCE(SUM(amount), 0.0) as total
            FROM receipts
            GROUP BY department_id
            ORDER BY total DESC
        """)
        by_department = [
            {"department": row["department_id"] or "Unknown", "count": row["count"], "total": round(float(row["total"]), 2)}
            for row in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT employee_id, COUNT(*) as count, COALESCE(SUM(amount), 0.0) as total
            FROM receipts
            GROUP BY employee_id
            ORDER BY total DESC
        """)
        by_employee = [
            {"employeeId": row["employee_id"] or "Unknown", "count": row["count"], "total": round(float(row["total"]), 2)}
            for row in cursor.fetchall()
        ]

        return {
            "byCategory": by_category,
            "byDepartment": by_department,
            "byEmployee": by_employee
        }


def get_flagged_receipts(limit: int = 20, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve list of flagged or rejected receipts requiring compliance review."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT receipt_id, employee_id, vendor, amount, status, recommendation, raw_json
            FROM receipts
            WHERE recommendation != 'AUTO_APPROVE' OR status != 'APPROVED'
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        flagged = []
        for row in cursor.fetchall():
            reason = "Policy review required"
            try:
                parsed = json.loads(row["raw_json"])
                reason = parsed.get("approval", {}).get("reason") or reason
            except Exception:
                pass

            flagged.append({
                "receiptId": row["receipt_id"],
                "employeeId": row["employee_id"],
                "vendor": row["vendor"],
                "amount": round(float(row["amount"]), 2),
                "reason": reason,
                "status": row["status"]
            })
        return flagged

