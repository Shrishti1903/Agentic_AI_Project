import pytest
from app.audit_engine import audit_expense
from app.categorizer import categorize_expense
from app.validator import validate_extraction
from app.schemas import Extraction, Item, Categorization


def test_audit_auto_approve():
    extraction = {
        "vendor": "Panera Bread",
        "amount": 28.50,
        "currency": "USD",
        "date": "2026-09-18",
        "confidence": 0.95,
        "items": [
            {"name": "Sandwich Combo", "quantity": 1, "price": 18.50},
            {"name": "Soup", "quantity": 1, "price": 10.00}
        ]
    }
    cat = Categorization(category="Meals & Entertainment", confidence=0.95)
    val = validate_extraction(extraction)
    compliance, approval = audit_expense(extraction, cat, val)

    assert compliance.status == "APPROVED"
    assert approval.recommendation == "AUTO_APPROVE"
    assert approval.requiredApproval is None
    assert len(compliance.anomalies) == 0


def test_audit_meal_limit_exceeded():
    extraction = {
        "vendor": "Steakhouse Prime",
        "amount": 85.00,  # Exceeds $50 daily meal limit
        "currency": "USD",
        "date": "2026-09-18",
        "confidence": 0.92,
        "items": [
            {"name": "Filet Mignon", "quantity": 1, "price": 85.00}
        ]
    }
    cat = Categorization(category="Meals & Entertainment", confidence=0.95)
    val = validate_extraction(extraction)
    compliance, approval = audit_expense(extraction, cat, val)

    assert compliance.status == "NEEDS_REVIEW"
    assert approval.recommendation == "NEEDS_REVIEW"
    assert approval.requiredApproval == "manager"
    assert any(a.type == "budget_exceed" for a in compliance.anomalies)


def test_audit_prohibited_alcohol_rejection():
    extraction = {
        "vendor": "Downtown Bistro",
        "amount": 42.00,
        "currency": "USD",
        "date": "2026-09-18",
        "confidence": 0.94,
        "items": [
            {"name": "Burger", "quantity": 1, "price": 18.00},
            {"name": "Cabernet Red Wine", "quantity": 2, "price": 12.00}
        ]
    }
    cat = Categorization(category="Meals & Entertainment", confidence=0.95)
    val = validate_extraction(extraction)
    compliance, approval = audit_expense(extraction, cat, val)

    assert compliance.status == "REJECTED"
    assert approval.recommendation == "REJECT"
    assert approval.requiredApproval == "manager"
    assert any(a.type == "policy_violation" for a in compliance.anomalies)
    assert "alcohol" in approval.alternativeAction.lower() or "prohibited" in approval.reason.lower()


def test_audit_high_value_cfo_escalation():
    extraction = {
        "vendor": "Apple Store",
        "amount": 1850.00,  # > $1,000 threshold
        "currency": "USD",
        "date": "2026-09-18",
        "confidence": 0.98,
        "items": [
            {"name": "MacBook Pro", "quantity": 1, "price": 1850.00}
        ]
    }
    cat = Categorization(category="Equipment", confidence=0.95)
    val = validate_extraction(extraction)
    compliance, approval = audit_expense(extraction, cat, val)

    assert compliance.status == "NEEDS_REVIEW"
    assert approval.recommendation == "NEEDS_REVIEW"
    assert approval.requiredApproval == "cfo"
    assert "CFO" in approval.alternativeAction or "cfo" in approval.requiredApproval


def test_audit_math_discrepancy_flag():
    extraction = {
        "vendor": "Office Depot",
        "amount": 100.00,
        "currency": "USD",
        "date": "2026-09-18",
        "confidence": 0.90,
        "items": [
            {"name": "Notebooks", "quantity": 1, "price": 20.00}  # Discrepancy $80
        ]
    }
    cat = Categorization(category="Office Supplies", confidence=0.90)
    val = validate_extraction(extraction)
    compliance, approval = audit_expense(extraction, cat, val)

    assert compliance.status == "NEEDS_REVIEW"
    assert approval.recommendation == "NEEDS_REVIEW"
    assert any(a.type == "math_discrepancy" for a in compliance.anomalies)
