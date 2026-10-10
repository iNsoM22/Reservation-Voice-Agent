# Project notes

## Current state

- 2026-10-10: Reviewed `../Context/voice_ai_agent_coding_challenge.md` and the UV starter project.
- Current implementation: patient models/DTOs, patient service, authenticated REST CRUD, administrator bootstrap and session auth, Jinja patient dashboard, call-log views, and browser registration simulation are implemented. SQLite is the local persistent default; PostgreSQL URLs are supported.
- The Vapi endpoint authenticates callbacks and persists `end-of-call-report` reports for the call dashboard. Registration tool calls still return an error stub and do not write patients. No Vapi phone number, assistant, or public deployment is configured.
- The browser simulation supports text input plus optional browser speech, per-field `PatientCreate` validation, correction/readback, explicit save confirmation, persistent transcripts, and repeat-confirm idempotence. It is an independent demo flow, not evidence of live telephony integration.
- Historical verification counts from earlier implementation stages: 34 and then 48 pytest tests passed at those points, with Ruff lint/format checks passing then. These are not current verification claims.
- Review fixes include `updated_at` advancement for partial updates within one clock tick and generic database errors without logging patient query values.
- 2026-10-11 dashboard polish covered call list/detail views, transcript wrapping, timestamp display, table/navigation semantics, pagination keyboard behavior, and login validation feedback.

## Decisions

- Target stack: Vapi + FastAPI/Pydantic + SQLAlchemy + PostgreSQL + Railway, managed with uv. Use Ruff and pytest.
- Layout: `app/{validations,models,routes,services,config}` and mirrored `test/` packages.
- The REST routes use one patient service. The Vapi route should use that same service when its registration stub is replaced.
- Write tests first for every behavior; observe a meaningful failure before implementing.
- Keep all source and test files under 600 lines.
- For a no-upfront-payment demo, prefer Vapi trial number/credits + local SQLite/FastAPI + Cloudflare Quick Tunnel. This depends on an active laptop and remaining credits; it is not a permanent free hosting arrangement.

## Next actions

1. Confirm Vapi account, free inbound number, available credits, and model/voice/transcriber selections.
2. Create/publish the assistant prompt; configure the authenticated tool URL; inspect a real Vapi event.
3. Implement confirmed Vapi registration and retry idempotency using tests first; leave the webhook's report persistence intact.
4. Keep backend/tunnel live for review, test two real calls and restart persistence, and add actual number/API URL to README.

## Open issues / changes

- Live-call blocker: no Vapi account, number, credits, or provider credentials supplied in the workspace.
- Public URL blocker: no tunnel/domain is running; a Quick Tunnel URL is temporary and the local machine must remain online.
- Financial limit: Vapi's free number still consumes call credits; after trial credits, live calls require payment. See `docs/PIPELINE_REPORT.md`.
- Live-call blocker: the browser simulation exercises registration independently, but no Vapi credentials, phone number, or public endpoint are configured; real phone calls still cannot register patients.
- Scope boundary: Vapi end-of-call reports are persisted in call logs; registration tool calls deliberately return an error without saving. Voice confirmation, idempotency, and registration writes remain pending.
- Vapi documentation shows both `function.arguments` and simplified `name`/`parameters` tool-call shapes; the stub route accepts both. Confirm the shape of a real event before implementing writes.
- Restart persistence of a retained patient has not yet been exercised as a separate integration test or real process restart. Do this before the live demo.
