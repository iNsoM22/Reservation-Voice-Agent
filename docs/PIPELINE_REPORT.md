# Voice pipeline and deployment notes

## Current pipeline

| Step | Component | Behavior |
| --- | --- | --- |
| Phone and browser audio | Configured Vapi assistant | Vapi handles transcription, conversation, and voice output. The browser simulation uses the same saved assistant. |
| Public API and webhook | Heroku web dyno | The root `Procfile` runs FastAPI through Uvicorn. Vapi calls the deployed HTTPS `POST /calls/vapi` endpoint. |
| Tool handoff | Authenticated Vapi webhook | A bearer token authenticates `tool-calls` and `end-of-call-report` events. The adapter handles registration, lookup, and call reports. |
| Validation and persistence | Patient and call services | REST and Vapi share patient validation and persistence. A durable Heroku deployment needs a persistent database such as Heroku Postgres; local development defaults to SQLite. |
| Observability | Administrator dashboard and Vapi logs | Patient list/detail and call list/detail pages show saved records, linked calls, transcripts, and report data when present. Vapi webhook logs help diagnose delivery errors. |

Browser simulation issues a one-hour signed test caller number. Registration
requires its confirmed phone number to match; lookup combines that number with
last name and DOB. Phone lookup uses the inbound provider caller number. Tool
arguments cannot choose a lookup number or patient ID. Use synthetic data only.

## Verification still needed

- Confirm the deployed Heroku `DATABASE_URL` points to persistent storage and a
  patient survives a dyno restart.
- Publish the revised repository prompt in the saved Vapi assistant, then
  verify a registration and lookup in both phone and browser calls. Inspect
  Vapi webhook logs and the call-detail page for the actual event shape.
- Record the live app URL, Vapi number, and chosen Vapi providers in README
  when those details are available to share. They are not stored here.

## Cost and local alternative

Vapi calls and a continuously running Heroku web dyno can incur charges; check
the account's current plan and usage before testing. For temporary local
development, run FastAPI with SQLite and expose it through a tunnel. A local
SQLite file and temporary tunnel are not a substitute for persistent deployed
storage and a stable webhook URL.
