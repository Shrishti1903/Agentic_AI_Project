from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    r = client.get('/')
    assert r.status_code == 200
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
