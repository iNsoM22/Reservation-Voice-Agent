# Voice pipeline and cost report

## TL;DR

For a no-upfront-payment assessment demo, use **Vapi free inbound U.S. number + trial credits**, this **FastAPI service**, **local SQLite**, and a **Cloudflare Quick Tunnel**. Vapi handles the speech and LLM parts; the app validates and stores patients. This is temporary: the number is free but calls consume credits, and the tunnel works only while the local computer stays online. A guaranteed, indefinitely free, publicly callable U.S. phone system is **not established** by the available plans.

## Pipeline

| Step | Owner now | Contract / check |
| --- | --- | --- |
| Public inbound number | Vapi free U.S. inbound number | Provision and assign to an assistant; call it from a real phone. The number supports inbound calls only. |
| Speech in / speech out / LLM | Vapi assistant's configured providers | Prompt for required fields, handle corrections, read back every field, obtain explicit confirmation. Exact provider choices and costs must be checked in the Vapi dashboard. |
| Tool handoff | `POST /calls/vapi` | Vapi posts `message.type = "tool-calls"` with `toolCallList`; app authenticates bearer token and returns one flat-string `error`/`result` per `toolCallId`. The adapter accepts both documented tool-call shapes. Current service is an intentional error stub. |
| Validation and persistence | FastAPI DTOs, `PatientService`, SQLite | Same service powers REST and future voice path. SQLite file survives process restarts on this computer. |
| External access | Cloudflare Quick Tunnel | Expose local port 8000 for a controlled review window; update Vapi tool URL whenever the tunnel URL changes. |
| Verification | pytest, Ruff, real call | Test REST independently, then tool contract, then one call plus readback/query/restart/call-back before submission. |

## Cost and alternative choices

- [Vapi says one free U.S. inbound number is available](https://docs.vapi.ai/free-telephony), while calls still consume credits. Its [published usage-only plan](https://vapi.ai/pricing) currently includes $5 introductory credits; this is a **trial budget**, not a permanent free tier for calls. Vapi notes that its dashboard may require a payment method for number creation, so verify account eligibility. [Credits at zero freeze billable usage](https://docs.vapi.ai/billing/manage-billing-and-credits).
- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) provide a temporary public URL without an account or domain, but have no uptime guarantee and change hostname on restart. Use them for development or a scheduled review, not unattended hosting.
- [Supabase Free Postgres](https://supabase.com/docs/guides/platform/free-project-pausing) can separate database persistence from the laptop, but inactive free projects can pause after seven days. It does not host this FastAPI server.
- [Twilio trial](https://www.twilio.com/docs/usage/trials) is an alternative number trial, but adds telephony integration work. A production U.S. number and calls have [ongoing prices](https://www.twilio.com/en-us/voice/pricing/us). It does not make an all-free live service.
- A fully local speech/LLM stack such as [Ollama](https://ollama.com/) can avoid hosted model fees, but it still needs a carrier or trial number and custom real-time audio integration. That route is larger than this challenge's three-hour scope.

## Integration gates and blockers

1. **Backend gate:** REST create, get/list/filter, update, delete, validation errors, and database failure responses are tested with synthetic records. Verify a retained patient across an actual process restart before the live demo.
2. **Voice gate:** Create/publish the Vapi assistant and prompt, configure the tool URL and bearer credential, verify the real event body, implement confirmation-aware and retry-safe registration, then replace the call stub. A tool argument saying `confirmed=true` alone is not independent proof of spoken consent; preserve an auditable call state or transcript before writing.
3. **Demo gate:** Provision a real number, verify available credits and allowed caller access, keep API+tunnel running, make two calls, then put actual number and URL in README.
4. **Known blocker:** No Vapi account, number, credits, hosted URL, or provider credentials are available in this workspace. Therefore the live-call requirement cannot yet be validated.

Vapi documents the full `function.arguments` tool-call form in its [custom tools guide](https://docs.vapi.ai/tools/custom-tools) and a simplified `name`/`parameters` form in its [server events guide](https://docs.vapi.ai/server-url/events). The adapter accepts both, but a real webhook capture remains the integration gate.
