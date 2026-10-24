# Backend Quickstart

The full architecture, Expo configuration, Meta setup, tunnel instructions, local curl test, and troubleshooting guide are in the [repository README](../README.md).

From this directory in PowerShell:

```powershell
Copy-Item .env.example .env
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8000`, with OpenAPI docs at `/docs`. SQLite initializes automatically at the path configured by `DATABASE_URL`. Local routes include `GET /health`, `GET /leads`, `GET /leads/{lead_id}`, `POST /leads`, `GET/POST /webhook/meta`, and `WS /ws/leads`.

Run tests from this directory with `python -m pytest tests -q`.