"""Short complaint intake and durable case shape."""

from datetime import date
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ComplaintInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    productId: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    addressId: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    issueSummary: str = Field(default="", max_length=120)
    description: str = Field(min_length=1, max_length=2000)

    preferredDate: date | None = None
    preferredSlotId: str | None = Field(default=None, max_length=100)

    @model_validator(mode='after')
    def summary_and_preference(self):
        if not self.issueSummary:
            self.issueSummary = self.description[:120]
        if bool(self.preferredDate) != bool(self.preferredSlotId):
            raise ValueError('Choose both a preferred date and time, or leave both blank')
        return self
