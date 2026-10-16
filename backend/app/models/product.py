"""Manual product entry; no extraction or serial number requirement."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ProductInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    categoryId: str = Field(min_length=1)
    brandId: str = Field(min_length=1)
    displayName: str = Field(min_length=1, max_length=120)
    purchaseDate: date | None = None
    warrantyExpiry: date | None = None
