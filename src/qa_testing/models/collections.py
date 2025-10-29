"""Collections and delinquency models for testing collections functionality."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from .base import AccountingDate, BaseTestModel, MoneyAmount


class FeeType(str, Enum):
    """Types of late fees that can be charged."""

    FLAT = "FLAT"
    PERCENTAGE = "PERCENTAGE"
    BOTH = "BOTH"


class CollectionStage(str, Enum):
    """Collection stage progression for delinquent accounts."""

    CURRENT = "CURRENT"
    DAYS_0_30 = "0_30_DAYS"
    DAYS_31_60 = "31_60_DAYS"
    DAYS_61_90 = "61_90_DAYS"
    DAYS_90_PLUS = "90_PLUS_DAYS"
    ATTORNEY_REFERRAL = "ATTORNEY_REFERRAL"
    LIEN_FILED = "LIEN_FILED"
    FORECLOSURE = "FORECLOSURE"


class NoticeType(str, Enum):
    """Types of collection notices that can be sent."""

    FIRST_NOTICE = "FIRST_NOTICE"
    SECOND_NOTICE = "SECOND_NOTICE"
    FINAL_NOTICE = "FINAL_NOTICE"
    PRE_LIEN = "PRE_LIEN"
    LIEN_FILED = "LIEN_FILED"
    ATTORNEY_REFERRAL = "ATTORNEY_REFERRAL"


class DeliveryMethod(str, Enum):
    """Delivery methods for collection notices."""

    EMAIL = "EMAIL"
    CERTIFIED_MAIL = "CERTIFIED_MAIL"
    REGULAR_MAIL = "REGULAR_MAIL"


class ActionType(str, Enum):
    """Types of collection actions."""

    ATTORNEY_REFERRAL = "ATTORNEY_REFERRAL"
    LIEN_FILED = "LIEN_FILED"
    FORECLOSURE = "FORECLOSURE"
    PAYMENT_PLAN = "PAYMENT_PLAN"
    WRITE_OFF = "WRITE_OFF"


class ActionStatus(str, Enum):
    """Status of collection actions."""

    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class LateFeeRule(BaseTestModel):
    """
    Late fee rule configuration.

    Defines how late fees are calculated and applied to delinquent accounts.
    Supports flat fees, percentage fees, or both with optional maximum cap.
    """

    name: str = Field(
        description="Rule name (e.g., 'Standard Late Fee')"
    )

    grace_period_days: int = Field(
        description="Grace period before late fee applies (typically 5-15 days)",
        ge=0,
        le=30,
    )

    fee_type: FeeType = Field(
        description="Type of late fee (FLAT, PERCENTAGE, or BOTH)"
    )

    flat_amount: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Flat fee amount (e.g., $25.00)"
    )

    percentage_rate: Decimal = Field(
        default=Decimal("0.00"),
        description="Percentage rate (e.g., 10.00 for 10%)",
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
    )

    max_amount: Optional[MoneyAmount] = Field(
        default=None,
        description="Maximum late fee cap (optional)"
    )

    is_recurring: bool = Field(
        default=False,
        description="Whether fee applies monthly while delinquent"
    )

    is_active: bool = Field(
        default=True,
        description="Whether this rule is currently active"
    )

    @field_validator("flat_amount")
    @classmethod
    def validate_flat_amount_precision(cls, v):
        """Ensure flat_amount has exactly 2 decimal places."""
        return v.quantize(Decimal("0.01"))

    @field_validator("max_amount")
    @classmethod
    def validate_max_amount_precision(cls, v):
        """Ensure max_amount has exactly 2 decimal places."""
        if v is None:
            return v
        return v.quantize(Decimal("0.01"))


class DelinquencyStatus(BaseTestModel):
    """
    Delinquency status tracking with aging buckets.

    Tracks collection stage, aging buckets (0-30, 31-60, 61-90, 90+ days),
    payment plan status, and notice history for delinquent accounts.
    """

    member_id: UUID = Field(
        description="Member with delinquent balance"
    )

    collection_stage: CollectionStage = Field(
        description="Current collection stage"
    )

    days_delinquent: int = Field(
        description="Number of days account is past due",
        ge=0,
    )

    balance_0_30: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Balance 0-30 days past due"
    )

    balance_31_60: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Balance 31-60 days past due"
    )

    balance_61_90: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Balance 61-90 days past due"
    )

    balance_90_plus: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Balance 90+ days past due"
    )

    current_balance: MoneyAmount = Field(
        description="Total current delinquent balance"
    )

    last_payment_date: Optional[AccountingDate] = Field(
        default=None,
        description="Date of last payment received"
    )

    last_notice_date: Optional[AccountingDate] = Field(
        default=None,
        description="Date of last notice sent"
    )

    is_payment_plan: bool = Field(
        default=False,
        description="Whether member is on a payment plan"
    )

    notes: str = Field(
        default="",
        description="Notes about delinquency status"
    )

    @field_validator("balance_0_30", "balance_31_60", "balance_61_90", "balance_90_plus", "current_balance")
    @classmethod
    def validate_balance_precision(cls, v):
        """Ensure all balances have exactly 2 decimal places."""
        return v.quantize(Decimal("0.01"))

    @field_validator("current_balance")
    @classmethod
    def validate_current_balance_sum(cls, v, info):
        """Verify current_balance equals sum of aging buckets."""
        data = info.data
        if all(key in data for key in ["balance_0_30", "balance_31_60", "balance_61_90", "balance_90_plus"]):
            sum_of_buckets = (
                data["balance_0_30"] +
                data["balance_31_60"] +
                data["balance_61_90"] +
                data["balance_90_plus"]
            )
            # Allow small rounding differences (within $0.01)
            if abs(v - sum_of_buckets) > Decimal("0.01"):
                raise ValueError(
                    f"current_balance {v} must equal sum of aging buckets {sum_of_buckets}"
                )
        return v

    @property
    def is_delinquent(self) -> bool:
        """Check if account is delinquent (has positive balance)."""
        return self.current_balance > Decimal("0.00")


class CollectionNotice(BaseTestModel):
    """
    Collection notice sent to delinquent member.

    Tracks notice type, delivery method, sent/delivered dates, and
    tracking information for certified mail.
    """

    delinquency_status_id: UUID = Field(
        description="Associated delinquency status"
    )

    notice_type: NoticeType = Field(
        description="Type of notice sent"
    )

    delivery_method: DeliveryMethod = Field(
        description="How notice was delivered"
    )

    sent_date: AccountingDate = Field(
        description="Date notice was sent"
    )

    balance_at_notice: MoneyAmount = Field(
        description="Balance at time notice was sent"
    )

    tracking_number: str = Field(
        default="",
        description="Tracking number for certified mail"
    )

    delivered_date: Optional[AccountingDate] = Field(
        default=None,
        description="Date notice was delivered (if confirmed)"
    )

    returned_undeliverable: bool = Field(
        default=False,
        description="Whether notice was returned as undeliverable"
    )

    notes: str = Field(
        default="",
        description="Notes about notice delivery"
    )

    @field_validator("balance_at_notice")
    @classmethod
    def validate_balance_precision(cls, v):
        """Ensure balance has exactly 2 decimal places."""
        return v.quantize(Decimal("0.01"))

    @field_validator("delivered_date")
    @classmethod
    def validate_delivered_after_sent(cls, v, info):
        """Ensure delivered_date is after sent_date."""
        if v is not None and "sent_date" in info.data:
            if v < info.data["sent_date"]:
                raise ValueError("delivered_date must be after sent_date")
        return v


class CollectionAction(BaseTestModel):
    """
    Collection action taken on delinquent account.

    Tracks attorney referrals, lien filings, foreclosures, payment plans,
    and write-offs with approval workflow and status tracking.
    """

    delinquency_status_id: UUID = Field(
        description="Associated delinquency status"
    )

    action_type: ActionType = Field(
        description="Type of collection action"
    )

    status: ActionStatus = Field(
        default=ActionStatus.PENDING_APPROVAL,
        description="Current status of action"
    )

    requested_date: AccountingDate = Field(
        description="Date action was requested"
    )

    approved_date: Optional[AccountingDate] = Field(
        default=None,
        description="Date action was approved by board"
    )

    approved_by: Optional[UUID] = Field(
        default=None,
        description="Board member who approved action"
    )

    completed_date: Optional[AccountingDate] = Field(
        default=None,
        description="Date action was completed"
    )

    balance_at_action: MoneyAmount = Field(
        description="Balance at time action was taken"
    )

    attorney_name: str = Field(
        default="",
        description="Attorney name (for attorney referrals)"
    )

    case_number: str = Field(
        default="",
        description="Case number (for liens/foreclosures)"
    )

    notes: str = Field(
        default="",
        description="Notes about collection action"
    )

    @field_validator("balance_at_action")
    @classmethod
    def validate_balance_precision(cls, v):
        """Ensure balance has exactly 2 decimal places."""
        return v.quantize(Decimal("0.01"))

    @field_validator("approved_date")
    @classmethod
    def validate_approved_after_requested(cls, v, info):
        """Ensure approved_date is after requested_date."""
        if v is not None and "requested_date" in info.data:
            if v < info.data["requested_date"]:
                raise ValueError("approved_date must be after requested_date")
        return v

    @field_validator("completed_date")
    @classmethod
    def validate_completed_after_requested(cls, v, info):
        """Ensure completed_date is after requested_date."""
        if v is not None and "requested_date" in info.data:
            if v < info.data["requested_date"]:
                raise ValueError("completed_date must be after requested_date")
        return v
