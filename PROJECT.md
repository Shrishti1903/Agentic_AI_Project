# Smart Expense Receipt Parser Agent

Goal: An AI-powered agentic system that automatically extracts, validates, categorizes, and audits expense receipts against enterprise policies in real-time, targeting >95% accuracy and <2s processing latency.
Tech stack: Python 3.11, FastAPI, Pydantic v2, Pytest, Pillow + Pytesseract (OCR adapter), SQLite.

## Status
Current step: Step 5 — Bulk Upload & Analytics Dashboard API Endpoints Completed | Last updated: 2026-09-19

## Roadmap
- [x] **Step 1**: Establish Living Project Document (`PROJECT.md`) as single source of truth.
- [x] **Step 2**: Build Validation & Categorization Engine (`app/validator.py`, `app/categorizer.py`) with unit tests.
- [x] **Step 3**: Build Policy & Anomaly Audit Engine (`app/audit_engine.py`) for limit checks, prohibited items, and approval routing.
- [x] **Step 4**: Implement SQLite Storage Layer (`app/db.py`) for receipt persistence, 24-hour duplicate detection, and history tracking.
- [x] **Step 5**: Implement Bulk Upload & Analytics Dashboard API Endpoints (`POST /api/receipts/bulk`, `GET /api/analytics/dashboard`).
- [ ] **Step 6**: Add CI/CD Workflow (`.github/workflows/ci.yml`) and Performance/Accuracy Benchmark script.
- [ ] **Step 7**: Build Interactive Web UI for receipt upload, review, and analytics.

## Step Log
- **Step 0 (Initial Scaffolding & Setup)** — 2026-09-19
  - Extracted rules from `AI_Agent_Project_Rules.pdf` into `rules_text.txt`.
  - Mapped core constraints into `CONSTRAINTS.md` from `PRD_Receipt_Parser.md`.
  - Scaffolding of FastAPI prototype in `app/main.py` with `app/schemas.py`.
  - Added OCR adapter with pytesseract and fallback mock in `app/ocr_adapter.py`.
  - Added initial tests in `tests/test_parse.py` (all passing).
- **Step 1 (Living Project Document)** — 2026-09-19
  - Created `PROJECT.md` conforming to project rules template as the single source of truth.
  - Aligned team roadmap, step log, file map, open issues, and execution instructions.
- **Step 2 (Validation & Categorization Engine)** — 2026-09-19
  - Created `app/validator.py` for completeness check, math verification (`sum(items) == total`), and low confidence (<80%) threshold detection.
  - Created `app/categorizer.py` implementing heuristic categorization across the 7 PRD categories with confidence scores and reasoning.
  - Integrated `validator` and `categorizer` into `app/ocr_adapter.py`.
  - Added default `= None` to optional Pydantic fields in `app/schemas.py`.
  - Created test suite `tests/test_validation_categorization.py` (all 8 tests passing).
- **Step 3 (Policy & Anomaly Audit Engine)** — 2026-09-19
  - Created `app/audit_engine.py` evaluating expense limits ($50 meal / $150 general), prohibited items (alcohol, luxury), and risk scoring.
  - Implemented role-based approval logic (`AUTO_APPROVE`, `NEEDS_REVIEW`, `REJECT`) with escalation routing (`manager` vs `cfo` for >$1,000).
  - Wired `audit_expense` into `app/ocr_adapter.py`.
  - Created test suite `tests/test_audit_engine.py` covering policy rules and edge cases (all 13 tests passing).
- **Step 4 (SQLite Storage & Duplicate Detection)** — 2026-09-19
  - Created `app/db.py` managing SQLite schema (`receipts`, `receipt_items` tables and indices).
  - Implemented receipt persistence with full structured JSON payload and item reconciliation.
  - Implemented 24-hour duplicate transaction detection engine (matching employee, vendor, amount).
  - Wired duplicate detection into `app/audit_engine.py` (anomalies flag & policy check) and `app/main.py`.
  - Added REST endpoints: `GET /api/receipts/{receipt_id}`, `GET /api/receipts/employee/{employee_id}`, and `GET /api/receipts`.
  - Created comprehensive test suite `tests/test_db.py` (all 17 test cases across project passing).
- **Step 5 (Bulk Upload & Analytics Dashboard API)** — 2026-09-19
  - Added Pydantic schema models for `BulkUploadResponse`, `AnalyticsSummary`, `AnalyticsTrends`, `FlaggedReceiptItem`, and `AnalyticsDashboardResponse`.
  - Added SQL query aggregation helpers `get_analytics_summary`, `get_analytics_trends`, and `get_flagged_receipts` in `app/db.py`.
  - Implemented `POST /api/receipts/bulk` supporting multipart batch receipt image processing, duplicate checks, timing calculation, and aggregate status.
  - Implemented `GET /api/analytics/dashboard` delivering finance team visibility (total spend, approval rates, category/department breakdowns, and pending review queue).
  - Created test suite `tests/test_bulk_and_analytics.py` (all 21 tests across project passing).

## File Map
- `AI_Agent_Project_Rules.pdf` — Primary project rules and working agreement.
- `rules_text.txt` — Plain text extraction of project rules.
- `PRD_Receipt_Parser.md` — Complete Product Requirements Document.
- `CONSTRAINTS.md` — Distilled hard constraints, metrics, and data structures.
- `PROJECT_PLAN.md` — Initial high-level plan.
- `PROJECT.md` — Living project tracking document (single source of truth).
- `requirements.txt` — Python dependencies.
- `app/`
  - `main.py` — FastAPI application entry point, lifecycle management, and HTTP route handlers.
  - `db.py` — SQLite database persistence layer, 24h duplicate detection, analytics aggregations, and history tracking.
  - `schemas.py` — Pydantic models for extraction, categorization, compliance, approval, bulk upload, and analytics dashboard.
  - `validator.py` — Integrity, quality, and item sum math reconciliation validator.
  - `categorizer.py` — Intelligent rule-based categorization engine for the 7 PRD categories.
  - `audit_engine.py` — Policy compliance, prohibited item detection, anomaly scoring, and approval recommendation.
  - `ocr_adapter.py` — OCR extraction module with Pillow/pytesseract and mock fallback.
- `tests/`
  - `test_parse.py` — Pytest suite covering root and receipt parsing endpoints.
  - `test_validation_categorization.py` — Pytest suite covering validation rules, math reconciliation, and categorization heuristics.
  - `test_audit_engine.py` — Pytest suite covering policy limits, alcohol/luxury rejection, and approval escalation.
  - `test_db.py` — Pytest suite covering SQLite storage, 24h duplicate detection, employee history, and API persistence flow.
  - `test_bulk_and_analytics.py` — Pytest suite covering batch upload processing and analytics dashboard metrics.

## Open Issues
- Virtual environment `.venv` needs packages installed if isolated from system Python.

## Backlog / Future Ideas
- Integration with Claude Vision API adapter for advanced multimodal OCR.
- Mobile camera receipt capture support.
- Multi-currency conversion service.
- Corporate ERP / accounting software export (Quickbooks, SAP).

## How to Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the development server:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```
3. Run test suite:
   ```bash
   python -m pytest -v
   ```
