import os
import time
import uuid
from typing import Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.schemas import (
    ParseResponse,
    BulkUploadResponse,
    AnalyticsDashboardResponse,
    AnalyticsSummary,
    AnalyticsTrends,
    FlaggedReceiptItem
)
from app.ocr_adapter import extract_from_image
from app.validator import validate_extraction
from app.audit_engine import audit_expense
from app.db import (
    init_db,
    save_receipt,
    get_receipt,
    check_duplicate_receipt,
    get_employee_history,
    get_all_receipts,
    get_analytics_summary,
    get_analytics_trends,
    get_flagged_receipts
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


# Locate the static/ directory relative to this file's parent
_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


app = FastAPI(title="Receipt Parser Agent", lifespan=lifespan)

# Mount the static directory so /static/styles.css and /static/app.js are served
if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def ui_root():
    """Serve the interactive Web UI."""
    index_path = os.path.join(_STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"status": "ok", "service": "receipt-parser"}

def process_single_receipt(
    image_bytes: bytes,
    employee_id: str,
    department_id: str,
    receipt_id_override: Optional[str] = None
) -> ParseResponse:
    """Extract, validate, categorize, audit against policies, and persist a single receipt."""
    data = extract_from_image(image_bytes)
    if receipt_id_override:
        data["receiptId"] = receipt_id_override

    vendor = data["extraction"].get("vendor", "")
    amount = float(data["extraction"].get("amount", 0.0) or 0.0)
    receipt_date = data["extraction"].get("date")

    # Check for 24-hour duplicate transaction
    duplicate = check_duplicate_receipt(
        employee_id=employee_id,
        vendor=vendor,
        amount=amount,
        receipt_date=receipt_date
    )

    if duplicate:
        dup_info = f"Matches prior submission {duplicate['receipt_id']} (${duplicate['amount']:.2f}) on {duplicate['date']}"
        val = validate_extraction(data["extraction"])
        compliance, approval = audit_expense(
            extraction=data["extraction"],
            categorization=data["categorization"],
            validation=val,
            is_duplicate=True,
            duplicate_info=dup_info
        )
        data["compliance"] = compliance.model_dump()
        data["approval"] = approval.model_dump()

    resp = ParseResponse(**data)
    save_receipt(resp.model_dump(), employee_id, department_id)
    return resp


@app.get("/")
async def root():
    return {"status": "ok", "service": "receipt-parser"}


@app.post("/api/parse-receipt", response_model=ParseResponse)
async def parse_receipt(
    employeeId: str = Form(...),
    departmentId: str = Form(...),
    image: UploadFile = File(...)
):
    """Upload a single receipt image to extract, audit, and persist."""
    image_bytes = await image.read()
    return process_single_receipt(image_bytes, employeeId, departmentId)


@app.post("/api/receipts/bulk", response_model=BulkUploadResponse)
async def bulk_parse_receipts(
    employeeId: str = Form(...),
    departmentId: str = Form("dept_general"),
    receipts: List[UploadFile] = File(...)
):
    """Batch process multiple receipt uploads."""
    start_time = time.time()
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"

    results: List[ParseResponse] = []
    approved_count = 0
    flagged_count = 0
    total_amount = 0.0

    for idx, receipt_file in enumerate(receipts):
        file_bytes = await receipt_file.read()
        receipt_id = f"{batch_id}_{idx+1:03d}"
        parse_resp = process_single_receipt(
            image_bytes=file_bytes,
            employee_id=employeeId,
            department_id=departmentId,
            receipt_id_override=receipt_id
        )
        results.append(parse_resp)
        amt = parse_resp.extraction.amount
        total_amount += amt

        if parse_resp.approval.recommendation == "AUTO_APPROVE" and parse_resp.compliance.status == "APPROVED":
            approved_count += 1
        else:
            flagged_count += 1

    duration = time.time() - start_time
    duration_str = f"{duration:.2f} seconds"

    return BulkUploadResponse(
        batchId=batch_id,
        processed=len(results),
        approved=approved_count,
        flagged=flagged_count,
        totalAmount=round(total_amount, 2),
        processingTime=duration_str,
        results=results
    )


@app.get("/api/analytics/dashboard", response_model=AnalyticsDashboardResponse)
async def get_analytics_dashboard():
    """Retrieve finance dashboard metrics, category/department breakdowns, and flagged items."""
    summary_data = get_analytics_summary()
    trends_data = get_analytics_trends()
    flagged_data = get_flagged_receipts()

    return AnalyticsDashboardResponse(
        summary=AnalyticsSummary(**summary_data),
        trends=AnalyticsTrends(**trends_data),
        flagged=[FlaggedReceiptItem(**item) for item in flagged_data]
    )


@app.get("/api/receipts/{receipt_id}")
async def fetch_receipt(receipt_id: str):
    """Retrieve full details of a previously parsed receipt."""
    receipt = get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


@app.get("/api/receipts/employee/{employee_id}")
async def fetch_employee_receipts(employee_id: str, limit: int = Query(50, ge=1, le=200)):
    """Retrieve receipt history for a given employee."""
    return get_employee_history(employee_id, limit=limit)


@app.get("/api/receipts")
async def fetch_all_receipts(limit: int = Query(100, ge=1, le=500)):
    """Retrieve recent receipts list."""
    return get_all_receipts(limit=limit)


@app.get("/api/debug")
async def debug_env():
    """Expose API config status for diagnosing live deployment issues."""
    import os
    import anthropic
    from app.config import get_anthropic_key, get_anthropic_workspace_id

    api_key = get_anthropic_key()
    workspace_id = get_anthropic_workspace_id()

    result = {
        "api_key_set": bool(api_key),
        "api_key_prefix": api_key[:15] + "..." if api_key else None,
        "workspace_id_set": bool(workspace_id),
        "workspace_id": workspace_id or None,
        "claude_test": None,
        "error": None,
    }

    if api_key:
        try:
            extra_headers = {"anthropic-workspace-id": workspace_id} if workspace_id else {}
            client = anthropic.Anthropic(api_key=api_key, default_headers=extra_headers)
            msg = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "Say OK"}],
            )
            result["claude_test"] = msg.content[0].text.strip()
        except Exception as exc:
            result["error"] = str(exc)

    return result

