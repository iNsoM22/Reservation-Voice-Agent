# Project notes

## Current state (2026-10-12)

- Browser simulation now starts the saved assistant through Vapi's Web SDK with
  the signed number in `assistantOverrides.variableValues`. The widget embed
  wrapped the saved assistant ID and overrides inside an `assistant` object;
  Vapi rejected that call as a transient assistant for the restricted public
  key. The page has explicit start/end controls and a way to change the test
  number. Verify the actual call payload and audio flow after deployment.
- The owner reports that the app is deployed on Heroku and the assistant is
  configured in Vapi. This workspace does not contain the live app URL, phone
  number, Vapi provider selections, or deployed config values, so those details
  cannot be independently verified here.
- The root `Procfile` starts Uvicorn on Heroku's `$PORT`. The app accepts
  Heroku-style PostgreSQL URLs and creates patient, user, and call tables on
  startup. Local development defaults to SQLite. Schema migrations are not yet
  implemented.
- REST patient CRUD, Vapi registration and lookup tools, and end-of-call report
  handling are implemented. REST and Vapi share patient validation and service
  logic. The Vapi webhook uses a bearer token; patient REST routes use an API
  key.
- The administrator dashboard has patient list/detail, call list/detail, and
  browser simulation pages. Call details show transcripts and report data when
  received. Authentication uses signed sessions; state-changing dashboard
  requests use CSRF tokens.
- Browser simulation uses the saved Vapi assistant. The page accepts a 10-digit
  test caller number and sends a one-hour signed token with the web call.
  Registration must use the confirmed matching number. Lookup uses the signed
  number plus last name and DOB; inbound calls use provider caller ID instead.
  Old simulation records are findable only when their stored phone number,
  last name, and DOB match.
- The repository prompt now permits browser lookup. It must be published in
  Vapi for the live assistant to use it; the published prompt is not visible
  from this workspace.

## Verification and limits

- Repository tests cover the simulated caller number, registration, lookup,
  expiry, malformed overrides, reports, and inbound-call isolation. The last
  full test run before this documentation update passed 84 tests with Ruff
  checks passing. Live Vapi calls and deployed Heroku configuration have not
  been independently inspected in this workspace.
- When Vapi sends conversation messages, the webhook checks the final
  readback question, affirmative reply, and spoken name/sex. Vapi may send an
  empty message artifact; then the published prompt is the spoken-confirmation
  control. Verify the actual event in Vapi Logs and the call-detail page.
- The app creates tables at startup; add migrations before making long-lived
  schema changes. Use a persistent deployed database and verify records survive
  a dyno restart. Caller ID can be spoofed, so lookup is assessment-grade
  verification with synthetic data only.

## Next checks

1. Confirm Heroku `/health`, a running web dyno, and persistent `DATABASE_URL`.
2. Publish the current prompt and tool schemas in the saved Vapi assistant.
3. Make synthetic registration and returning-caller calls through the phone
   number and browser simulation. Review Vapi webhook logs, the patient page,
   and the call-detail page.
4. Record the shareable live URL, Vapi number, and model/voice/transcriber
   selections in README.
