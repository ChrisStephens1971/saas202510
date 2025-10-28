"""Base types and utilities for test data models."""

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


def money_amount(value: str | float | Decimal) -> Decimal:
    """
    Convert to NUMERIC(15, 2) - exact precision for money.

    CRITICAL: Always use Decimal with exactly 2 decimal places.
    Never use float for money calculations!
    """
    if isinstance(value, str):
        d = Decimal(value)
    elif isinstance(value, float):
        # Allow float input but convert to string first to avoid precision issues
        d = Decimal(str(value))
    else:
        d = value

    # Quantize to exactly 2 decimal places
    return d.quantize(Decimal("0.01"))


# Type alias for money amounts (NUMERIC(15, 2))
MoneyAmount = Annotated[
    Decimal,
    Field(
        description="Money amount with exactly 2 decimal places (NUMERIC(15,2))",
        max_digits=15,
        decimal_places=2,
    ),
]

# Type alias for accounting dates (DATE, not datetime)
AccountingDate = Annotated[
    date,
    Field(description="Accounting date (DATE type, not datetime)"),
]


class BaseTestModel(BaseModel):
    """Base model for all test data models."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    tenant_id: UUID = Field(description="Tenant ID for multi-tenant isolation")
    created_at: AccountingDate = Field(
        default_factory=date.today,
        description="Creation date"
    )

    class Config:
        """Pydantic config."""
        json_encoders = {
            Decimal: str,  # Serialize Decimal as string to preserve precision
            date: lambda v: v.isoformat(),
        }
        arbitrary_types_allowed = True

    @field_validator("*", mode="before")
    @classmethod
    def validate_money_fields(cls, v, info):
        """Convert money fields to proper Decimal type."""
        field_name = info.field_name
        if field_name and "amount" in field_name.lower():
            if isinstance(v, (str, float, int)):
                return money_amount(v)
        return v
