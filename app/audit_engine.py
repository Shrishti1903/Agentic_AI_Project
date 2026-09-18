"""Policy & Anomaly Audit Engine.

Evaluates receipt extraction and categorization against enterprise expense policies:
- Daily Meal Limit ($50.00) and General Daily Limit ($150.00)
- Prohibited items detection (alcohol, luxury, personal items)
- Itemization completeness and math discrepancy checks
- Role-based approval escalation:
    - Auto-approve if clean and within limits
    - Manager review for limit overages or minor policy flags
    - CFO escalation for expenses exceeding $1,000.00
    - Rejection for prohibited items
"""
from typing import List, Dict, Any, Optional, Tuple
from app.schemas import Compliance, PolicyCheck, Flag, Approval, Extraction, Categorization
from app.validator import ValidationResult

# Prohibited purchase keywords
PROHIBITED_ITEMS = {
    "alcohol": [
        "beer", "wine", "cocktail", "liquor", "whiskey", "vodka", "tequila",
        "rum", "margarita", "champagne", "ipa", "cider", "bourbon", "alcohol",
        "gin", "sake"
    ],
    "luxury": [
        "jewelry", "spa", "massage", "casino", "rolex", "luxury", "resort fee"
    ]
}

DAILY_MEAL_LIMIT = 50.00
DAILY_GENERAL_LIMIT = 150.00
CFO_APPROVAL_THRESHOLD = 1000.00


def audit_expense(
    extraction: Extraction | Dict[str, Any],
    categorization: Categorization | Dict[str, Any],
    validation: Optional[ValidationResult] = None
) -> Tuple[Compliance, Approval]:
    """Run full policy, compliance, and anomaly checks on extracted receipt."""
    if isinstance(extraction, dict):
        amount = float(extraction.get("amount", 0.0) or 0.0)
        items_raw = extraction.get("items", [])
    else:
        amount = extraction.amount
        items_raw = extraction.items

    if isinstance(categorization, dict):
        category = categorization.get("category", "Other")
    else:
        category = categorization.category

    policy_checks: List[PolicyCheck] = []
    anomalies: List[Flag] = []
    prohibited_detected: List[str] = []

    # 1. Prohibited Items Check
    for itm in items_raw:
        name = itm.get("name", "") if isinstance(itm, dict) else itm.name
        name_lower = name.lower()
        for p_type, keywords in PROHIBITED_ITEMS.items():
            for kw in keywords:
                if kw in name_lower:
                    prohibited_detected.append(f"{kw.title()} ('{name}')")

    if prohibited_detected:
        policy_checks.append(PolicyCheck(
            rule="prohibited_items",
            status="fail",
            message=f"Prohibited items detected: {', '.join(prohibited_detected)}"
        ))
        anomalies.append(Flag(
            type="policy_violation",
            message=f"Prohibited purchase detected: {', '.join(prohibited_detected)}",
            severity="high"
        ))
    else:
        policy_checks.append(PolicyCheck(
            rule="prohibited_items",
            status="pass",
            message="No prohibited items (alcohol/luxury) detected"
        ))

    # 2. Daily Limit Checks
    if category == "Meals & Entertainment":
        if amount > DAILY_MEAL_LIMIT:
            policy_checks.append(PolicyCheck(
                rule="daily_meal_limit",
                status="fail",
                message=f"Amount ${amount:.2f} exceeds daily meal limit of ${DAILY_MEAL_LIMIT:.2f}"
            ))
            anomalies.append(Flag(
                type="budget_exceed",
                message=f"Meal expense (${amount:.2f}) exceeds daily policy limit of ${DAILY_MEAL_LIMIT:.2f}",
                severity="high" if amount > (DAILY_MEAL_LIMIT * 2) else "medium"
            ))
        else:
            policy_checks.append(PolicyCheck(
                rule="daily_meal_limit",
                status="pass",
                message=f"Meal amount ${amount:.2f} is within ${DAILY_MEAL_LIMIT:.2f} limit"
            ))
    else:
        if amount > DAILY_GENERAL_LIMIT:
            policy_checks.append(PolicyCheck(
                rule="daily_general_limit",
                status="fail",
                message=f"Amount ${amount:.2f} exceeds general limit of ${DAILY_GENERAL_LIMIT:.2f}"
            ))
            anomalies.append(Flag(
                type="budget_exceed",
                message=f"Expense (${amount:.2f}) exceeds standard single-day limit of ${DAILY_GENERAL_LIMIT:.2f}",
                severity="medium"
            ))
        else:
            policy_checks.append(PolicyCheck(
                rule="daily_general_limit",
                status="pass",
                message=f"Amount ${amount:.2f} is within ${DAILY_GENERAL_LIMIT:.2f} limit"
            ))

    # 3. Validation & Quality Checks
    if validation:
        if validation.is_low_confidence:
            policy_checks.append(PolicyCheck(
                rule="image_quality",
                status="fail",
                message=f"Extraction confidence ({validation.confidence * 100:.1f}%) is below 80% threshold"
            ))
            anomalies.append(Flag(
                type="low_confidence",
                message="Receipt image confidence is below 80% threshold. Requires manual verification.",
                severity="medium"
            ))
        else:
            policy_checks.append(PolicyCheck(
                rule="image_quality",
                status="pass",
                message=f"Extraction confidence ({validation.confidence * 100:.1f}%) satisfies quality threshold"
            ))

        if not validation.math_matches:
            policy_checks.append(PolicyCheck(
                rule="itemization_integrity",
                status="fail",
                message=f"Item sum does not match receipt total (discrepancy: ${validation.discrepancy:.2f})"
            ))
            anomalies.append(Flag(
                type="math_discrepancy",
                message=f"Itemization mismatch: discrepancy of ${validation.discrepancy:.2f} between items and total.",
                severity="medium"
            ))
        elif validation.issues and not validation.is_low_confidence:
            for issue in validation.issues:
                policy_checks.append(PolicyCheck(
                    rule="field_completeness",
                    status="fail",
                    message=issue
                ))
                anomalies.append(Flag(
                    type="incomplete_data",
                    message=issue,
                    severity="high"
                ))

    # 4. Determine Approval Recommendation and Required Approval Role
    if prohibited_detected:
        recommendation = "REJECT"
        status = "REJECTED"
        required_approval = "manager"
        reason = f"Prohibited item policy violation: {', '.join(prohibited_detected)}"
        alternative_action = "Resubmit receipt without prohibited items or provide documented executive exception"
    elif anomalies:
        recommendation = "NEEDS_REVIEW"
        status = "NEEDS_REVIEW"
        required_approval = "cfo" if amount > CFO_APPROVAL_THRESHOLD else "manager"
        reason = "; ".join([f.message for f in anomalies])
        alternative_action = "Submit for manual supervisor review and justification"
    else:
        # Check if amount requires CFO escalation even if otherwise clean
        if amount > CFO_APPROVAL_THRESHOLD:
            recommendation = "NEEDS_REVIEW"
            status = "NEEDS_REVIEW"
            required_approval = "cfo"
            reason = f"Clean expense exceeds high-value threshold (${CFO_APPROVAL_THRESHOLD:.2f})"
            alternative_action = "Route to CFO for high-value authorization"
        else:
            recommendation = "AUTO_APPROVE"
            status = "APPROVED"
            required_approval = None
            reason = "Within policy limits and passed all automated checks"
            alternative_action = None

    compliance = Compliance(
        status=status,
        policyChecks=policy_checks,
        anomalies=anomalies
    )

    approval = Approval(
        recommendation=recommendation,
        reason=reason,
        requiredApproval=required_approval,
        alternativeAction=alternative_action
    )

    return compliance, approval
