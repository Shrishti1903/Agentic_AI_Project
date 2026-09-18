from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from app.schemas import ParseResponse
from app.ocr_adapter import mock_extract

app = FastAPI(title="Receipt Parser Agent")

@app.get("/")
async def root():
    return {"status": "ok", "service": "receipt-parser"}

@app.post("/api/parse-receipt")
async def parse_receipt(employeeId: str = Form(...), departmentId: str = Form(...), image: UploadFile = File(...)):
    # For prototype, use a mocked OCR/vision adapter
    data = mock_extract()
    resp = ParseResponse(**data)
    return resp.dict()
