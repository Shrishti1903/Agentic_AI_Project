"""Receipt Validation Module.

Performs completeness checks, math verification (sum of item prices vs total amount),
and image confidence quality thresholding (<0.80 indicates low confidence per PRD).
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.schemas import Extraction, Item


class ValidationResult(BaseModel):
    is_valid: bool
    issues: List[str]
    math_matches: bool
    discrepancy: float
    is_low_confidence: bool
    confidence: float


def validate_extraction(data: Extraction | Dict[str, Any]) -> ValidationResult:
    """Validate extracted receipt data against quality and integrity rules."""
    if isinstance(data, dict):
        vendor = data.get("vendor", "")
        amount = float(data.get("amount", 0.0) or 0.0)
        currency = data.get("currency", "")
        date = data.get("date", "")
        confidence = float(data.get("confidence", 1.0) or 1.0)
        items_raw = data.get("items", [])
    else:
        vendor = data.vendor
        amount = data.amount
        currency = data.currency
        date = data.date
        confidence = data.confidence
        items_raw = data.items

    issues: List[str] = []

    # Completeness checks
    if not vendor or vendor.strip().lower() in ["", "unknown", "unknown vendor"]:
        issues.append("Missing or unrecognized vendor name.")
    if amount <= 0:
        issues.append("Total amount must be greater than zero.")
    if not currency:
        issues.append("Missing currency specification.")
    if not date or date.strip().lower() in ["", "unknown"]:
        issues.append("Missing or invalid receipt date.")

    # Image confidence threshold (PRD Section 3.1 & Story 3: <80% requires review/resubmission)
    is_low_confidence = confidence < 0.80
    if is_low_confidence:
        issues.append(f"Low extraction confidence ({confidence * 100:.1f}% < 80%). Manual review recommended.")

    # Item math reconciliation
    items_total = 0.0
    for itm in items_raw:
        if isinstance(itm, dict):
            price = float(itm.get("price", 0.0) or 0.0)
            qty = int(itm.get("quantity", 1) or 1)
        else:
            price = float(itm.price)
            qty = int(itm.quantity or 1)
        items_total += price * qty

    discrepancy = 0.0
    math_matches = True
    if items_raw:
        discrepancy = round(abs(items_total - amount), 2)
        # Allow 0.05 tolerance for rounding/tax discrepancies
        if discrepancy > 0.05:
            math_matches = False
            issues.append(f"Itemization discrepancy: sum of items (${items_total:.2f}) does not match total amount (${amount:.2f}).")

    is_valid = len(issues) == 0

    return ValidationResult(
        is_valid=is_valid,
        issues=issues,
        math_matches=math_matches,
        discrepancy=discrepancy,
        is_low_confidence=is_low_confidence,
        confidence=confidence
    )
