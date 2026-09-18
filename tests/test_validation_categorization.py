import pytest
from app.categorizer import categorize_expense
from app.validator import validate_extraction
from app.schemas import Extraction, Item


def test_categorize_vendor_matching():
    # Travel
    res_travel = categorize_expense(vendor="Delta Airlines")
    assert res_travel.category == "Travel"
    assert res_travel.confidence >= 0.90

    # Meals & Entertainment
    res_meals = categorize_expense(vendor="Starbucks Coffee")
    assert res_meals.category == "Meals & Entertainment"
    assert res_meals.confidence >= 0.90

    # Office Supplies
    res_supplies = categorize_expense(vendor="Staples Store #102")
    assert res_supplies.category == "Office Supplies"
    assert res_supplies.confidence >= 0.90

    # Professional Development
    res_edu = categorize_expense(vendor="Coursera Inc")
    assert res_edu.category == "Professional Development"
    assert res_edu.confidence >= 0.90

    # Equipment
    res_eq = categorize_expense(vendor="Apple Store")
    assert res_eq.category == "Equipment"
    assert res_eq.confidence >= 0.90

    # Other (unrecognized)
    res_other = categorize_expense(vendor="Mysterious Unknown Merchant XYZ")
    assert res_other.category == "Other"
    assert res_other.confidence == 0.50


def test_categorize_item_heuristics():
    # Vendor Amazon with equipment items
    res_eq = categorize_expense(
        vendor="Amazon.com",
        items=[{"name": "Dell 27-inch 4K Monitor", "quantity": 1, "price": 320.00}]
    )
    assert res_eq.category == "Equipment"

    # Vendor Amazon with office supplies items
    res_off = categorize_expense(
        vendor="Amazon.com",
        items=[{"name": "Printer Paper 500 sheets", "quantity": 2, "price": 15.00}]
    )
    assert res_off.category == "Office Supplies"

    # Client Expense keyword
    res_client = categorize_expense(
        vendor="Bistro 55",
        items=[{"name": "Client dinner tasting menu", "quantity": 2, "price": 120.00}]
    )
    assert res_client.category == "Client Expenses"


def test_validation_valid_receipt():
    data = Extraction(
        vendor="Chipotle Mexican Grill",
        amount=15.50,
        currency="USD",
        date="2026-09-18",
        time="1:15 PM",
        itemsCount=2,
        items=[
            Item(name="Chicken Bowl", quantity=1, price=11.50),
            Item(name="Fountain Drink", quantity=1, price=4.00)
        ],
        confidence=0.96
    )
    res = validate_extraction(data)
    assert res.is_valid is True
    assert res.math_matches is True
    assert res.discrepancy == 0.0
    assert res.is_low_confidence is False
    assert len(res.issues) == 0


def test_validation_math_discrepancy():
    data = {
        "vendor": "Uber Eats",
        "amount": 50.00,
        "currency": "USD",
        "date": "2026-09-18",
        "confidence": 0.95,
        "items": [
            {"name": "Burger", "quantity": 1, "price": 15.00},
            {"name": "Fries", "quantity": 1, "price": 5.00}
            # Items sum to $20.00, but amount is $50.00 -> discrepancy
        ]
    }
    res = validate_extraction(data)
    assert res.is_valid is False
    assert res.math_matches is False
    assert res.discrepancy == 30.00
    assert any("Itemization discrepancy" in iss for iss in res.issues)


def test_validation_low_confidence():
    data = {
        "vendor": "Corner Deli",
        "amount": 10.00,
        "currency": "USD",
        "date": "2026-09-18",
        "confidence": 0.65,  # < 0.80 triggers low confidence
        "items": []
    }
    res = validate_extraction(data)
    assert res.is_valid is False
    assert res.is_low_confidence is True
    assert any("Low extraction confidence" in iss for iss in res.issues)


def test_validation_missing_fields():
    data = {
        "vendor": "",
        "amount": 0.0,
        "currency": "",
        "date": "",
        "confidence": 0.90,
        "items": []
    }
    res = validate_extraction(data)
    assert res.is_valid is False
    assert len(res.issues) >= 3
