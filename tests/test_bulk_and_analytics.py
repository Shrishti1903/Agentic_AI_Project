import os
import pytest
from fastapi.testclient import TestClient
from app.db import (
    init_db,
    save_receipt,
    get_analytics_summary,
    get_analytics_trends,
    get_flagged_receipts
)
from app.main import app

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_analytics.db")
    monkeypatch.setenv("EXPENSE_DB_PATH", db_file)
    init_db(db_file)
    return db_file


def test_analytics_empty_database(temp_db):
    summary = get_analytics_summary(db_path=temp_db)
    assert summary["totalReceipts"] == 0
    assert summary["todayExpenses"] == 0.0
    assert summary["anomalyRate"] == "0.0%"
    assert summary["approvalRate"] == "100.0%"

    trends = get_analytics_trends(db_path=temp_db)
    assert trends["byCategory"] == []
    assert trends["byDepartment"] == []
    assert trends["byEmployee"] == []

    flagged = get_flagged_receipts(db_path=temp_db)
    assert flagged == []


def test_analytics_aggregations(temp_db):
    # Insert 3 receipts: 2 approved, 1 flagged
    r1 = {
        "receiptId": "rcpt_an_1",
        "extraction": {"vendor": "Uber", "amount": 35.00, "date": "2026-09-19", "items": []},
        "categorization": {"category": "Travel", "confidence": 0.95},
        "compliance": {"status": "APPROVED", "policyChecks": [], "anomalies": []},
        "approval": {"recommendation": "AUTO_APPROVE", "reason": "Standard ride"}
    }
    r2 = {
        "receiptId": "rcpt_an_2",
        "extraction": {"vendor": "Delta", "amount": 250.00, "date": "2026-09-19", "items": []},
        "categorization": {"category": "Travel", "confidence": 0.9},
        "compliance": {"status": "APPROVED", "policyChecks": [], "anomalies": []},
        "approval": {"recommendation": "AUTO_APPROVE", "reason": "Flight"}
    }
    r3 = {
        "receiptId": "rcpt_an_3",
        "extraction": {"vendor": "Luxury Lounge", "amount": 180.00, "date": "2026-09-19", "items": []},
        "categorization": {"category": "Meals & Entertainment", "confidence": 0.85},
        "compliance": {"status": "NEEDS_REVIEW", "policyChecks": [], "anomalies": [{"type": "budget_exceed", "message": "Exceeds daily limit", "severity": "high"}]},
        "approval": {"recommendation": "NEEDS_REVIEW", "reason": "Exceeds $150 limit"}
    }

    save_receipt(r1, "emp_sales_1", "dept_sales", db_path=temp_db)
    save_receipt(r2, "emp_eng_1", "dept_eng", db_path=temp_db)
    save_receipt(r3, "emp_sales_1", "dept_sales", db_path=temp_db)

    summary = get_analytics_summary(db_path=temp_db)
    assert summary["totalReceipts"] == 3
    assert summary["todayExpenses"] == 465.00
    assert summary["approvalRate"] == "66.7%"
    assert summary["anomalyRate"] == "33.3%"

    trends = get_analytics_trends(db_path=temp_db)
    # Categories: Travel ($285.00, 2), Meals ($180.00, 1)
    categories = {c["category"]: c for c in trends["byCategory"]}
    assert "Travel" in categories
    assert categories["Travel"]["count"] == 2
    assert abs(categories["Travel"]["total"] - 285.00) < 0.01

    # Departments: dept_sales ($215.00, 2), dept_eng ($250.00, 1)
    depts = {d["department"]: d for d in trends["byDepartment"]}
    assert "dept_sales" in depts
    assert depts["dept_sales"]["count"] == 2

    # Flagged receipts
    flagged = get_flagged_receipts(db_path=temp_db)
    assert len(flagged) == 1
    assert flagged[0]["receiptId"] == "rcpt_an_3"
    assert flagged[0]["vendor"] == "Luxury Lounge"


def test_bulk_upload_endpoint(temp_db):
    client = TestClient(app)

    files = [
        ('receipts', ('receipt1.jpg', b'fake-image-1', 'image/jpeg')),
        ('receipts', ('receipt2.jpg', b'fake-image-2', 'image/jpeg')),
        ('receipts', ('receipt3.jpg', b'fake-image-3', 'image/jpeg'))
    ]
    data = {'employeeId': 'emp_bulk_user', 'departmentId': 'dept_marketing'}

    response = client.post('/api/receipts/bulk', data=data, files=files)
    assert response.status_code == 200
    resp_json = response.json()

    assert resp_json['batchId'].startswith('batch_')
    assert resp_json['processed'] == 3
    assert len(resp_json['results']) == 3
    # First one was auto-approved, subsequent identical receipts in batch flagged as duplicates
    assert resp_json['approved'] >= 1
    assert resp_json['totalAmount'] > 0
    assert 'seconds' in resp_json['processingTime']


def test_analytics_dashboard_endpoint(temp_db):
    client = TestClient(app)

    # Initially empty
    res_empty = client.get('/api/analytics/dashboard')
    assert res_empty.status_code == 200
    assert res_empty.json()['summary']['totalReceipts'] == 0

    # Submit a receipt
    files = {'image': ('test.jpg', b'receipt-bytes', 'image/jpeg')}
    client.post('/api/parse-receipt', data={'employeeId': 'emp_analyst', 'departmentId': 'dept_finance'}, files=files)

    res_populated = client.get('/api/analytics/dashboard')
    assert res_populated.status_code == 200
    dashboard = res_populated.json()
    assert dashboard['summary']['totalReceipts'] == 1
    assert len(dashboard['trends']['byCategory']) >= 1
    assert len(dashboard['trends']['byDepartment']) >= 1
