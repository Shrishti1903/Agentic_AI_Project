import os
import pytest
from fastapi.testclient import TestClient
from app.db import (
    init_db,
    save_receipt,
    get_receipt,
    check_duplicate_receipt,
    get_employee_history,
    get_all_receipts
)
from app.main import app

# Fixture to provide an isolated temporary SQLite database for tests
@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_expenses.db")
    monkeypatch.setenv("EXPENSE_DB_PATH", db_file)
    init_db(db_file)
    return db_file


def test_init_and_save_receipt(temp_db):
    sample_data = {
        "receiptId": "rcpt_test_001",
        "extraction": {
            "vendor": "Staples",
            "amount": 45.50,
            "currency": "USD",
            "date": "2026-09-18",
            "time": "10:15 AM",
            "itemsCount": 2,
            "items": [
                {"name": "Printer Paper", "quantity": 2, "price": 20.00},
                {"name": "Pens", "quantity": 1, "price": 5.50}
            ],
            "confidence": 0.95
        },
        "categorization": {
            "category": "Office Supplies",
            "confidence": 0.95,
            "reasoning": "Vendor Staples"
        },
        "compliance": {
            "status": "APPROVED",
            "policyChecks": [],
            "anomalies": []
        },
        "approval": {
            "recommendation": "AUTO_APPROVE",
            "reason": "Clean receipt"
        }
    }

    rcpt_id = save_receipt(sample_data, "emp_001", "dept_ops", db_path=temp_db)
    assert rcpt_id == "rcpt_test_001"

    fetched = get_receipt("rcpt_test_001", db_path=temp_db)
    assert fetched is not None
    assert fetched["vendor"] == "Staples"
    assert abs(fetched["amount"] - 45.50) < 0.001
    assert fetched["category"] == "Office Supplies"
    assert fetched["recommendation"] == "AUTO_APPROVE"
    assert fetched["parsed_response"]["extraction"]["itemsCount"] == 2


def test_duplicate_detection(temp_db):
    sample_data = {
        "receiptId": "rcpt_dup_1",
        "extraction": {
            "vendor": "Starbucks",
            "amount": 14.50,
            "currency": "USD",
            "date": "2026-09-19",
            "items": [{"name": "Latte", "quantity": 2, "price": 14.50}],
            "confidence": 0.98
        },
        "categorization": {"category": "Meals & Entertainment", "confidence": 0.9},
        "compliance": {"status": "APPROVED", "policyChecks": [], "anomalies": []},
        "approval": {"recommendation": "AUTO_APPROVE"}
    }

    # Before saving, no duplicate
    dup = check_duplicate_receipt("emp_100", "Starbucks", 14.50, "2026-09-19", db_path=temp_db)
    assert dup is None

    save_receipt(sample_data, "emp_100", "dept_eng", db_path=temp_db)

    # Now duplicate should be detected for same employee, vendor, amount
    dup_found = check_duplicate_receipt("emp_100", "Starbucks", 14.50, "2026-09-19", db_path=temp_db)
    assert dup_found is not None
    assert dup_found["receipt_id"] == "rcpt_dup_1"

    # Case insensitive vendor check
    dup_case = check_duplicate_receipt("emp_100", "starbucks", 14.50, "2026-09-19", db_path=temp_db)
    assert dup_case is not None

    # Different employee should not flag duplicate
    diff_emp = check_duplicate_receipt("emp_200", "Starbucks", 14.50, "2026-09-19", db_path=temp_db)
    assert diff_emp is None

    # Different amount should not flag duplicate
    diff_amt = check_duplicate_receipt("emp_100", "Starbucks", 25.00, "2026-09-19", db_path=temp_db)
    assert diff_amt is None


def test_employee_history_and_all_receipts(temp_db):
    for i in range(3):
        data = {
            "receiptId": f"rcpt_hist_{i}",
            "extraction": {"vendor": f"Vendor {i}", "amount": 10.0 * (i + 1), "date": "2026-09-19", "items": []},
            "categorization": {"category": "Other", "confidence": 0.8},
            "compliance": {"status": "APPROVED", "policyChecks": [], "anomalies": []},
            "approval": {"recommendation": "AUTO_APPROVE"}
        }
        save_receipt(data, "emp_hist", "dept_sales", db_path=temp_db)

    history = get_employee_history("emp_hist", db_path=temp_db)
    assert len(history) == 3

    all_rcpts = get_all_receipts(db_path=temp_db)
    assert len(all_rcpts) == 3


def test_api_receipt_persistence_and_duplicate_flow(temp_db):
    client = TestClient(app)

    # 1. First submission
    files = {'image': ('sample.jpg', b'receipt-bytes', 'image/jpeg')}
    data = {'employeeId': 'emp_qa', 'departmentId': 'dept_qa'}
    resp1 = client.post('/api/parse-receipt', data=data, files=files)
    assert resp1.status_code == 200
    j1 = resp1.json()
    assert j1['approval']['recommendation'] == 'AUTO_APPROVE'
    receipt_id = j1['receiptId']

    # 2. Fetch stored receipt by ID
    get_resp = client.get(f'/api/receipts/{receipt_id}')
    assert get_resp.status_code == 200
    assert get_resp.json()['receipt_id'] == receipt_id
    assert get_resp.json()['employee_id'] == 'emp_qa'

    # 3. Second identical submission triggers 24h duplicate anomaly
    files2 = {'image': ('sample.jpg', b'receipt-bytes', 'image/jpeg')}
    resp2 = client.post('/api/parse-receipt', data=data, files=files2)
    assert resp2.status_code == 200
    j2 = resp2.json()
    assert j2['approval']['recommendation'] == 'NEEDS_REVIEW'
    anomaly_types = [a['type'] for a in j2['compliance']['anomalies']]
    assert 'duplicate_transaction' in anomaly_types

    # 4. Fetch employee receipts list endpoint
    emp_resp = client.get('/api/receipts/employee/emp_qa')
    assert emp_resp.status_code == 200
    assert len(emp_resp.json()) >= 1

    # 5. Fetch 404 for unknown receipt
    not_found = client.get('/api/receipts/non_existent_rcpt')
    assert not_found.status_code == 404
