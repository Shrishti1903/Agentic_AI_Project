# Constraints and Requirements Mapping

Source: `PRD_Receipt_Parser.md` and `AI_Agent_Project_Rules.pdf` (PDF parsed by content inspection where possible).

> Note: I attempted to read the PDF programmatically but the file is binary; constraints below are mapped from the PRD and the PDF where text was discoverable. If you want a verbatim PDF-to-text extraction I can run a local extractor next.

## Hard Constraints (must-follow)
- Extraction accuracy target: >95% (measured via manual audit of 100 receipts).
- Processing latency target: <2 seconds per receipt (API latency tracking).
- False positive rate for anomalies: <5%.
- Policy compliance: 100% automated rule checking.
- Supported input formats: JPG, PNG, PDF.
- Acceptance of low-quality images: agent must detect low confidence (<80%) and request resubmission or allow manual override.

## Data Fields to Extract
- `amount`, `currency`, `vendor`, `date`, `time` (if present), `itemsCount`, `items[]` (name, quantity, price), `paymentMethod`, `category`, `confidence`.
- Structured output JSON must include `extraction`, `categorization`, `compliance`, and `approval` sections per PRD API spec.

## Categorization Rules
- Categories: Travel, Meals & Entertainment, Office Supplies, Professional Development, Client Expenses, Equipment, Other.
- Logic sources: vendor name matching, item description analysis, historical patterns, and policy-based rules.

## Anomaly & Audit Rules
- Flag when:
  - Amount > daily limit ($150)
  - Amount > weekly limit ($500)
  - Duplicate transaction within 24 hours
  - Unusual vendor for employee (deviation from historical vendor list)
  - Missing itemization (sum of items != receipt total)
  - Personal items mixed with business items
  - Policy violations (e.g., alcohol, luxury purchases)
- Output for flagged receipts includes `isAnomalous`, `riskLevel`, and `flags[]` with `type`, `message`, and `severity`.

## Compliance & Approval
- Automated checks required: policy rules, documentation completeness, business purpose (where required), and budget availability by department.
- Approval recommendation must include `recommendation` (APPROVE/REJECT/NEEDS_REVIEW), `reason`, `requiredApproval` role, and `alternativeAction` where applicable.

## Security & Privacy (inferred / recommended)
- Store receipts in S3-like storage with restricted access.
- PII (employee identifiers, payment methods) must be handled per company policy — redact where necessary.

## Technical Constraints / Integration
- OCR/Vision adapter: Claude Vision API is preferred but the implementation must be pluggable/mocked for prototype.
- Prototype DB: SQLite acceptable; production: PostgreSQL.
- Storage: local filesystem for prototype; S3-compatible for production.
- APIs as defined in PRD: `/api/parse-receipt`, `/api/receipts/bulk`, `/api/analytics/dashboard`.

## Test & Acceptance
- Provide a reproducible audit script to measure extraction accuracy on a sample set of 100 receipts.
- Performance tests to verify average latency <2s per receipt on representative hardware or mocked vision calls.

## Open Questions / Items Requiring Confirmation
- Confirm exact daily/weekly limit values if they differ per department or role (PRD uses $150/$500 as examples).
- Confirm required retention period and encryption standards for stored receipts.
- Confirm whether Claude Vision API keys or alternative OCR services are available for development.

---

Next step: I will scaffold the repository structure and add a minimal FastAPI prototype (or Node.js if you prefer). Tell me if you prefer Python/FastAPI or Node/Express; otherwise I'll proceed with Python/FastAPI.
