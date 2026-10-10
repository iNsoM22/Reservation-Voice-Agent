# Patient Registration Voice Agent

Python backend for a patient-registration voice-agent assessment. The patient REST API, admin dashboard, and provider-independent browser simulation work locally. The Vapi call webhook remains a stub and does **not** register callers. No phone number or deployment is configured yet.

## TL;DR

Use Vapi for the inbound U.S. phone number, speech and LLM; this FastAPI app for validated patient records; SQLite for local persistent storage; and a Cloudflare Quick Tunnel for a temporary public test URL. The Vapi number and initial credits may allow a short test with no upfront payment, but calls are metered and the tunnel requires this computer to stay running.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
Copy-Item .env.example .env
# Edit .env, including the dashboard credentials and session secret, before exposing the app.
uv run python -m scripts.create_admin
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

For a public tunnel, use `cloudflared tunnel --url http://localhost:8000` in another terminal after installing `cloudflared`. The tunnel URL changes when restarted. Keep the app and tunnel running during evaluation.

Do not commit `.env` or `patients.db`. Use synthetic patient data only.

## Configuration

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy URL. Defaults to local `sqlite:///./patients.db`; `postgresql://` URLs are normalized to `postgresql+psycopg://`. |
| `API_KEY` | Required `X-API-Key` for `/patients` routes. Without it, protected routes return 503. |
| `VAPI_WEBHOOK_TOKEN` | Required bearer token for `POST /calls/vapi`. Without it, the webhook returns 503. Configure the matching credential in Vapi. |
| `ADMIN_EMAIL` | Email used to create the initial dashboard administrator. |
| `ADMIN_PASSWORD` | Password used to create the initial dashboard administrator. |
| `DASHBOARD_SESSION_SECRET` | Long random secret used to sign dashboard sessions and CSRF tokens. |

Run `uv run python -m scripts.create_admin` after setting the admin values to create the account. The command refuses to overwrite an existing administrator.

The app creates the patient table at startup. For a long-lived deployment, add migrations before changing the schema.

## API

Success responses use `{ "data": ..., "error": null }`. Error responses use `{ "data": null, "error": { "code": "...", "message": "..." } }`; invalid input also includes field details.

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/health` | Public process health check. |
| `GET` | `/patients` | List active patients; optional exact filters `last_name`, `date_of_birth` (`MM/DD/YYYY`), `phone_number` (10 digits). |
| `GET` | `/patients/{id}` | Get an active patient by UUID. |
| `POST` | `/patients` | Create a patient; required fields follow the challenge data model. |
| `PUT` | `/patients/{id}` | Update only supplied fields. |
| `DELETE` | `/patients/{id}` | Soft delete a patient. |
| `POST` | `/calls/vapi` | Authenticated Vapi event endpoint; registration tool is currently a stub. |
| `GET` | `/dashboard/login` | Dashboard sign-in page. |
| `GET` | `/dashboard/patients`, `/dashboard/calls` | Authenticated patient and call-log pages. |
| `GET` | `/dashboard/simulation` | Authenticated browser call simulation. |
| `POST` | `/dashboard/simulation/calls`, `/dashboard/simulation/calls/{id}/turn` | Start and continue an admin-session-bound simulation; require the dashboard CSRF token. |

Example local call:

```powershell
$headers = @{ 'X-API-Key' = 'your-api-key' }
Invoke-RestMethod http://localhost:8000/patients -Headers $headers
```

## Architecture and tests

`app/validations` owns Pydantic DTOs; `app/models` owns SQLAlchemy tables; `app/services` owns patient writes/queries and call logs; `app/routes` owns HTTP transport and authentication; `app/config` owns settings. The browser simulation uses native Web Speech APIs and `PatientCreate`/`PatientService`, and saves only after a readback and explicit confirmation. Speech recognition is not supported in every browser and some browser implementations use a vendor service to process audio; it is not guaranteed to run locally or offline. Text entry remains available. The Vapi tool endpoint is separate and still does not register patients.

```powershell
uv run python -m pytest -q
uv run ruff check .
uv run ruff format --check .
```

## Current limitations and next steps

- Live phone registration, conversation prompt, Vapi assistant/number, and deployment remain unconfigured. The Vapi webhook returns `error` for each tool call and cannot save patient data. Use `/dashboard/simulation` to exercise the independent browser flow.
- A Vapi free number does not make calls free indefinitely. Check current credits and billing before a live review.
- Local SQLite persists across app restarts, but the app and tunnel must stay online. A Quick Tunnel has a temporary hostname and no uptime guarantee.
- Patient API uses a shared API key. This is assessment-grade access control, not a production healthcare identity model.
- The challenge requests final payload logs; logging patient demographics is intentionally deferred until synthetic-data handling and retention are defined.
- Live phone number: **not provisioned**. Live API URL: **not deployed**. Add both here before submission.
