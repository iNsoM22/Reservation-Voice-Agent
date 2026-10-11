"""Vapi webhook event fields used by registration, lookup, and call reports."""

import json
from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator


class ToolFunction(BaseModel):
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    id: str = Field(min_length=1)
    function: ToolFunction | None = None
    name: str | None = None
    parameters: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_tool_name(self) -> Self:
        if self.function is None and not self.name:
            raise ValueError("Tool name is required")
        return self

    @property
    def tool_name(self) -> str:
        return self.function.name if self.function else self.name or ""

    @property
    def arguments(self) -> dict[str, Any]:
        return self.function.arguments if self.function else self.parameters or {}


class VapiMessage(BaseModel):
    type: str = Field(min_length=1)
    tool_call_list: list[ToolCall] = Field(default_factory=list, alias="toolCallList")
    call: "CallReportCall | None" = None
    ended_reason: str | None = Field(default=None, alias="endedReason", max_length=100)
    artifact: "CallReportArtifact | None" = None

    @model_validator(mode="after")
    def require_report_call(self) -> Self:
        if self.type == "end-of-call-report" and self.call is None:
            raise ValueError("Call details are required for end-of-call reports")
        return self


class VapiEvent(BaseModel):
    message: VapiMessage


class CallParty(BaseModel):
    number: str | None = Field(default=None, max_length=100)


class CallReportCall(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    type: str | None = None
    started_at: datetime | None = Field(default=None, alias="startedAt")
    ended_at: datetime | None = Field(default=None, alias="endedAt")
    customer: CallParty = Field(default_factory=CallParty)
    phone_number: CallParty = Field(default_factory=CallParty, alias="phoneNumber")
    assistant_overrides: dict[str, Any] = Field(
        default_factory=dict, alias="assistantOverrides"
    )

    @field_validator("started_at", "ended_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Call timestamps must include a timezone")
        return value


class CallReportArtifact(BaseModel):
    transcript: str = Field(default="", max_length=200_000)
    messages: list[dict[str, Any]] = Field(default_factory=list, max_length=2_000)

    @field_validator("messages")
    @classmethod
    def bound_message_size(cls, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(json.dumps(messages, ensure_ascii=False).encode()) > 1_000_000:
            raise ValueError("Conversation messages are too large")
        return messages
