# Patient Registration Voice Agent: implementation plan

Source: `../../Context/voice_ai_agent_coding_challenge.md`. This document is a plan, not an implementation. The project is a patient registration system despite the existing folder name.

## TL;DR

Use **Vapi** for the U.S. phone number, speech, and conversational LLM; **Python 3.12 + FastAPI + Pydantic** for the API and Vapi tool webhook; **SQLAlchemy + PostgreSQL** for validated persistent records; **Railway** for the API and database; **uv + pytest + Ruff + FastAPI TestClient** for development and tests. Keep one backend service and one database. Configure the assistant and number in Vapi. SQLite can serve local tests, but the live deployment should use persistent PostgreSQL.

## Components and feature map

| Requirement | Component | Build and verification |
| --- | --- | --- |
| Dialable U.S. number and natural speech | Vapi number and assistant | Assign an inbound number to the assistant. Select its LLM, STT, and TTS in Vapi. Place a real call and verify turn taking and interruptions. |
| Intake of required fields | Versioned assistant prompt and `PatientCreate` schema | Prompt for first/last name, DOB, sex, phone, address line 1, city, state, ZIP. Accept out-of-order information and ask only for missing fields. Test several spoken phrasings. |
| Optional fields | Prompt and schema | Offer email, address line 2, insurance, language, and emergency contact after required fields; skip declined fields. Keep `preferred_language` default English. |
| Corrections, validation, and confirmation | Prompt plus server-side Pydantic validators | Normalize spoken DOB and phone input. Reject future DOB, malformed phone/ZIP/state, invalid enum, and names outside the stated rules. Return field-specific errors to the assistant. Read back all collected values; call the save tool only after explicit confirmation. Test correction and invalid-input calls. |
| Save and graceful result | `register_patient` Vapi function tool, webhook adapter, patient service | Webhook validates the tool request, invokes the same service used by REST, and returns a Vapi result tied to `toolCallId`. Success includes patient ID; failure is a short speakable error. Avoid duplicate inserts on tool retries with a call/tool idempotency key. |
| Persistent patient model | PostgreSQL table and repository | UUID primary key; date, enum/check constraints, bounded text, UTC `created_at`/`updated_at`, nullable `deleted_at`. Validate in API and database where practical. Restart the app and verify the record remains. |
| REST CRUD | FastAPI routes and shared service | `GET /patients` with three optional filters, `GET /patients/{id}`, `POST /patients`, partial `PUT /patients/{id}`, and soft `DELETE /patients/{id}`. Hide deleted records from ordinary reads. Use the specified `{ "data": ..., "error": null }` envelope and consistent error envelope/status codes. |
| Returning caller | Optional lookup tool | After core path works, look up normalized phone, confirm identity before speaking or changing a matching record, and offer an update. This is a bonus, not a launch dependency. |
| Deployment and visibility | Railway API + Postgres, Vapi settings, README | Set `DATABASE_URL` and webhook secret through environment variables, deploy HTTPS API, configure Vapi tool URL, add live number/API URL to README, and place a second call. Log call ID, validation result, and write outcome; avoid full patient payloads in public logs. |

## Request flow

1. Caller dials Vapi number; assistant gathers information conversationally.
2. Assistant repeats every collected field and obtains an explicit yes or corrections.
3. Assistant invokes `register_patient` only after confirmation.
4. FastAPI webhook authenticates Vapi, validates the tool payload, and calls `PatientService`.
5. Service writes to PostgreSQL. Webhook returns a Vapi tool result; assistant speaks success or failure and ends gracefully.
6. REST routes use the same service and database. No second persistence path.

## Suggested project layout

```text
Reservation Voice Agent/
  agent.md
  NOTES.md
  README.md
  pyproject.toml
  uv.lock
  app/
    main.py
    config/settings.py
    validations/patient.py   # request and response DTOs
    models/patient.py        # SQLAlchemy table
    routes/patients.py
    routes/vapi.py
    services/patients.py
    prompt.md
  test/
    validations/test_patient.py
    models/test_patient.py
    routes/test_patients.py
    routes/test_vapi.py
    services/test_patients.py  docs/
    IMPLEMENTATION_PLAN.md
```

Split any module as its responsibilities grow. Every source and test file must remain under 600 lines. Do not add a dashboard, scheduling, transcript storage, or multilingual support until the core phone registration path works.

## Delivery order and validation gates

1. **Review:** Re-read challenge, `pyproject.toml`, repository guidance, and relevant vendor docs. Record any changed assumptions in `NOTES.md`.
2. **Plan:** Fix API contracts, schemas, state normalization, Vapi tool shape, hosting, and acceptance cases before writing production code.
3. **Validate plan:** Check every mandatory challenge row against the feature map above; verify number availability, Vapi webhook response format, Railway persistence, and how reviewer access will work. Resolve gaps before coding.
4. **TDD: data/API:** For each behavior, write a failing test, observe the expected failure, implement the minimum, rerun, and refactor. Cover validation boundaries, filters, partial update, soft delete, envelopes, restart persistence, and write failures.
5. **TDD: voice integration:** Write contract tests with representative Vapi tool events and failures before implementing the adapter. Confirm tool idempotency and that saving cannot happen before explicit confirmation at the assistant level.
6. **End-to-end:** Deploy, configure number and tool, complete one real call, query the patient, restart the API, repeat the query, then make a correction/invalid-data call. Complete README with actual live details and limitations.

## Decisions and limits to confirm during implementation

- Vapi manages the LLM, STT, and TTS selection; its exact model/voice configuration should be recorded in README after setup.
- A live service needs durable storage. SQLite is suitable for local tests; an ephemeral host filesystem would not satisfy the restart requirement.
- API endpoints expose demographic data. Add a simple API key for reviewer access and authenticate Vapi's webhook separately; document how reviewers obtain the key. Keep secrets out of git.
- The spec calls for final-payload logging, but these are patient-like demographics. Use synthetic test data and mask direct identifiers in ordinary logs; enable full payload logging only in a controlled demo if the reviewer explicitly requires it.
- Use UTC timestamps and store DOB as a date. Format DOB as `MM/DD/YYYY` at voice/API boundaries as required by the challenge.
- No production healthcare claim or real patient data; the challenge explicitly excludes HIPAA compliance.

## Reference documentation

- [Vapi phone quickstart](https://docs.vapi.ai/quickstart/phone)
- [Vapi custom tool contract](https://docs.vapi.ai/tools/custom-tools)
- [Vapi server URLs](https://docs.vapi.ai/server-url/)
- [FastAPI SQL database tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [Railway PostgreSQL](https://docs.railway.com/databases/postgresql)

