# Patient Registration Voice Agent: implementation plan

Source: `../../Context/voice_ai_agent_coding_challenge.md`. This document records the intended design and current delivery status. The project is a patient registration system despite the existing folder name.

## TL;DR

The delivered stack uses **Vapi** for the configured voice assistant, speech, and phone calls; **Heroku** for the FastAPI API and webhook; **SQLAlchemy** with a configured database for persistence; and **uv + pytest + Ruff** for development. Local development defaults to SQLite. See `PIPELINE_REPORT.md` for deployment trade-offs and cost notes.

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
| Admin access and bootstrap | Dashboard auth routes, user model, `scripts/create_admin.py` | Delivered: bootstrap the initial administrator from environment settings and protect dashboard pages with signed sessions and CSRF checks. |
| Patient dashboard | Jinja templates and static assets | Delivered: authenticated patient list/detail pages and call-log list/detail pages. Templates live in `app/templates/`; browser styles and behavior live in `app/static/`. |
| Browser simulation | Authenticated dashboard page and Vapi Web SDK | Delivered: browser microphone/audio uses the same saved assistant, tools, webhook, validation, persistence, and reports as phone calls. A signed test caller number enables registration and lookup against matching synthetic records. Live provider verification remains. |
| Vapi registration and reports | Authenticated Vapi route, call service and call-log service | Delivered: validate a transcript-backed confirmation, write through `PatientService`, link the call, handle retries, and persist `end-of-call-report` data. Live provider validation is still pending. |
| Returning caller | Caller-bound `lookup_patient` tool | Lookup uses the provider caller number or signed simulation number plus matching last name and DOB; tool arguments cannot select another number or patient ID. |
| Deployment and visibility | Heroku API, Vapi settings, dashboard | Heroku serves the HTTPS API and webhook. The authenticated dashboard shows patients and call details, including transcripts and reports when supplied by Vapi. Use a persistent database URL for deployed records. |

## Request flow

1. Caller dials Vapi number; assistant gathers information conversationally.
2. Assistant repeats every collected field and obtains an explicit yes or corrections.
3. Assistant invokes `register_patient` only after confirmation.
4. FastAPI webhook authenticates Vapi, validates the tool payload, and calls `PatientService`.
5. Service writes to the configured database. Webhook returns a Vapi tool result; assistant speaks success or failure and ends gracefully.
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
    prompts/patient_registration.md
    prompts/vapi_tool_parameters.json
  test/
    validations/test_patient.py
    models/test_patient.py
    routes/test_patients.py
    routes/test_vapi.py
    services/test_patients.py
  docs/
    IMPLEMENTATION_PLAN.md
```

Split any module as its responsibilities grow. Every source and test file must remain under 600 lines. The dashboard, browser voice page, and call-log visibility were explicitly requested by the project owner and are delivered; live provider verification remains.

## Delivery order and validation gates

1. **Review:** Re-read challenge, `pyproject.toml`, repository guidance, and relevant vendor docs. Record any changed assumptions in `NOTES.md`.
2. **Plan:** Fix API contracts, schemas, state normalization, Vapi tool shape, hosting, and acceptance cases before writing production code.
3. **Validate plan:** Check every mandatory challenge row against the feature map above; verify number availability, Vapi webhook response format, Heroku persistence, and reviewer access. Resolve gaps before coding.
4. **TDD: data/API:** For each behavior, write a failing test, observe the expected failure, implement the minimum, rerun, and refactor. Cover validation boundaries, filters, partial update, soft delete, envelopes, restart persistence, and write failures.
5. **Delivered TDD: Vapi registration:** Contract tests cover confirmed registration, retry idempotency, invalid and unconfirmed data, and report linking. Validate the actual provider payload in a live call before review.
6. **Pending end-to-end evidence:** Verify a real Vapi call against the deployed Heroku endpoint, query the patient, restart the API, repeat the query, then test correction and invalid data. Add the actual live URL, number, and provider selections to README when available.

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
- [Heroku Postgres](https://devcenter.heroku.com/articles/heroku-postgresql)

