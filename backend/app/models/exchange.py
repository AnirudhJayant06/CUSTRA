"""Validated application payload carried in A2A data parts."""

from typing import Any, Literal
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class ExchangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    case_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    action: Literal["start", "answer", "listSlots", "book"]
    stage: str = Field(min_length=1)
    data: dict[str, Any]
    context_id: str | None = None


class AppointmentSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    start: AwareDatetime
    end: AwareDatetime
    timezone: Literal["Asia/Kolkata"]
    simulated: Literal[True]

    @model_validator(mode="after")
    def validate_interval(self):
        if self.end <= self.start:
            raise ValueError("Appointment must end after it starts")
        return self


class Appointment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slotId: str
    start: AwareDatetime
    end: AwareDatetime
    timezone: Literal["Asia/Kolkata"]
    bookingReference: str = Field(min_length=1)
    simulated: Literal[True]


class ExchangeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_code: str | None = None
    requested_fields: list[str] = Field(default_factory=list)
    display_text: str = Field(min_length=1)
    next_stage: str = Field(min_length=1)
    reference: str | None = None
    slots: list[AppointmentSlot] = Field(default_factory=list, max_length=12)
    appointment: Appointment | None = None
    context_id: str | None = None
    task_id: str | None = None
    message_id: str | None = None


class ValidatedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=500)
    field_refs: list[str] = Field(min_length=1, max_length=4)
