# Meta Lead Ads + React Native PoC

A small end-to-end proof of concept that stores Meta Lead Ads submissions in SQLite and streams newly received leads to an open Expo app over WebSocket.

## Architecture

```text
Meta Lead Testing Tool
  -> Meta Page leadgen webhook (public HTTPS)
  -> FastAPI verifies request signature and reads leadgen_id
  -> Graph API retrieves submitted form fields
  -> SQLite stores the normalized lead
  -> FastAPI broadcasts new_lead over WebSocket
  -> Expo app merges the event into FlatList state
```

Responsibilities:

- Meta sends a webhook notification containing a lead ID; the notification is not treated as the submitted form data.
- FastAPI verifies the `X-Hub-Signature-256` HMAC using `META_APP_SECRET`, retrieves field data from Graph API using `META_ACCESS_TOKEN`, persists it, and broadcasts only newly inserted lead IDs.
- SQLite is the durable source for `GET /leads`; when the backend has no leads, the app shows an empty state.
- The mobile service loads `/leads`, then stays connected to `/ws/leads`. It deduplicates events and retries dropped connections without requiring a device interaction.
- `POST /leads` creates a development lead and broadcasts it to connected clients. Use it only on the local development server.

## Project Layout

```text
mobile/                 Expo Router React Native app
  app/                  Leads screen and root layout
  components/           Lead card, loading, empty, connection states
  config/               Backend URL selection
  data/                 UI sample leads
  services/             HTTP and WebSocket client
  types/                Lead model
backend/                FastAPI app, SQLite store, and pytest tests
README.md
.gitignore
```

## Prerequisites

- Node.js LTS and npm
- Python 3.11 or newer
- Android Studio emulator with Expo Go, or an Android phone with Expo Go
- A Meta Developer app, Facebook Page, and a lead form for the Meta stage
- ngrok (or another public HTTPS tunnel) for Meta to reach local FastAPI

## Environment Setup

Create the backend environment file from the template:

```powershell
cd backend
Copy-Item .env.example .env
```

Edit `backend/.env` locally. Keep all credentials out of GitHub:

```dotenv
META_ACCESS_TOKEN=
META_VERIFY_TOKEN=use-a-long-random-string
META_APP_SECRET=
META_PAGE_ID=
META_API_VERSION=vXX.X
DATABASE_URL=sqlite:///./leads.db
PUBLIC_BACKEND_URL=https://your-ngrok-domain.ngrok-free.app
```

Replace `META_API_VERSION` with a currently supported Graph API version shown in Meta's current documentation/dashboard before using Graph API. `vXX.X` is deliberately a placeholder, not an API version. Never put the Meta access token or app secret in the mobile app. The verify token is an arbitrary shared string used only for the initial webhook challenge.

Copy the mobile example into a local environment file and adjust for the target device:

```powershell
Copy-Item mobile/.env.example mobile/.env
```

For Android emulator, `10.0.2.2` reaches the host machine. For a physical phone, set `EXPO_PUBLIC_API_URL` to the computer's LAN IP, e.g. `http://192.168.1.20:8000`; both devices must be on a reachable network. For web/iOS simulator, `http://localhost:8000` usually works. For Expo Go on a phone while using the public tunnel, use the HTTPS tunnel URL for API and the app will derive WSS automatically. Restart Expo after changing `.env`.

## Run FastAPI

From `backend/` in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check `http://localhost:8000/health`, `http://localhost:8000/leads`, and interactive API docs at `http://localhost:8000/docs`. SQLite is created at `backend/leads.db` by default. Existing databases using the previous schema are migrated on startup when `DATABASE_URL` points to that file.

## Local Real-Time Test

1. Start FastAPI using the command above.
2. Set `EXPO_PUBLIC_API_URL` for the target device and start the Expo app (next section).
3. Open Leads and wait for the `Live connection` indicator.
4. From a separate PowerShell window, run:

```powershell
$body = @{ meta_lead_id = "local-demo-001"; name = "Harsha Test"; email = "harsha@test.com"; phone = "+91 9999999999"; form_id = "local-form"; page_id = "local-page" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/leads -ContentType "application/json" -Body $body
```

Equivalent curl command:

```bash
curl -X POST http://localhost:8000/leads \
  -H "Content-Type: application/json" \
  -d '{"meta_lead_id":"local-demo-001","name":"Harsha Test","email":"harsha@test.com","phone":"+91 9999999999","form_id":"local-form","page_id":"local-page"}'
```

The new lead should appear in the already-open app immediately and the count should increase. No app refresh or device tap is needed. Reusing an existing Meta lead ID returns the existing record and intentionally does not create or broadcast a duplicate.

## Run the Mobile App

From the repository root:

```powershell
npm --prefix .\mobile install
npm --prefix .\mobile run start
```

Scan the Expo QR code with Expo Go, or press `a` to launch an Android emulator. To preview the screen in a browser, press `w`. Ensure the backend URL in `mobile/.env` is reachable from that device. In Android emulator, use `http://10.0.2.2:8000`, not `localhost`.

## HTTPS Tunnel

Start the backend on port 8000, then in another terminal:

```powershell
ngrok http 8000
```

Copy the HTTPS forwarding address (for example `https://example.ngrok-free.app`) into `PUBLIC_BACKEND_URL` and use it as the mobile API base when testing from a phone outside the LAN. Meta callback URL is:

```text
https://example.ngrok-free.app/webhook/meta
```

The tunnel must remain running, and its address must match the URL configured in Meta. Free tunnel addresses can change after restart; update Meta's callback and mobile `.env` accordingly.

## Meta Configuration

Meta's interface, permissions, review requirements, supported API versions, and lead access rules change over time. Verify every step against the current Meta for Developers documentation and dashboard; this PoC does not assume a particular current UI label or permission approval state.

1. Create/select a Meta Developer app and add/configure the relevant Facebook Login/Marketing API products as currently required for Lead Ads access.
2. Associate the Facebook Page and create a lead form that is available for testing. The Meta user/app must have the access needed to manage that Page and retrieve its leads.
3. Configure environment values: app secret from app settings, a long random `META_VERIFY_TOKEN`, a Page-authorized access token with the currently required lead retrieval permissions, `META_PAGE_ID`, and a supported `META_API_VERSION`.
4. In Webhooks, subscribe the app to the Page object and the `leadgen` field (exact navigation/permission names may change). Use callback URL `https://<public-host>/webhook/meta` and enter the exact `META_VERIFY_TOKEN` value.
5. Meta sends a GET challenge. FastAPI compares the mode/token and returns `hub.challenge`. A mismatch returns HTTP 403.
6. Subscribe the Facebook Page to the app for Lead Ads notifications using the current Meta-supported Page subscription workflow. App-level webhook subscription alone may not be sufficient; confirm the Page is subscribed in the dashboard/API.
7. Use Meta's Lead Ads Testing Tool to select the Page/form and create a test lead. A webhook payload's `leadgen_id` is used to request `id,created_time,field_data` from Graph API. Check FastAPI logs and `/leads` if it does not arrive.

This backend requires a valid `X-Hub-Signature-256` whenever Meta's app secret is configured; requests are rejected if the secret/signature is missing or invalid. Do not expose the API publicly without setting `META_APP_SECRET`, `META_VERIFY_TOKEN`, and a suitable access token. The Graph API version is intentionally not hard-coded.

## End-to-End Test

1. Fill in backend secrets/configuration and start FastAPI.
2. Start the HTTPS tunnel and configure Meta's callback URL/verify token.
3. Start Expo with `EXPO_PUBLIC_API_URL` set to the reachable backend URL.
4. Leave the Leads screen open and confirm the live status.
5. Open Meta Lead Ads Testing Tool and submit a test lead for the configured Page/form.
6. Do not touch or refresh the mobile app. Confirm the count increases and the new lead appears.
7. Confirm persistence by querying `GET /leads` or restarting the app/backend.

## Testing Checklist

- [ ] Expo app opens to Leads, fetches backend records, and displays the existing empty state when the database is empty.
- [ ] FastAPI starts and `/health` responds.
- [ ] SQLite initializes and `GET /leads` returns stored records.
- [ ] WebSocket connects (live status shown in app).
- [ ] Local `POST /leads` stores and broadcasts a lead.
- [ ] Open app receives test lead and updates count without interaction.
- [ ] HTTPS tunnel URL reaches `/health`.
- [ ] Meta webhook challenge returns the challenge for the correct verify token.
- [ ] Invalid webhook signature is rejected.
- [ ] Meta Lead Testing Tool sends a lead notification to FastAPI.
- [ ] Graph API retrieves the lead fields and the lead appears in the app.

Run backend tests from the backend directory using the same Python environment in which backend dependencies are installed:

```powershell
Set-Location backend
python -m pytest tests -q
```

Run mobile type checking:

```powershell
Set-Location mobile
npx tsc --noEmit
```

## Loom #1: Five-Minute Live Demo

1. Prepare the phone/emulator with the Leads screen already open and live status visible.
2. Show FastAPI and the HTTPS tunnel running, but keep the app on screen.
3. Open Meta Lead Testing Tool and select the intended Page/form.
4. Submit the test lead.
5. Keep hands off the mobile device; capture the live count increment and new card.
6. Briefly show the saved lead in `GET /leads` or API logs as confirmation.

Use the local `POST /leads` flow for a rehearsal. For the Meta demonstration, ensure token permissions, page subscription, webhook subscription, and Graph API retrieval have all been confirmed beforehand.

## Loom #2: Architecture Explanation

Explain this path in order:

1. Meta Lead Testing Tool creates a test submission for a Page form.
2. Meta Webhook sends a lead ID to the public HTTPS callback.
3. FastAPI verifies the signed request and requests actual fields from Graph API.
4. SQLite persists the normalized lead and provides history to `GET /leads`.
5. WebSocket at `/ws/leads` broadcasts a `new_lead` event with the record under `data`.
6. React Native merges the event by lead ID into FlatList state, updating count and UI immediately.

Mention that HTTP loads history, WebSocket handles new arrivals, and the device requires no refresh. Mention that Graph API credentials stay only on the backend.

## Assumptions and Limitations

- This is a single-process, one-week PoC. WebSocket clients are in process memory; multiple backend workers need a shared pub/sub layer.
- The unauthenticated `POST /leads` endpoint is intended for local development/demo only; protect or disable it before public deployment.
- Graph API field names and access requirements depend on the current form configuration and Meta policy. The extractor recognizes common full name, email, and phone field names; adjust it for custom form field keys.
- Meta webhook delivery is retried by Meta, and lead IDs are idempotent in SQLite. This implementation does not persist a webhook delivery queue or retry Graph API failures asynchronously.
- App-level FastAPI CORS is permissive for local development. Production deployments should restrict origins and add rate limits/monitoring.
- App must be foreground/open for the live WebSocket demo; background delivery and push notifications are not included.
- No credentials should be committed. `.env`, local SQLite data, virtual environments, node modules, and Expo state are ignored.

## Troubleshooting

- **App says backend unavailable:** verify FastAPI is running, `GET /health` works, and the device-specific URL is set. Android emulator uses `10.0.2.2`; a phone uses the host LAN IP or reachable HTTPS tunnel.
- **WebSocket stays disconnected:** confirm URL is `ws://` on local HTTP or `wss://` on HTTPS and the backend/tunnel permits WebSocket upgrades. Restart Expo after editing `.env`.
- **Webhook verification fails:** compare `META_VERIFY_TOKEN` exactly with the Meta callback token and verify the callback path ends in `/webhook/meta`.
- **Webhook arrives but no lead card:** inspect backend logs. Confirm `META_APP_SECRET` matches the app, signature verification succeeds, `META_ACCESS_TOKEN` can access that Page's lead, and Graph API version is currently supported.
- **Graph API reports permission/access errors:** verify the current Meta permission, Page task, app mode/review state, token type/expiry, Page subscription, and form ownership in Meta documentation/dashboard.
- **ngrok URL no longer works:** update `PUBLIC_BACKEND_URL`, Meta callback URL, and phone's `EXPO_PUBLIC_API_URL` after tunnel address changes.
- **Port already in use:** choose another Uvicorn port and tunnel that port, updating both mobile and Meta callback configuration as appropriate.

## GitHub Checklist

- [ ] Commit source, tests, lockfiles, README, and `.env.example` only.
- [ ] Confirm `.env`, access tokens, app secrets, database files, and local logs are not staged.
- [ ] Rotate any credential accidentally exposed in chat, terminal logs, or Git history.
- [ ] Include the exact Meta API version and permission state used for the demo in private project notes, not committed secrets.