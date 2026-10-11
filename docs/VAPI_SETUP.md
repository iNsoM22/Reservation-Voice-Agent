# Vapi live-call setup

The backend is ready for authenticated `tool-calls` and `end-of-call-report`
webhooks. A Vapi account, public HTTPS URL, assistant, and dialable U.S. number
must be configured in the provider dashboard to make real calls.

1. Set a strong `VAPI_WEBHOOK_TOKEN` in `.env` and start the app. Expose port
   8000 with HTTPS (for example, a temporary Cloudflare tunnel).
2. Create a Vapi bearer credential with exactly that token. Keep the bearer
   prefix enabled. Use a saved assistant or saved tool server URL; Vapi may
   withhold credentials for URLs supplied only in a transient API request.
3. Create Function tools named `register_patient` and `lookup_patient`. Set each
   server URL to `https://YOUR-HOST/calls/vapi` and attach the bearer credential.
   Copy each tool's `function.parameters` from
   `app/prompts/vapi_tool_parameters.json`. The lookup schema intentionally has
   no phone number or patient ID field; the server reads the provider's caller
   number and requires matching last name and date of birth.
4. Create a saved assistant with the system message in
   `app/prompts/patient_registration.md` and attach both Function tools. Set
   the assistant server URL to the same webhook,
   attach the same credential, and enable `end-of-call-report` events. Choose
   the available transcriber, model, and voice in your account.
5. Assign the assistant to a Vapi inbound U.S. number. Call it with synthetic
   data. Check the call's webhook log for a 200 response with a flat-string
   `result` for the matching `toolCallId`. Query `/patients` with `X-API-Key`
   and verify the call in `/dashboard/calls`.
6. Make a second call, restart the API, and query again to verify persistence.
   Try a correction, invalid DOB, rejected confirmation, and repeat delivery.
   Record the actual number, public URL, and provider selections in README.

For the dashboard browser voice test, create a **public** Vapi key restricted to
the dashboard origin and the same saved assistant. Set `VAPI_PUBLIC_KEY` and
`VAPI_ASSISTANT_ID` in `.env`, restart the app, and open `/dashboard/simulation`
as an admin. Allow microphone access and start the widget's voice session.
It uses Vapi's configured LLM, transcriber, voice, Function tools, webhook,
and call reports without dialing a number. The app's webhook still needs a
public HTTPS URL reachable by Vapi. Check the patient and call-log dashboards
after confirming a synthetic registration. Existing-record lookup remains
unavailable in a web call because it has no trusted inbound caller number.

The registration webhook requires the Vapi event's `call.id`. When conversation
`artifact.messages` are present, it verifies the assistant's final readback
question, an immediate clear user confirmation, and the spoken name and sex.
Vapi may send an empty message artifact with a tool call; then the published
assistant prompt is responsible for waiting for spoken confirmation before
invoking the tool. Update that prompt when deploying this fix. Check the actual
tool payload and live audio path in Vapi Logs → Webhooks after a real call.
Caller ID can be absent or spoofed. Lookup denies absent caller ID and requires
last name and DOB as additional checks. It also denies web and outbound calls,
where the customer number can be supplied by a client. Use synthetic data only.

See [Vapi Function tools](https://docs.vapi.ai/tools/custom-tools) and
[server authentication](https://docs.vapi.ai/server-url/server-authentication).
