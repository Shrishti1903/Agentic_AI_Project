"""OCR adapter module.

Provides `extract_from_image(image_bytes)` which:
  - Uses OpenAI GPT-4o Vision when OPENAI_API_KEY is set (production).
  - Falls back to the mock extraction when the key is absent (tests / local dev).

The downstream pipeline (categorizer, validator, audit_engine) is unchanged.
"""
import base64
import io
import json
import uuid
from typing import Dict

from app.categorizer import categorize_expense
from app.validator import validate_extraction
from app.audit_engine import audit_expense
from app.config import get_openai_key


# ---------------------------------------------------------------------------
# Mock extraction (used when no API key is configured)
# ---------------------------------------------------------------------------

def _mock_extract() -> Dict:
    extraction_data = {
        "vendor": "Chipotle",
        "amount": 12.99,
        "currency": "USD",
        "date": "2026-09-15",
        "time": "12:30 PM",
        "itemsCount": 3,
        "items": [
            {"name": "Burrito Bowl", "quantity": 1, "price": 8.99},
            {"name": "Drink",        "quantity": 1, "price": 2.99},
            {"name": "Tax",          "quantity": 1, "price": 0.99},
        ],
        "paymentMethod": "Credit Card",
        "category": "Meals & Entertainment",
        "confidence": 0.97,
    }
    cat = categorize_expense(extraction_data["vendor"], extraction_data["items"])
    extraction_data["category"] = cat.category
    val = validate_extraction(extraction_data)
    compliance, approval = audit_expense(extraction_data, cat, val)
    return {
        "receiptId": "rcpt_demo_001",
        "extraction": extraction_data,
        "categorization": cat.model_dump(),
        "compliance": compliance.model_dump(),
        "approval": approval.model_dump(),
    }


# ---------------------------------------------------------------------------
# GPT-4o Vision extraction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a receipt parser AI.
Extract structured data from the receipt image and return ONLY valid JSON with this exact schema:
{
  "vendor": "<store / restaurant name>",
  "amount": <total numeric amount as float>,
  "currency": "<3-letter code, default USD>",
  "date": "<YYYY-MM-DD or 'unknown'>",
  "time": "<HH:MM AM/PM or null>",
  "itemsCount": <integer count of line items>,
  "items": [{"name": "<item>", "quantity": <int>, "price": <float>}],
  "paymentMethod": "<Cash|Credit Card|Debit Card|Other or null>",
  "confidence": <0.0-1.0 confidence score for the extraction>
}
Return ONLY the JSON object, no markdown, no explanation."""


def _gpt4o_extract(image_bytes: bytes, api_key: str) -> Dict:
    """Call GPT-4o Vision and return structured extraction data."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    # Detect MIME type for the data URI
    mime = "image/jpeg"
    if image_bytes[:4] == b"\x89PNG":
        mime = "image/png"
    elif image_bytes[:4] in (b"GIF8", b"GIF9"):
        mime = "image/gif"
    elif image_bytes[:2] == b"BM":
        mime = "image/bmp"

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:{mime};base64,{b64}"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri, "detail": "high"},
                    },
                    {
                        "type": "text",
                        "text": "Extract all receipt data as JSON.",
                    },
                ],
            },
        ],
        max_tokens=1024,
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()

    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    extraction_data = json.loads(raw)

    # Ensure required keys exist with sensible defaults
    extraction_data.setdefault("currency", "USD")
    extraction_data.setdefault("time", None)
    extraction_data.setdefault("itemsCount", len(extraction_data.get("items", [])))
    extraction_data.setdefault("paymentMethod", None)
    extraction_data.setdefault("confidence", 0.85)
    extraction_data.setdefault("items", [])

    # Run existing pipeline stages
    cat = categorize_expense(
        vendor=extraction_data.get("vendor", ""),
        items=extraction_data.get("items", []),
    )
    extraction_data["category"] = cat.category
    val = validate_extraction(extraction_data)
    compliance, approval = audit_expense(extraction_data, cat, val)

    return {
        "receiptId": f"rcpt_{uuid.uuid4().hex[:8]}",
        "extraction": extraction_data,
        "categorization": cat.model_dump(),
        "compliance": compliance.model_dump(),
        "approval": approval.model_dump(),
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract_from_image(image_bytes: bytes) -> Dict:
    """Parse a receipt image and return a structured extraction dict.

    - If ``OPENAI_API_KEY`` is set: calls GPT-4o Vision (production path).
    - If the key is absent or the API call fails: returns mock data (dev/test).
    """
    api_key = get_openai_key()

    if api_key:
        try:
            return _gpt4o_extract(image_bytes, api_key)
        except Exception as exc:
            # Log the error but don't crash — fall back gracefully
            import sys
            print(f"[ocr_adapter] GPT-4o call failed ({exc}), using mock.", file=sys.stderr)

    return _mock_extract()


__all__ = ["extract_from_image", "_mock_extract"]
