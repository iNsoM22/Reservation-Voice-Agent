"""Only the Vapi event fields used by the current webhook stub."""

from typing import Any, Self

from pydantic import BaseModel, Field, model_validator


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


class VapiEvent(BaseModel):
    message: VapiMessage
