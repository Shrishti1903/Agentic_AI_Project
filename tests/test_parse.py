from fastapi.testclient import TestClient
from app.main import app
from app.ocr_adapter import _mock_extract

client = TestClient(app)

def test_root():
    r = client.get('/')
    assert r.status_code == 200
    # Root now serves the Web UI (text/html); fall back to JSON health check
    # when the static/ directory is absent (e.g. CI without assets).
    if "text/html" in r.headers.get("content-type", ""):
        assert "<!DOCTYPE html>" in r.text
    else:
        assert r.json().get('status') == 'ok'

def test_parse_receipt():
    files = {
        'image': ('dummy.jpg', b'fake-image-bytes', 'image/jpeg')
    }
    data = {'employeeId': 'emp_123', 'departmentId': 'dept_sales'}
    r = client.post('/api/parse-receipt', data=data, files=files)
    assert r.status_code == 200
    j = r.json()
    assert j['receiptId'] == 'rcpt_demo_001'
    assert j['extraction']['vendor'] == 'Chipotle'
    assert abs(j['extraction']['amount'] - 12.99) < 0.001

def test_ocr_adapter_mock_fallback():
    """Mock extraction must return a structurally valid result (no API key needed)."""
    result = _mock_extract()
    assert "receiptId" in result
    assert "extraction" in result
    assert "categorization" in result
    assert "compliance" in result
    assert "approval" in result
    ext = result["extraction"]
    assert isinstance(ext["vendor"], str)
    assert isinstance(ext["amount"], (int, float))
    assert isinstance(ext["items"], list)
    assert 0.0 <= ext["confidence"] <= 1.0
