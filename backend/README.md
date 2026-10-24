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

Before using the protected leads API, set `ADMIN_EMAIL`, `ADMIN_PASSWORD_HASH`, and `JWT_SECRET_KEY` in `.env`. Generate the hash and signing key with:

```powershell
python -c "import getpass; from pwdlib import PasswordHash; print(PasswordHash.recommended().hash(getpass.getpass('Admin password: ')))"
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Sign in with `POST /auth/login` to get a one-hour bearer token. The leads endpoints require it; the app obtains a short-lived WebSocket ticket from `POST /auth/ws-ticket`. Set `CORS_ORIGINS` to exact web client origins if using Expo web; native mobile requests do not use browser CORS. Do not use real leads until these secrets are set. The Meta webhook remains public but validates Meta's request signature.

Run tests from this directory with `python -m pytest tests -q`.