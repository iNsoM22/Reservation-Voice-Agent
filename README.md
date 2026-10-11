# Patient Registration Voice Agent

Python backend for a patient-registration voice-agent assessment. The patient REST API, admin dashboard, authenticated Vapi webhook, and browser voice page are implemented. Provider configuration and a live call check are still required. No phone number or deployment is configured yet.

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

To connect a real phone, follow [Vapi live-call setup](docs/VAPI_SETUP.md). The Vapi account, public URL, assistant, and number must be supplied in that dashboard. The backend cannot provision them without provider access.

Do not commit `.env` or `patients.db`. Use synthetic patient data only.

## Configuration

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy URL. Defaults to local `sqlite:///./patients.db`; `postgresql://` URLs are normalized to `postgresql+psycopg://`. |
| `API_KEY` | Required `X-API-Key` for `/patients` routes. Without it, protected routes return 503. |
| `VAPI_WEBHOOK_TOKEN` | Required bearer token for `POST /calls/vapi`. Without it, the webhook returns 503. Configure the matching credential in Vapi. |
| `VAPI_PUBLIC_KEY` | Vapi public key for browser voice calls. Restrict it to the dashboard origin and saved assistant in Vapi. |
| `VAPI_ASSISTANT_ID` | ID of the same saved Vapi assistant assigned to the phone number. |
| `ADMIN_EMAIL` | Email used to create the initial dashboard administrator. |
| `ADMIN_PASSWORD` | Password used to create the initial dashboard administrator. |
| `DASHBOARD_SESSION_SECRET` | Long random secret used to sign dashboard sessions and CSRF tokens. |

Run `uv run python -m scripts.create_admin` after setting the admin values to create the account. The command refuses to overwrite an existing administrator.

The app creates all model tables at startup, including patients, users, and call logs. For a long-lived deployment, add migrations before changing the schema.

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
| `POST` | `/calls/vapi` | Authenticated Vapi webhook for confirmed registration, caller-bound lookup, and end-of-call reports. |
| `GET` | `/dashboard/login` | Dashboard sign-in page. |
| `GET` | `/dashboard/patients`, `/dashboard/calls` | Authenticated patient and call-log pages. |
| `GET` | `/dashboard/simulation` | Authenticated browser voice call with the saved Vapi assistant. |

Example local call:

```powershell
$headers = @{ 'X-API-Key' = 'your-api-key' }
Invoke-RestMethod http://localhost:8000/patients -Headers $headers
```

## Architecture and tests

`app/validations` owns Pydantic DTOs; `app/models` owns SQLAlchemy tables; `app/services` owns patient writes/queries and call logs; `app/routes` owns HTTP transport and authentication; `app/config` owns settings. Vapi registration and REST share `PatientCreate` and `PatientService`. The voice webhook checks the call transcript for a matching readback and explicit confirmation, then saves the patient and call link in one transaction. Replayed calls return the existing result. Phone and browser calls use the same saved Vapi assistant, tools, webhook, and call-log path; the browser page uses Vapi's voice widget and requires microphone access. Web calls do not have an inbound caller number, so existing-record lookup remains phone-only.

The Vapi assistant prompt and exact tool parameter schemas live in `app/prompts/`. The `lookup_patient` tool is limited to inbound phone calls, searches only records for the caller number supplied by Vapi, and additionally requires last name and DOB. It rejects tool arguments that try to select a phone number or patient ID. Caller ID can be spoofed, so this is assessment-grade verification with synthetic data, not strong identity proof.

```powershell
uv run python -m pytest -q
uv run ruff check .
uv run ruff format --check .
```

## Current limitations and next steps

- The Vapi prompt and registration webhook are implemented, but the assistant, number, and deployment require provider access. A real call is still needed to validate Vapi's actual transcript shape and audio flow.
- The browser voice page now uses the actual Vapi assistant, but it cannot be exercised until the public key, assistant, HTTPS webhook, and provider account are configured. Browser calls may consume Vapi credits.
- A Vapi free number does not make calls free indefinitely. Check current credits and billing before a live review.
- Local SQLite persists across app restarts, but the app and tunnel must stay online. A Quick Tunnel has a temporary hostname and no uptime guarantee.
- Patient API uses a shared API key. This is assessment-grade access control, not a production healthcare identity model.
- Confirmed Vapi registrations persist their conversation and patient link, and end-of-call reports add final call details. Logs can contain synthetic demographic data; use test data only.
- Live phone number: **not provisioned**. Live API URL: **not deployed**. Add both here before submission.
