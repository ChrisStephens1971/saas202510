"""Budget models for testing budget management functionality."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from .base import AccountingDate, BaseTestModel, MoneyAmount


class BudgetStatus(str, Enum):
    """Budget status choices."""

    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class Budget(BaseTestModel):
    """
    Annual operating budget for an HOA.

    Tracks budgeted amounts by account for fiscal planning and variance analysis.
    """

    name: str = Field(
        description="Budget name (e.g., 'FY 2025 Operating Budget')"
    )

    fiscal_year: int = Field(
        description="Fiscal year for this budget"
    )

    start_date: AccountingDate = Field(
        description="Budget period start date"
    )

    end_date: AccountingDate = Field(
        description="Budget period end date"
    )

    fund_id: Optional[UUID] = Field(
        default=None,
        description="Specific fund (null = all funds)"
    )

    status: BudgetStatus = Field(
        default=BudgetStatus.DRAFT,
        description="Budget status"
    )

    approved_by: Optional[UUID] = Field(
        default=None,
        description="User ID who approved the budget"
    )

    approved_at: Optional[AccountingDate] = Field(
        default=None,
        description="Date when budget was approved"
    )

    notes: str = Field(
        default="",
        description="Budget notes and assumptions"
    )

    created_by: Optional[UUID] = Field(
        default=None,
        description="User ID who created the budget"
    )

    @field_validator("end_date")
    @classmethod
    def validate_end_date_after_start(cls, v, info):
        """Ensure end_date is after start_date."""
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v

    @field_validator("fiscal_year")
    @classmethod
    def validate_fiscal_year(cls, v):
        """Ensure fiscal year is reasonable."""
        current_year = date.today().year
        if v < 2000 or v > current_year + 10:
            raise ValueError(f"fiscal_year must be between 2000 and {current_year + 10}")
        return v

    def get_total_budgeted(self, lines: List["BudgetLine"]) -> Decimal:
        """Calculate total budgeted amount across all lines."""
        return sum((line.budgeted_amount for line in lines), Decimal("0.00"))

    def is_active(self) -> bool:
        """Check if budget is currently active."""
        today = date.today()
        return (
            self.status == BudgetStatus.ACTIVE
            and self.start_date <= today <= self.end_date
        )


class BudgetLine(BaseTestModel):
    """
    Individual line item within a budget.

    Links a budgeted amount to a specific account.
    """

    budget_id: UUID = Field(
        description="Budget this line belongs to"
    )

    account_id: UUID = Field(
        description="Account this budget line applies to"
    )

    account_number: str = Field(
        description="Account number for reference"
    )

    account_name: str = Field(
        description="Account name for reference"
    )

    budgeted_amount: MoneyAmount = Field(
        description="Budgeted amount for this account"
    )

    notes: str = Field(
        default="",
        description="Notes and assumptions for this budget line"
    )

    @field_validator("budgeted_amount")
    @classmethod
    def validate_budgeted_amount(cls, v):
        """Ensure budgeted amount is non-negative."""
        if v < Decimal("0.00"):
            raise ValueError("budgeted_amount cannot be negative")
        return v


class VarianceReport(BaseTestModel):
    """
    Budget variance report showing budget vs actual.

    Used for comparing budgeted amounts to actual spending.
    """

    budget_id: UUID = Field(
        description="Budget this report is for"
    )

    budget_name: str = Field(
        description="Budget name"
    )

    fiscal_year: int = Field(
        description="Fiscal year"
    )

    period_start: AccountingDate = Field(
        description="Report period start date"
    )

    period_end: AccountingDate = Field(
        description="Report period end date"
    )

    as_of_date: AccountingDate = Field(
        description="Date actuals were calculated through"
    )

    total_budgeted: MoneyAmount = Field(
        description="Total budgeted amount"
    )

    total_actual: MoneyAmount = Field(
        description="Total actual amount"
    )

    total_variance: MoneyAmount = Field(
        description="Total variance (budgeted - actual)"
    )

    variance_percentage: Decimal = Field(
        description="Variance as percentage"
    )

    def is_favorable(self) -> bool:
        """Check if variance is favorable (under budget)."""
        return self.total_variance > Decimal("0.00")

    def is_unfavorable(self) -> bool:
        """Check if variance is unfavorable (over budget)."""
        return self.total_variance < Decimal("0.00")

    def is_on_track(self) -> bool:
        """Check if variance is within acceptable range (±5%)."""
        return abs(self.variance_percentage) <= Decimal("5.00")


class BudgetLineVariance(BaseTestModel):
    """Variance data for a single budget line."""

    budget_line_id: UUID = Field(
        description="Budget line this variance is for"
    )

    account_number: str = Field(
        description="Account number"
    )

    account_name: str = Field(
        description="Account name"
    )

    budgeted: MoneyAmount = Field(
        description="Budgeted amount"
    )

    actual: MoneyAmount = Field(
        description="Actual amount spent/earned"
    )

    variance: MoneyAmount = Field(
        description="Variance (budgeted - actual)"
    )

    variance_percentage: Decimal = Field(
        description="Variance as percentage of budget"
    )

    status: str = Field(
        description="Status: 'favorable', 'unfavorable', or 'on_track'"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Ensure status is valid."""
        valid_statuses = {"favorable", "unfavorable", "on_track"}
        if v not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}")
        return v
