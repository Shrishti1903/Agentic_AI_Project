from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from app.schemas import ParseResponse
from app.ocr_adapter import extract_from_image, _mock_extract

app = FastAPI(title="Receipt Parser Agent")

@app.get("/")
async def root():
    return {"status": "ok", "service": "receipt-parser"}

@app.post("/api/parse-receipt")
async def parse_receipt(employeeId: str = Form(...), departmentId: str = Form(...), image: UploadFile = File(...)):
    # Read image bytes
    image_bytes = await image.read()
    # Try running real OCR; adapter will fall back to mock if unavailable or invalid image
    data = extract_from_image(image_bytes)
    resp = ParseResponse(**data)
    return resp.model_dump()
