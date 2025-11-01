"""Invoice models for testing invoicing functionality."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base import AccountingDate, BaseTestModel, MoneyAmount


class Invoice(BaseTestModel):
    """
    Invoice for member charges.

    Represents an invoice for various charges (late fees, assessments, violations, etc.).
    Used by InvoiceGenerator to create test data for invoicing workflows.
    """

    member_id: UUID = Field(
        description="Member receiving the invoice"
    )

    invoice_type: str = Field(
        description="Type of invoice (LATE_FEE, ASSESSMENT, VIOLATION_FINE, etc.)"
    )

    amount: MoneyAmount = Field(
        gt=Decimal("0.00"),
        description="Invoice amount"
    )

    description: str = Field(
        description="Invoice description"
    )

    due_date: AccountingDate = Field(
        description="Payment due date"
    )

    invoice_date: AccountingDate = Field(
        default_factory=date.today,
        description="Date invoice was created"
    )

    paid: bool = Field(
        default=False,
        description="Whether invoice has been paid"
    )

    paid_date: Optional[AccountingDate] = Field(
        default=None,
        description="Date invoice was paid (if applicable)"
    )

    reference_id: Optional[UUID] = Field(
        default=None,
        description="Reference to related entity (violation, assessment, etc.)"
    )
