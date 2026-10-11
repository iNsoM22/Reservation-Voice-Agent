# Vapi configuration and verification

The backend accepts authenticated `tool-calls` and `end-of-call-report`
webhooks. The assistant is configured in Vapi and the app is deployed on Heroku.
Use this checklist when checking or changing that configuration.

1. Set a strong `VAPI_WEBHOOK_TOKEN` as a Heroku config var. Use the deployed
   HTTPS URL for the webhook; use `.env` and localhost only for local development.
2. Create a Vapi bearer credential with exactly that token. Keep the bearer
   prefix enabled. Use a saved assistant or saved tool server URL; Vapi may
   withhold credentials for URLs supplied only in a transient API request.
3. Create Function tools named `register_patient` and `lookup_patient`. Set each
   server URL to `https://YOUR-HOST/calls/vapi` and attach the bearer credential.
   Copy each tool's `function.parameters` from
   `app/prompts/vapi_tool_parameters.json`. The lookup schema intentionally has
   no phone number or patient ID field; the server uses the inbound caller
   number or signed simulation number and requires matching last name and DOB.
4. Create a saved assistant with the system message in
   `app/prompts/patient_registration.md` and attach both Function tools. Set
   the assistant server URL to the same webhook,
   attach the same credential, and enable `end-of-call-report` events. Choose
   the available transcriber, model, and voice in your account.
5. Confirm the assistant is assigned to a Vapi inbound U.S. number. Call it with synthetic
   data. Check the call's webhook log for a 200 response with a flat-string
   `result` for the matching `toolCallId`. Query `/patients` with `X-API-Key`
   and verify the call in `/dashboard/calls`.
6. Make a second call, restart the API, and query again to verify persistence.
   Try a correction, invalid DOB, rejected confirmation, and repeat delivery.
   Record the actual number, public URL, and provider selections in README
   when those details are available to share.

For the dashboard browser voice test, use a **public** Vapi key restricted to
the dashboard origin and the same saved assistant. Set `VAPI_PUBLIC_KEY` and
`VAPI_ASSISTANT_ID` as Heroku config vars, then open `/dashboard/simulation`
as an admin. Enter a 10-digit test caller number, select Start voice test, and
allow microphone access. The browser uses Vapi's Web SDK to start the saved
assistant ID with the signed number in `assistantOverrides.variableValues`.
It uses Vapi's configured LLM, transcriber, voice, Function tools, webhook,
and call reports without dialing a number. The app's webhook still needs a
public HTTPS URL reachable by Vapi. Check the patient and call-log dashboards
after confirming a synthetic registration. For lookup, use a test number that
matches an existing patient's stored number, then give the matching last name
and DOB. The server verifies the signed simulation number; the model never
supplies a lookup number. The revised prompt must also be published in Vapi.

The registration webhook requires the Vapi event's `call.id`. When conversation
`artifact.messages` are present, it verifies the assistant's final readback
question, an immediate clear user confirmation, and the spoken name and sex.
Vapi may send an empty message artifact with a tool call; then the published
assistant prompt is responsible for waiting for spoken confirmation before
invoking the tool. Update that prompt when deploying this fix. Check the actual
tool payload and live audio path in Vapi Logs → Webhooks after a real call.
Caller ID can be absent or spoofed. Inbound lookup denies absent caller ID and
requires last name and DOB as additional checks. Browser lookup requires the
one-hour signed simulation number; outbound calls cannot use lookup. Use
synthetic data only.

See [Vapi Function tools](https://docs.vapi.ai/tools/custom-tools) and
[server authentication](https://docs.vapi.ai/server-url/server-authentication).
