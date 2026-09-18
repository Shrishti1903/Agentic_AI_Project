def mock_extract():
    return {
        "receiptId": "rcpt_demo_001",
        "extraction": {
            "vendor": "Chipotle",
            "amount": 12.99,
            "currency": "USD",
            "date": "2026-09-15",
            "time": "12:30 PM",
            "itemsCount": 3,
            "items": [
                {"name": "Burrito Bowl", "quantity": 1, "price": 8.99},
                {"name": "Drink", "quantity": 1, "price": 2.99},
                {"name": "Tax", "quantity": 1, "price": 0.99}
            ],
            "paymentMethod": "Credit Card",
            "category": "Meals & Entertainment",
            "confidence": 0.97
        },
        "categorization": {
            "category": "Meals & Entertainment",
            "confidence": 0.95,
            "reasoning": "Vendor is food, business meal pattern"
        },
        "compliance": {
            "status": "APPROVED",
            "policyChecks": [
                {"rule": "daily_limit", "status": "pass", "message": "12.99 < 150"}
            ],
            "anomalies": []
        },
        "approval": {
            "recommendation": "AUTO_APPROVE",
            "reason": "Within policy",
            "requiredApproval": None,
            "alternativeAction": None
        }
    }
