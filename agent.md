# Agent instructions for this project

## Scope and source of truth

- Read `../Context/voice_ai_agent_coding_challenge.md`, `docs/IMPLEMENTATION_PLAN.md`, `NOTES.md`, `pyproject.toml`, and relevant implementation files before changes.
- This is a patient registration voice agent. The folder/package's `reservation` name is historical; use patient-registration terminology in new product code and docs.
- Keep the project clean and every source/test file below 600 lines.
- Use `app/validations/` for Pydantic request and response DTOs, `app/models/` for SQLAlchemy tables, `app/routes/` for HTTP endpoints, `app/services/` for business logic, and `app/config/settings.py` for Starlette-compatible settings. Put pytest tests under `test/`, grouped by the matching component.
- Use Ruff for formatting and linting; run `uv run ruff format --check .`, `uv run ruff check .`, and `uv run pytest` before completing code changes.

## Workflow

1. **Plan:** Map the requested behavior to challenge requirements and identify affected components and acceptance checks.
2. **Validate:** Check the plan against the challenge, existing code, and current vendor documentation. Record material decisions or blockers in `NOTES.md`.
3. **Implement with TDD:** Follow the test-driven-development skill for every feature, bug fix, and behavior change: write one behavioral test, run it and observe the expected failure, write minimal production code, run all relevant tests, then refactor with tests green. Read that skill's `writing-good-tests.md` guidance when writing tests.
4. Verify the integrated phone-to-database-to-API path before declaring completion. Update README and `NOTES.md` with actual status, commands, live endpoints, and limitations.

## Architecture constraints

- Keep telephony/LLM configuration, webhook transport, validation, patient service, and persistence clearly separated.
- REST and voice paths must share the same validation and patient service.
- Save only after explicit spoken confirmation. Return field-specific validation errors and speakable database failure results.
- Use a persistent database for the live system, UTC timestamps, UUID patient IDs, and soft deletes.
- Authenticate Vapi callbacks and protect patient API access. Never commit credentials or real patient data; use synthetic fixtures.
- The authenticated admin dashboard uses server-rendered Jinja templates in `app/templates/` and browser assets in `app/static/` (including `scripts/` for admin bootstrap utilities).
- Dashboard and browser-simulation bonuses were explicitly requested by the project owner; implement those alongside the core API while preserving the patient service as the shared persistence path.
- Prefer the simplest dependency and structure that meets the challenge. Keep owner-requested bonus work scoped and maintain TDD, Ruff, and the 600-line limit.
