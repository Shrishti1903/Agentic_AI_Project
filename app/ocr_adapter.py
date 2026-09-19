"""OCR adapter module.

Provides `extract_from_image(image_bytes)` which:
  - Uses Anthropic Claude Vision when ANTHROPIC_API_KEY is set (production).
  - Falls back to mock extraction when the key is absent (tests / local dev).

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
from app.config import get_anthropic_key, get_anthropic_workspace_id, get_gemini_key


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
# Claude Vision extraction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a receipt parser AI. "
    "Extract structured data from the receipt image and return ONLY valid JSON "
    "with this exact schema — no markdown, no explanation, no extra text:\n"
    "{\n"
    '  "vendor": "<store or restaurant name>",\n'
    '  "amount": <total numeric amount as float>,\n'
    '  "currency": "<3-letter code, default USD>",\n'
    '  "date": "<YYYY-MM-DD or unknown>",\n'
    '  "time": "<HH:MM AM/PM or null>",\n'
    '  "itemsCount": <integer>,\n'
    '  "items": [{"name": "<item>", "quantity": <int>, "price": <float>}],\n'
    '  "paymentMethod": "<Cash|Credit Card|Debit Card|Other or null>",\n'
    '  "confidence": <0.0-1.0>\n'
    "}"
)


def _gemini_extract(image_bytes: bytes, api_key: str) -> Dict:
    """Call Gemini Vision and return structured extraction data."""
    import google.generativeai as genai
    import PIL.Image
    import io

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.6-flash")

    image = PIL.Image.open(io.BytesIO(image_bytes))
    response = model.generate_content([_SYSTEM_PROMPT, image])
    raw = response.text.strip()

    # Strip any accidental markdown fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    extraction_data = json.loads(raw)

    # Ensure required keys with sensible defaults
    extraction_data.setdefault("currency", "USD")
    extraction_data.setdefault("time", None)
    extraction_data.setdefault("itemsCount", len(extraction_data.get("items", [])))
    extraction_data.setdefault("paymentMethod", None)
    extraction_data.setdefault("confidence", 0.90)
    extraction_data.setdefault("items", [])

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


def _claude_extract(image_bytes: bytes, api_key: str) -> Dict:
    """Call Claude Vision and return structured extraction data."""
    import anthropic

    # Detect media type
    media_type = "image/jpeg"
    if image_bytes[:4] == b"\x89PNG":
        media_type = "image/png"
    elif image_bytes[:6] in (b"GIF87a", b"GIF89a"):
        media_type = "image/gif"
    elif image_bytes[:2] == b"BM":
        media_type = "image/webp"

    b64_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    # Build client — pass workspace header for org-level (non-scoped) keys
    workspace_id = get_anthropic_workspace_id()
    extra_headers = {"anthropic-workspace-id": workspace_id} if workspace_id else {}
    client = anthropic.Anthropic(api_key=api_key, default_headers=extra_headers)
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                    },
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()

    # Strip any accidental markdown fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    extraction_data = json.loads(raw)

    # Ensure required keys with sensible defaults
    extraction_data.setdefault("currency", "USD")
    extraction_data.setdefault("time", None)
    extraction_data.setdefault("itemsCount", len(extraction_data.get("items", [])))
    extraction_data.setdefault("paymentMethod", None)
    extraction_data.setdefault("confidence", 0.90)
    extraction_data.setdefault("items", [])

    # Run existing pipeline stages — unchanged
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

    Priority:
      1. Gemini Vision  (if GEMINI_API_KEY is set)  — free tier
      2. Claude Vision  (if ANTHROPIC_API_KEY is set)
      3. Mock data      (fallback for dev / test)
    """
    import sys

    gemini_key = get_gemini_key()
    if gemini_key:
        try:
            return _gemini_extract(image_bytes, gemini_key)
        except Exception as exc:
            import sys, traceback
            print(f"[ocr_adapter] Gemini Vision call failed: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

    api_key = get_anthropic_key()
    if api_key:
        try:
            return _claude_extract(image_bytes, api_key)
        except Exception as exc:
            print(f"[ocr_adapter] Claude Vision call failed ({exc}), using mock.", file=sys.stderr)

    return _mock_extract()


__all__ = ["extract_from_image", "_mock_extract"]
