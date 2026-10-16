"""Shared demo profile and saved address contracts."""

from pydantic import BaseModel, ConfigDict, Field


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=40)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class AddressInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str = Field(min_length=1, max_length=60)
    line1: str = Field(min_length=1, max_length=180)
    line2: str = Field(default="", max_length=180)
    city: str = Field(min_length=1, max_length=100)
    region: str = Field(min_length=1, max_length=100)
    postalCode: str = Field(min_length=1, max_length=20)
    country: str = Field(min_length=1, max_length=80)
