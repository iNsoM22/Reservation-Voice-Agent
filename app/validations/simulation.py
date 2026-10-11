"""Browser simulation request fields."""

from pydantic import BaseModel, Field


class SimulationNumber(BaseModel):
    phone_number: str = Field(max_length=32)
    csrf_token: str = Field(max_length=256)
