"""Bounded contracts shared by model roles, ingestion and conversation."""
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

PRODUCT_FIELDS = frozenset({
    'product.brand', 'product.model', 'product.serialNumber', 'product.purchaseDate',
    'product.invoiceNumber', 'product.seller', 'product.sellerBranch',
    'product.warrantyMonths', 'product.warrantyExpiry',
})
CONTEXT_FIELDS = frozenset({'profile.name', 'profile.phone', 'profile.email',
    'address.line1', 'address.line2', 'address.city', 'address.region', 'address.country', 'address.postal_code', 'issue.summary', 'issue.description',
    'appointment.preference'})

def is_product_field(field):
    return field in PRODUCT_FIELDS or bool(re.fullmatch(r'product\.details\.[a-z][a-z0-9_]{0,39}', field))


def is_fact_field(field):
    return is_product_field(field) or field in CONTEXT_FIELDS


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid')

class ExtractedFact(Contract):
    field: str = Field(max_length=80)
    value: str = Field(min_length=1, max_length=500)
    quote: str = Field(min_length=1, max_length=1200)
    page: int = Field(default=1, ge=1, le=1000)
    uncertain: bool = False

class Passage(Contract):
    text: str = Field(min_length=1, max_length=2000)
    page: int = Field(default=1, ge=1, le=1000)

class Extraction(Contract):
    document_type: Literal['invoice', 'warranty', 'serial_label', 'product_photo', 'unrelated', 'unknown']
    description: str = Field(max_length=600)
    product_match: bool
    complete_for_product: bool = False
    facts: list[ExtractedFact] = Field(default_factory=list, max_length=24)
    passages: list[Passage] = Field(default_factory=list, max_length=24)

class Resolution(Contract):
    standalone_question: str = Field(min_length=1, max_length=2000)
    requested_facts: list[str] = Field(default_factory=list, max_length=8)
    needs_clarification: bool = False
    clarification: str = Field(default='', max_length=500)
    requires_document: bool = False
    document_type: Literal['invoice', 'warranty', 'serial_label', 'unknown'] = 'unknown'

class GroundedAnswer(Contract):
    text: str = Field(min_length=1, max_length=1800)
    citations: list[str] = Field(default_factory=list, max_length=12)
    values: dict[str, str] = Field(default_factory=dict)
    missing: bool = False
