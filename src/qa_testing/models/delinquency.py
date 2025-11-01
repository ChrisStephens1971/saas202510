"""Delinquency models for testing delinquency scenarios."""

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base import AccountingDate, BaseTestModel, MoneyAmount


class Delinquency(BaseTestModel):
    """
    Delinquency record for member with outstanding balance.

    Represents a simplified delinquency scenario for testing purposes.
    Used by DelinquencyGenerator to create test data for delinquency workflows.
    """

    member_id: UUID = Field(
        description="Member with delinquent balance"
    )

    days_delinquent: int = Field(
        description="Number of days account is past due",
        ge=0,
    )

    total_amount_due: MoneyAmount = Field(
        description="Total amount currently due"
    )

    status: str = Field(
        description="Delinquency status (CURRENT, LATE_30, LATE_60, LATE_90, etc.)"
    )

    due_date: Optional[AccountingDate] = Field(
        default=None,
        description="Original due date"
    )

    last_payment_date: Optional[AccountingDate] = Field(
        default=None,
        description="Date of last payment received"
    )
