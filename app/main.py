from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from contextlib import asynccontextmanager
from typing import Optional, List
from app.schemas import ParseResponse
from app.ocr_adapter import extract_from_image
from app.validator import validate_extraction
from app.audit_engine import audit_expense
from app.db import (
    init_db,
    save_receipt,
    get_receipt,
    check_duplicate_receipt,
    get_employee_history,
    get_all_receipts
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Receipt Parser Agent", lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "ok", "service": "receipt-parser"}


@app.post("/api/parse-receipt")
async def parse_receipt(
    employeeId: str = Form(...),
    departmentId: str = Form(...),
    image: UploadFile = File(...)
):
    # Read image bytes
    image_bytes = await image.read()
    # Try running real OCR; adapter will fall back to mock if unavailable or invalid image
    data = extract_from_image(image_bytes)

    # Check for 24-hour duplicate transaction
    vendor = data["extraction"].get("vendor", "")
    amount = float(data["extraction"].get("amount", 0.0) or 0.0)
    receipt_date = data["extraction"].get("date")

    duplicate = check_duplicate_receipt(
        employee_id=employeeId,
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

    # Validate with Pydantic schema
    resp = ParseResponse(**data)
    resp_dict = resp.model_dump()

    # Persist receipt in SQLite
    save_receipt(resp_dict, employeeId, departmentId)

    return resp_dict


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
