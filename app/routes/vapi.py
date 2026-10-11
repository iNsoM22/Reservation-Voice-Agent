"""Authenticated Vapi server URL endpoint."""

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.routes.errors import APIError
from app.services.call_logs import CallLogService
from app.services.calls import CallService
from app.validations.vapi import VapiEvent

router = APIRouter()


@router.post("/calls/vapi")
def vapi_webhook(
    request: Request,
    event: VapiEvent,
) -> dict[str, object]:
    if event.message.type == "end-of-call-report":
        report = event.message.model_dump(by_alias=True, exclude_none=True)
        with Session(request.app.state.engine) as session:
            CallLogService(session).record_vapi_report(report)
        return {}
    if event.message.type != "tool-calls":
        return {}
    if not event.message.tool_call_list:
        raise APIError(422, "invalid_event", "Tool call list is required")
    with Session(request.app.state.engine) as session:
        service = CallService(session)
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
                        )
                        if call.tool_name == "register_patient"
                        else service.lookup_patient(
                            event.message.call.customer.number
                            if event.message.call
                            else None,
                            call.arguments,
                            call_type=event.message.call.type
                            if event.message.call
                            else None,
                        )
                        if call.tool_name == "lookup_patient"
                        else {"error": f"Unsupported tool: {call.tool_name}"}
                    ),
                }
                for call in event.message.tool_call_list
            ]
        }
