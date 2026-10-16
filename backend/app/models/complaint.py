"""Short complaint intake and durable case shape."""

from pydantic import BaseModel, ConfigDict, Field


class ComplaintInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    productId: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    addressId: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    issueSummary: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
