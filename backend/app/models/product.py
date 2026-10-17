"""Backward-compatible manual product identity and recorded warranty inputs."""
from datetime import date
from pydantic import BaseModel, ConfigDict, Field


class ProductInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    categoryId: str = Field(min_length=1)
    brandId: str = Field(min_length=1)
    displayName: str = Field(default='', max_length=120)
    nickname: str | None = Field(default=None, max_length=120)
    modelNumber: str | None = Field(default=None, max_length=120)
    purchaseDate: date | None = None
    warrantyMonths: int | None = Field(default=None, strict=True, ge=1, le=120)
    warrantyExpiry: date | None = None
