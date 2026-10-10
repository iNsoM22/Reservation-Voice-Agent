"""Authenticated Vapi server URL endpoint with inert registration behavior."""

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
    service = CallService()
    return {
        "results": [
            {
                "toolCallId": call.id,
                "error": (
                    service.register_patient(call.arguments)
                    if call.tool_name == "register_patient"
                    else f"Unsupported tool: {call.tool_name}"
                ),
            }
            for call in event.message.tool_call_list
        ]
    }
