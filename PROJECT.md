# Smart Expense Receipt Parser Agent

Goal: An AI-powered agentic system that automatically extracts, validates, categorizes, and audits expense receipts against enterprise policies in real-time, targeting >95% accuracy and <2s processing latency.
Tech stack: Python 3.11, FastAPI, Pydantic v2, Pytest, Pillow + Pytesseract (OCR adapter), SQLite (planned).

## Status
Current step: Step 1 — Establish Living Project Document (`PROJECT.md`) | Last updated: 2026-09-19

## Roadmap
- [x] **Step 1**: Establish Living Project Document (`PROJECT.md`) as single source of truth.
- [ ] **Step 2**: Build Validation & Categorization Engine (`app/validator.py`, `app/categorizer.py`) with unit tests.
- [ ] **Step 3**: Build Policy & Anomaly Audit Engine (`app/audit_engine.py`) for limit checks, prohibited items, and approval routing.
- [ ] **Step 4**: Implement SQLite Storage Layer (`app/db.py`) for receipt persistence, 24-hour duplicate detection, and history tracking.
- [ ] **Step 5**: Implement Bulk Upload & Analytics Dashboard API Endpoints (`POST /api/receipts/bulk`, `GET /api/analytics/dashboard`).
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

## File Map
- `AI_Agent_Project_Rules.pdf` — Primary project rules and working agreement.
- `rules_text.txt` — Plain text extraction of project rules.
- `PRD_Receipt_Parser.md` — Complete Product Requirements Document.
- `CONSTRAINTS.md` — Distilled hard constraints, metrics, and data structures.
- `PROJECT_PLAN.md` — Initial high-level plan.
- `PROJECT.md` — Living project tracking document (single source of truth).
- `requirements.txt` — Python dependencies.
- `app/`
  - `main.py` — FastAPI application entry point and HTTP route handlers.
  - `schemas.py` — Pydantic models for extraction, categorization, compliance, and approval.
  - `ocr_adapter.py` — OCR extraction module with Pillow/pytesseract and mock fallback.
- `tests/`
  - `test_parse.py` — Pytest suite covering root and receipt parsing endpoints.

## Open Issues
- `app/ocr_adapter.py` currently returns hardcoded/mocked categorization and approval data instead of running dedicated multi-agent rule engines.
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
