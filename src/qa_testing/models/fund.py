"""Fund models for HOA accounting system."""

from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base import BaseTestModel, MoneyAmount


class FundType(str, Enum):
    """Types of funds in HOA accounting."""

    OPERATING = "operating"  # Operating fund (day-to-day expenses)
    RESERVE = "reserve"  # Reserve fund (future capital improvements)
    SPECIAL_ASSESSMENT = "special_assessment"  # Special assessment fund
    CAPITAL_IMPROVEMENT = "capital_improvement"  # Capital improvement fund
    CONTINGENCY = "contingency"  # Contingency/emergency fund


class Fund(BaseTestModel):
    """
    Fund model representing a financial fund in the HOA accounting system.

    Funds are used to track different categories of money:
    - Operating fund: Day-to-day expenses (utilities, maintenance, etc.)
    - Reserve fund: Long-term capital improvements (roof, parking lot, etc.)
    - Special assessment: One-time special assessments
    - Capital improvement: Major improvements
    - Contingency: Emergency expenses

    This model is used for generating test data to validate:
    - Fund balance tracking
    - Negative balance prevention
    - Fund transfers and allocations
    - Financial reporting by fund
    """

    # Fund information
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    fund_type: FundType = Field(
        ...,
        description="Type of fund"
    )

    # Financial information
    current_balance: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Current fund balance"
    )
    target_balance: Optional[MoneyAmount] = Field(
        None,
        description="Target balance for reserve/contingency funds"
    )
    minimum_balance: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Minimum allowed balance (typically 0, but some funds may allow negative)"
    )

    # Configuration
    allow_negative_balance: bool = Field(
        default=False,
        description="Whether this fund can have a negative balance"
    )
    is_active: bool = Field(
        default=True,
        description="Whether this fund is active"
    )

    # Relationships
    property_id: UUID = Field(..., description="Associated property ID")

    @property
    def is_underfunded(self) -> bool:
        """Check if fund is below target balance."""
        if self.target_balance is None:
            return False
        return self.current_balance < self.target_balance

    @property
    def is_below_minimum(self) -> bool:
        """Check if fund is below minimum balance."""
        return self.current_balance < self.minimum_balance

    @property
    def funding_percentage(self) -> Optional[float]:
        """Calculate percentage of target balance achieved."""
        if self.target_balance is None or self.target_balance == Decimal("0.00"):
            return None
        return float((self.current_balance / self.target_balance) * 100)

    def __str__(self) -> str:
        """String representation."""
        balance_str = f"${self.current_balance:,.2f}"
        return f"{self.name} ({self.fund_type.value}): {balance_str}"
