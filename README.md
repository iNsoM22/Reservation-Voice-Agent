# Patient Registration Voice Agent

Python backend for a patient-registration voice agent deployed on Heroku and connected to a configured Vapi assistant. It includes a patient REST API, authenticated Vapi webhook, administrator dashboard, call observability pages, and browser voice simulation. The live app URL, phone number, and provider settings are not stored in this repository.

## TL;DR

Vapi runs the voice assistant, inbound calls, and browser voice sessions. Heroku runs the FastAPI app and its Vapi webhook; Heroku Postgres should hold durable patient and call records. SQLite remains the local development default.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
Copy-Item .env.example .env
# Edit .env, including the dashboard credentials and session secret, before exposing the app.
uv run python -m scripts.create_admin
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

For Heroku, deploy this project directory with its root `Procfile`; set the variables below as config vars and attach Heroku Postgres for persistent records. The `web` process runs Uvicorn on Heroku's `$PORT`. Verify `/health` on the deployed app and open `/` for the dashboard login. Keep a web dyno running for Vapi webhooks; an H14 response means no web process is running.

To review or update the Vapi assistant, tools, webhook credential, and inbound number, follow [Vapi setup](docs/VAPI_SETUP.md). Publish prompt changes in Vapi; editing the repository prompt alone does not change the saved assistant.

Do not commit `.env` or `patients.db`. Use synthetic patient data only.

## Configuration

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy URL. Defaults to local `sqlite:///./patients.db`; Heroku's `postgres://` and `postgresql://` URLs are normalized to `postgresql+psycopg://`. |
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
| `GET` | `/`, `/dashboard/patients`, `/dashboard/patients/{id}` | Authenticated patient list and detail pages. |
| `GET` | `/dashboard/calls`, `/dashboard/calls/{id}` | Authenticated call list and detail pages with transcript and report data. |
| `GET` | `/dashboard/simulation` | Authenticated browser voice call with the saved Vapi assistant. |
| `POST` | `/dashboard/simulation/number` | Authenticated, CSRF-protected issuance of a signed test caller number. |

Example local call:

```powershell
$headers = @{ 'X-API-Key' = 'your-api-key' }
Invoke-RestMethod http://localhost:8000/patients -Headers $headers
```

## Architecture and tests

`app/validations` owns Pydantic DTOs; `app/models` owns SQLAlchemy tables; `app/services` owns patient writes/queries and call logs; `app/routes` owns HTTP transport and authentication; `app/config` owns settings. Vapi registration and REST share `PatientCreate` and `PatientService`. When Vapi supplies conversation messages, the voice webhook checks the final readback question, affirmative reply, and name/sex values before saving the patient and call link in one transaction. Vapi may send an empty message artifact; in that case, the webhook relies on the assistant's tool invocation and the published prompt to enforce spoken confirmation. Replayed calls return the existing result. Phone and browser calls use the same saved Vapi assistant, tools, webhook, and call-log path; the browser page uses Vapi's Web SDK and requires microphone access. The simulation page issues a signed test caller number for browser calls. Registration requires the confirmed phone number to match it; lookup uses that number plus last name and DOB. Existing records can be found only when their stored phone number matches the test number.

The Vapi assistant prompt and exact tool parameter schemas live in `app/prompts/`. The `lookup_patient` tool accepts inbound calls and signed browser simulations, searches only records for the provider caller number or signed test number, and additionally requires last name and DOB. It rejects tool arguments that try to select a phone number or patient ID. Caller ID can be spoofed, so this is assessment-grade verification with synthetic data, not strong identity proof.

```powershell
uv run python -m pytest -q
uv run ruff check .
uv run ruff format --check .
```

## Observability and current limits

- The patient list and detail pages show saved registrations. The call list and detail pages show persisted calls, transcripts, report data, and linked patients when available. Vapi's own webhook logs remain useful for checking delivery failures.
- A simulation requires microphone permission and a 10-digit U.S. test caller number. The server signs that number for the browser call; lookup matches it with the spoken last name and DOB. The signed number expires after one hour.
- The revised browser-lookup prompt must be published in the saved Vapi assistant before testing it live. Repository tests cannot verify published prompt contents, live audio, or provider delivery.
- Browser calls consume Vapi resources; check account credits and billing before testing.
- Heroku needs a persistent `DATABASE_URL` such as Heroku Postgres. Local SQLite persists only on the local machine.
- Patient API uses a shared API key. This is assessment-grade access control, not a production healthcare identity model.
- Confirmed Vapi registrations persist their conversation and patient link, and end-of-call reports add final call details. Logs can contain synthetic demographic data; use test data only.
- The live Heroku URL and Vapi phone number were not supplied for this documentation update. Add them before sharing the demo.
