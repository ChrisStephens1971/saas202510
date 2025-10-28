"""Transaction and LedgerEntry models for HOA accounting system."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base import AccountingDate, BaseTestModel, MoneyAmount


class TransactionType(str, Enum):
    """Types of financial transactions."""

    # Income
    DUES_PAYMENT = "dues_payment"  # Regular HOA dues payment
    ASSESSMENT_PAYMENT = "assessment_payment"  # Special assessment payment
    LATE_FEE = "late_fee"  # Late fee charge
    TRANSFER_FEE = "transfer_fee"  # Transfer/closing fee
    OTHER_INCOME = "other_income"  # Other income

    # Expenses
    VENDOR_PAYMENT = "vendor_payment"  # Payment to vendor
    UTILITY = "utility"  # Utility payment
    MAINTENANCE = "maintenance"  # Maintenance expense
    INSURANCE = "insurance"  # Insurance payment
    MANAGEMENT_FEE = "management_fee"  # Property management fee
    OTHER_EXPENSE = "other_expense"  # Other expense

    # Adjustments
    REFUND = "refund"  # Refund to member
    ADJUSTMENT = "adjustment"  # Manual adjustment
    FUND_TRANSFER = "fund_transfer"  # Transfer between funds
    BANK_FEE = "bank_fee"  # Bank fee


class Transaction(BaseTestModel):
    """
    Transaction model representing a financial transaction.

    This model is used for generating test data to validate:
    - Payment processing
    - Double-entry bookkeeping
    - Transaction history
    - Financial reporting
    """

    # Multi-tenant isolation
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenant isolation")

    # Transaction information
    transaction_type: TransactionType = Field(
        ...,
        description="Type of transaction"
    )
    description: str = Field(..., min_length=1, max_length=500)
    transaction_date: AccountingDate = Field(
        default_factory=date.today,
        description="Date of transaction"
    )
    posted_date: Optional[AccountingDate] = Field(
        None,
        description="Date transaction was posted to ledger"
    )

    # Amounts
    amount: MoneyAmount = Field(
        ...,
        gt=Decimal("0.00"),
        description="Transaction amount (always positive)"
    )

    # Status
    is_posted: bool = Field(
        default=False,
        description="Whether transaction has been posted to ledger"
    )
    is_void: bool = Field(
        default=False,
        description="Whether transaction has been voided"
    )

    # Relationships
    member_id: Optional[UUID] = Field(
        None,
        description="Associated member ID (if applicable)"
    )
    unit_id: Optional[UUID] = Field(
        None,
        description="Associated unit ID (if applicable)"
    )
    property_id: UUID = Field(..., description="Associated property ID")
    fund_id: Optional[UUID] = Field(
        None,
        description="Associated fund ID"
    )

    # External references
    check_number: Optional[str] = Field(None, max_length=50)
    bank_reference: Optional[str] = Field(None, max_length=100)
    plaid_transaction_id: Optional[str] = Field(
        None,
        max_length=100,
        description="Plaid transaction ID (if from bank sync)"
    )

    # Metadata
    notes: Optional[str] = Field(None, max_length=2000)
    processed_at: Optional[datetime] = Field(
        None,
        description="Timestamp when transaction was processed"
    )

    def __str__(self) -> str:
        """String representation."""
        date_str = self.transaction_date.isoformat()
        amount_str = f"${self.amount:,.2f}"
        return f"{self.transaction_type.value}: {amount_str} on {date_str}"


class LedgerEntry(BaseTestModel):
    """
    LedgerEntry model representing a double-entry bookkeeping entry.

    CRITICAL: Ledger entries are IMMUTABLE once created.
    - Never UPDATE a ledger entry
    - Never DELETE a ledger entry
    - Use reversing entries to correct mistakes

    This model is used for generating test data to validate:
    - Double-entry bookkeeping (debits = credits)
    - Ledger immutability
    - Account balances
    - Financial statement generation
    """

    # Multi-tenant isolation
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenant isolation")

    # Entry information
    entry_date: AccountingDate = Field(
        default_factory=date.today,
        description="Date of ledger entry"
    )
    description: str = Field(..., min_length=1, max_length=500)

    # Amount and type
    amount: MoneyAmount = Field(
        ...,
        gt=Decimal("0.00"),
        description="Entry amount (always positive)"
    )
    is_debit: bool = Field(
        ...,
        description="True if debit entry, False if credit entry"
    )

    # Account information
    account_code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Account code (e.g., '1000' for Cash, '4000' for Dues Income)"
    )
    account_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Account name"
    )

    # Relationships
    transaction_id: UUID = Field(
        ...,
        description="Associated transaction ID"
    )
    fund_id: UUID = Field(
        ...,
        description="Associated fund ID"
    )
    property_id: UUID = Field(..., description="Associated property ID")

    # Immutability tracking
    is_reversing: bool = Field(
        default=False,
        description="Whether this is a reversing entry (to correct a mistake)"
    )
    reverses_entry_id: Optional[UUID] = Field(
        None,
        description="ID of entry this reverses (if is_reversing=True)"
    )

    @property
    def debit_amount(self) -> Decimal:
        """Return debit amount (0 if credit)."""
        return self.amount if self.is_debit else Decimal("0.00")

    @property
    def credit_amount(self) -> Decimal:
        """Return credit amount (0 if debit)."""
        return Decimal("0.00") if self.is_debit else self.amount

    def __str__(self) -> str:
        """String representation."""
        entry_type = "DR" if self.is_debit else "CR"
        amount_str = f"${self.amount:,.2f}"
        return f"{entry_type} {self.account_code} {self.account_name}: {amount_str}"
