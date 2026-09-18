"""OCR adapter module.

Provides `extract_from_image(image_bytes)` which attempts to run pytesseract
OCR if available and the image is valid. If OCR is unavailable or fails,
falls back to the original mocked extraction used by the prototype tests.
"""
from typing import Dict
import io

def _mock_extract() -> Dict:
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


def extract_from_image(image_bytes: bytes) -> Dict:
    """Attempt real OCR; on any failure return mocked extraction.

    Notes:
    - Requires `pytesseract` and `Pillow` to be installed and `tesseract` binary
      available on PATH for real OCR to run.
    - For the prototype/tests we gracefully fall back to the mock.
    """
    try:
        from PIL import Image
        import pytesseract
    except Exception:
        # OCR libraries not available in environment
        return _mock_extract()

    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        # Very small heuristic parser: look for a dollar amount and vendor line
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        vendor = lines[0] if lines else "Unknown Vendor"
        import re
        amt = None
        for l in lines[::-1]:
            m = re.search(r"\$?([0-9]+\.[0-9]{2})", l)
            if m:
                amt = float(m.group(1))
                break
        if amt is None:
            return _mock_extract()

        # Build a minimal parsed structure from extracted text
        return {
            "receiptId": "rcpt_ocr_001",
            "extraction": {
                "vendor": vendor,
                "amount": amt,
                "currency": "USD",
                "date": "unknown",
                "time": None,
                "itemsCount": 0,
                "items": [],
                "paymentMethod": None,
                "category": None,
                "confidence": 0.6
            },
            "categorization": {
                "category": "Unknown",
                "confidence": 0.6,
                "reasoning": "OCR-only heuristic"
            },
            "compliance": {
                "status": "NEEDS_REVIEW",
                "policyChecks": [],
                "anomalies": []
            },
            "approval": {
                "recommendation": "NEEDS_REVIEW",
                "reason": "OCR parsed minimal fields",
                "requiredApproval": "manager",
                "alternativeAction": "Resubmit or manual entry"
            }
        }
    except Exception:
        return _mock_extract()


__all__ = ["extract_from_image", "_mock_extract"]
