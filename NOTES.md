# Project notes

## Current state

- 2026-10-10: Reviewed `../Context/voice_ai_agent_coding_challenge.md` and the UV starter project.
- Current implementation: patient models/DTOs, patient service, authenticated REST CRUD, administrator bootstrap and session auth, and Jinja patient and call-log views are implemented. The existing browser simulation requires rework. SQLite is the local persistent default; PostgreSQL URLs are supported.
- The Vapi endpoint authenticates callbacks, writes confirmed registrations through the shared patient service, and persists `end-of-call-report` reports for the call dashboard. No Vapi phone number, assistant, or public deployment is configured.
- The current browser simulation supports text input and optional browser speech, but its scripted, field-by-field intake does not exercise the actual Vapi agent or voice pipeline. The project owner considers this feature incorrect. Rework is deferred to a later task and is required before the project can be considered complete.
- Historical verification counts from earlier implementation stages: 34 and then 48 pytest tests passed at those points, with Ruff lint/format checks passing then. These are not current verification claims.
- Review fixes include `updated_at` advancement for partial updates within one clock tick and generic database errors without logging patient query values.
- 2026-10-11 dashboard polish covered call list/detail views, transcript wrapping, timestamp display, table/navigation semantics, pagination keyboard behavior, and login validation feedback.
- Reliability review added conflict-safe admin bootstrap, turn sequence checks for simulation retries, and one transaction for simulation patient creation and call completion. The current full suite has 71 passing tests; Ruff checks pass.

## Decisions

- Target stack: Vapi + FastAPI/Pydantic + SQLAlchemy + PostgreSQL + Railway, managed with uv. Use Ruff and pytest.
- Layout: `app/{validations,models,routes,services,config}` and mirrored `test/` packages.
- REST and Vapi registration share the same patient validation and service.
- Write tests first for every behavior; observe a meaningful failure before implementing.
- Keep all source and test files under 600 lines.
- For a no-upfront-payment demo, prefer Vapi trial number/credits + local SQLite/FastAPI + Cloudflare Quick Tunnel. This depends on an active laptop and remaining credits; it is not a permanent free hosting arrangement.

## Next actions

1. Rework the dashboard simulation to meet the project owner's intended agent-testing behavior; clarify the target integration when that work begins. This is a completion blocker, not an optional enhancement.
2. Confirm Vapi account, free inbound number, available credits, and model/voice/transcriber selections.
3. Create/publish the assistant prompt; configure the authenticated tool URL; inspect a real Vapi event.
4. Run a real call against the configured assistant and inspect the webhook payload, transcript shape, confirmation, retry behavior, and write result.
5. Keep backend/tunnel live for review, test two real calls and restart persistence, and add actual number/API URL to README.

## Open issues / changes

- Live-call blocker: no Vapi account, number, credits, or provider credentials supplied in the workspace.
- Public URL blocker: no tunnel/domain is running; a Quick Tunnel URL is temporary and the local machine must remain online.
- Financial limit: Vapi's free number still consumes call credits; after trial credits, live calls require payment. See `docs/PIPELINE_REPORT.md`.
- Simulation blocker: the current scripted browser flow is not the intended agent simulation. Do not mark the project complete until it is redesigned and verified against the intended voice-agent path.
- Voice webhook now validates required fields, verifies a matching readback and affirmative caller reply in the supplied conversation, links one patient per call, and returns speakable tool errors. It cannot independently authenticate transcript contents beyond the bearer-authenticated Vapi delivery; a live call remains the integration gate.
- 2026-10-11: Moved the voice prompt to `app/prompts/patient_registration.md` using the owner's GRASP-Q definition: Goal, Role, Additional Context, Scenario, Purpose, Clarifying Questions. Added `app/prompts/vapi_tool_parameters.json` for Vapi's two Function tools. Lookup uses the provider's caller number plus last name and DOB, and rejects model-supplied numbers or patient IDs. Caller ID may be spoofed, so this is not strong identity proof and needs a real-call check with synthetic data.
- Vapi documentation shows both `function.arguments` and simplified `name`/`parameters` tool-call shapes; the webhook accepts both. Confirm the shape of a real event during live integration.
- Restart persistence of a retained patient has not yet been exercised as a separate integration test or real process restart. Do this before the live demo.
