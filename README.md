# Smart Expense Receipt Parser (Prototype)

Prototype FastAPI service that returns a mocked parsed receipt response.

Quick start

1. Create a virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Run the app:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

4. Run tests:

```powershell
python -m pytest -q
```

API

- POST `/api/parse-receipt` — form multipart with `employeeId`, `departmentId`, and `image` file. Returns mocked parsed JSON matching PRD.
