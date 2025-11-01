"""Member models for HOA accounting system."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from .base import AccountingDate, BaseTestModel, MoneyAmount


class MemberType(str, Enum):
    """Types of members in an HOA."""

    OWNER = "owner"  # Property owner
    TENANT = "tenant"  # Renter
    BOARD_MEMBER = "board_member"  # HOA board member (also an owner)


class PaymentHistory(str, Enum):
    """Payment behavior patterns for realistic test data."""

    ON_TIME = "on_time"  # Always pays on time
    OCCASIONAL_LATE = "occasional_late"  # Sometimes late (10-20% of time)
    FREQUENTLY_LATE = "frequently_late"  # Often late (40-60% of time)
    DELINQUENT = "delinquent"  # Severely behind on payments
    OVERPAYER = "overpayer"  # Pays more than required (prepayment)


class Member(BaseTestModel):
    """
    Member model representing an HOA member (owner, tenant, or board member).

    This model is used for generating test data to validate:
    - Member account balances
    - Payment processing
    - Late fee calculations
    - Collection workflows
    """

    # Multi-tenant isolation
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenant isolation")

    # Personal information
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr = Field(..., description="Member email address")
    phone: Optional[str] = Field(None, max_length=20)

    # Member type and status
    member_type: MemberType = Field(
        default=MemberType.OWNER,
        description="Type of member (owner, tenant, board_member)"
    )
    is_active: bool = Field(default=True, description="Whether member is active")

    # Financial information
    current_balance: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Current account balance (negative = owes money)"
    )
    total_paid: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Total amount paid to date"
    )
    total_owed: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Total amount owed to date"
    )

    # Payment behavior (for test data generation)
    payment_history: PaymentHistory = Field(
        default=PaymentHistory.ON_TIME,
        description="Payment behavior pattern"
    )

    # Dates
    move_in_date: AccountingDate = Field(
        ...,
        description="Date member moved in or became owner"
    )
    move_out_date: Optional[AccountingDate] = Field(
        None,
        description="Date member moved out (if applicable)"
    )

    # Relationships
    unit_id: UUID = Field(..., description="Associated unit ID")
    property_id: UUID = Field(..., description="Associated property ID")

    @property
    def full_name(self) -> str:
        """Return full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_delinquent(self) -> bool:
        """Check if member is delinquent (owes money)."""
        return self.current_balance < Decimal("0.00")

    @property
    def is_board_member(self) -> bool:
        """Check if member is on the board."""
        return self.member_type == MemberType.BOARD_MEMBER

    @property
    def balance(self) -> Decimal:
        """Alias for current_balance (for test compatibility)."""
        return self.current_balance

    def __str__(self) -> str:
        """String representation."""
        return f"{self.full_name} ({self.member_type.value})"
