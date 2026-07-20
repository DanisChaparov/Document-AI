"""Pydantic models for extracted document data."""
from decimal import Decimal

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    name: str
    quantity: Decimal | None = None
    unit: str | None = None  # шт, кг, услуга...
    price: Decimal | None = None
    total: Decimal


class Invoice(BaseModel):
    doc_type: str  # "счёт-фактура" | "накладная" | "акт" | "чек" | "unknown"
    doc_number: str | None = None
    doc_date: str | None = None  # ISO 8601 (YYYY-MM-DD)
    supplier_name: str = ""
    supplier_bin: str | None = None  # БИН/ИИН, 12 digits
    buyer_name: str | None = None
    buyer_bin: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: Decimal | None = None
    vat_amount: Decimal | None = None  # НДС
    total: Decimal = Decimal(0)
    currency: str = "KZT"
    confidence: dict[str, float] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    field: str
    message: str
    severity: str = "warning"  # "warning" | "error"


class ExtractionResult(BaseModel):
    invoice: Invoice
    issues: list[ValidationIssue] = Field(default_factory=list)
    model_used: str = ""
    latency_ms: int = 0
