# Project notes

## Current state

- 2026-10-10: Reviewed `../Context/voice_ai_agent_coding_challenge.md` and the UV starter project.
- Planning is in `docs/IMPLEMENTATION_PLAN.md`; patient models and DTO validation are now implemented.
- UV dependencies, lockfile, README, API routes, and the inert Vapi webhook are present. Live voice integration, phone number, and deployment are still pending.
- Review pass: tightened update DTO limits and database constraints; 34 pytest tests pass, Ruff lint and format checks pass.
- 2026-10-11: Added patient service, authenticated REST routes, settings, Vapi webhook adapter with inert call service, README, and pipeline report. SQLite is the local persistent default; PostgreSQL URLs are supported. 48 tests pass; Ruff lint and format checks pass.
- Review fix: partial updates now advance `updated_at` even within one clock tick; database errors return a generic 500 without logging patient query values.

## Decisions

- Target stack: Vapi + FastAPI/Pydantic + SQLAlchemy + PostgreSQL + Railway, managed with uv. Use Ruff and pytest.
- Layout: `app/{validations,models,routes,services,config}` and mirrored `test/` packages.
- The REST routes use one patient service. The Vapi route will use that same service after its registration stub is replaced.
- Write tests first for every behavior; observe a meaningful failure before implementing.
- Keep all source and test files under 600 lines.
- For a no-upfront-payment demo, prefer Vapi trial number/credits + local SQLite/FastAPI + Cloudflare Quick Tunnel. This depends on an active laptop and remaining credits; it is not a permanent free hosting arrangement.

## Next actions

1. Confirm Vapi account, free inbound number, available credits, and model/voice/transcriber selections.
2. Create/publish the assistant prompt; configure the authenticated tool URL; inspect a real Vapi event.
3. Add confirmation state and idempotency, then replace the call service stub using tests first.
4. Keep backend/tunnel live for review, test two real calls and restart persistence, and add actual number/API URL to README.

## Open issues / changes

- Live-call blocker: no Vapi account, number, credits, or provider credentials supplied in the workspace.
- Public URL blocker: no tunnel/domain is running; a Quick Tunnel URL is temporary and the local machine must remain online.
- Financial limit: Vapi's free number still consumes call credits; after trial credits, live calls require payment. See `docs/PIPELINE_REPORT.md`.
- Scope boundary: call service deliberately returns a Vapi tool error without saving. Confirmation, idempotency, and final payload logging remain for the voice integration phase.
- Vapi documentation shows both `function.arguments` and simplified `name`/`parameters` tool-call shapes; the stub route accepts both. Confirm the shape of a real event before implementing writes.
- Restart persistence of a retained patient has not yet been exercised as a separate integration test or real process restart. Do this before the live demo.
