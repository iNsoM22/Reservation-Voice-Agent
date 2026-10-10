# Project notes

## Current state

- 2026-10-10: Reviewed `../Context/voice_ai_agent_coding_challenge.md` and the UV starter project.
- Planning complete in `docs/IMPLEMENTATION_PLAN.md`; application implementation has not started.
- Current project has `pyproject.toml` and starter `main.py`. README, lockfile, tests, live phone number, and deployment are still pending.

## Decisions

- Target stack: Vapi + FastAPI/Pydantic + SQLAlchemy + PostgreSQL + Railway, managed with uv. Use Ruff and pytest.
- Layout: `app/{validations,models,routes,services,config}` and mirrored `test/` packages.
- One patient service serves REST routes and the Vapi tool webhook.
- Write tests first for every behavior; observe a meaningful failure before implementing.
- Keep all source and test files under 600 lines.

## Next actions

1. Confirm Vapi number/tool access and hosting credentials are available.
2. Define API and webhook examples, then write failing tests for validation and CRUD.
3. Implement the core service and webhook through red-green-refactor cycles.
4. Deploy and verify two calls plus persistence after restart; document actual URLs and limitations in README.

## Open issues / changes

- None recorded yet. Add dated entries here as work proceeds.
