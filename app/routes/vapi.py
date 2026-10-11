"""Authenticated Vapi server URL endpoint."""

import re
import time

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.routes.dashboard_auth import _verified
from app.routes.errors import APIError
from app.services.call_logs import CallLogService
from app.services.calls import CallService
from app.validations.vapi import VapiEvent

router = APIRouter()


def _simulation_number(request: Request, call) -> str | None:
    if not call or call.type != "webCall":
        return None
    secret = request.app.state.settings.dashboard_session_secret
    variables = call.assistant_overrides.get("variableValues")
    if not secret or not isinstance(variables, dict):
        return None
    token = variables.get("simulationCallerToken")
    value = _verified(secret, token) if isinstance(token, str) else None
    if not value:
        return None
    number, _, expires = value.rpartition(":")
    if (
        re.fullmatch(r"\+1[0-9]{10}", number)
        and expires.isdigit()
        and int(expires) > time.time()
    ):
        return number
    return None


@router.post("/calls/vapi")
def vapi_webhook(
    request: Request,
    event: VapiEvent,
) -> dict[str, object]:
    if event.message.type == "end-of-call-report":
        report = event.message.model_dump(by_alias=True, exclude_none=True)
        number = _simulation_number(request, event.message.call)
        if number:
            report["call"]["customer"]["number"] = number
        with Session(request.app.state.engine) as session:
            CallLogService(session).record_vapi_report(report)
        return {}
    if event.message.type != "tool-calls":
        return {}
    if not event.message.tool_call_list:
        raise APIError(422, "invalid_event", "Tool call list is required")
    with Session(request.app.state.engine) as session:
        service = CallService(session)
        call_details = event.message.call
        simulated_number = _simulation_number(request, call_details)
        return {
            "results": [
                {
                    "toolCallId": call.id,
                    **(
                        service.register_patient(
                            event.message.call.id if event.message.call else None,
                            call.arguments,
                            event.message.artifact.messages
                            if event.message.artifact
                            else [],
                            caller_number=simulated_number,
                        )
                        if call.tool_name == "register_patient"
                        else service.lookup_patient(
                            simulated_number
                            or (call_details.customer.number if call_details else None),
                            call.arguments,
                            call_type="inboundPhoneCall"
                            if simulated_number
                            else (call_details.type if call_details else None),
                        )
                        if call.tool_name == "lookup_patient"
                        else {"error": f"Unsupported tool: {call.tool_name}"}
                    ),
                }
                for call in event.message.tool_call_list
            ]
        }
