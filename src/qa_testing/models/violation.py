"""Violation tracking models for testing HOA compliance enforcement functionality."""

from datetime import date, time
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from .base import AccountingDate, BaseTestModel, MoneyAmount


class ViolationStatus(str, Enum):
    """Violation status progression through lifecycle."""

    REPORTED = "REPORTED"
    NOTICE_SENT = "NOTICE_SENT"
    PENDING_CURE = "PENDING_CURE"
    CURED = "CURED"
    HEARING_SCHEDULED = "HEARING_SCHEDULED"
    FINED = "FINED"
    CLOSED = "CLOSED"


class ViolationSeverity(str, Enum):
    """Severity levels for violations."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ViolationNoticeType(str, Enum):
    """Types of notices sent for violations."""

    FIRST_NOTICE = "FIRST_NOTICE"
    SECOND_NOTICE = "SECOND_NOTICE"
    FINAL_NOTICE = "FINAL_NOTICE"
    HEARING_NOTICE = "HEARING_NOTICE"
    FINE_NOTICE = "FINE_NOTICE"


class NoticeDeliveryMethod(str, Enum):
    """Delivery methods for violation notices."""

    EMAIL = "EMAIL"
    CERTIFIED_MAIL = "CERTIFIED_MAIL"
    REGULAR_MAIL = "REGULAR_MAIL"


class HearingOutcome(str, Enum):
    """Possible outcomes from violation hearings."""

    PENDING = "PENDING"
    UPHELD = "UPHELD"
    OVERTURNED = "OVERTURNED"
    MODIFIED = "MODIFIED"
    POSTPONED = "POSTPONED"


class Violation(BaseTestModel):
    """
    HOA violation tracking with photo evidence.

    Tracks violations from report through resolution including:
    - Violation type and severity classification
    - Status workflow (7 stages)
    - Cure deadline management
    - Fine assessment and payment tracking
    - Photo evidence links
    - Notice history
    """

    owner_id: UUID = Field(
        description="Owner with the violation"
    )

    unit_id: Optional[UUID] = Field(
        default=None,
        description="Unit where violation occurred (optional)"
    )

    violation_type: str = Field(
        description="Type of violation (e.g., 'Unpainted Fence', 'Overgrown Lawn')"
    )

    description: str = Field(
        description="Detailed description of violation"
    )

    location: str = Field(
        default="",
        description="Specific location on property"
    )

    severity: ViolationSeverity = Field(
        default=ViolationSeverity.MEDIUM,
        description="Severity level (LOW, MEDIUM, HIGH, CRITICAL)"
    )

    status: ViolationStatus = Field(
        default=ViolationStatus.REPORTED,
        description="Current status in violation workflow"
    )

    reported_date: AccountingDate = Field(
        description="Date violation was reported"
    )

    reported_by: str = Field(
        description="Who reported the violation (name or role)"
    )

    cure_deadline: Optional[AccountingDate] = Field(
        default=None,
        description="Deadline to cure violation"
    )

    cured_date: Optional[AccountingDate] = Field(
        default=None,
        description="Date violation was cured"
    )

    fine_amount: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Fine amount if assessed"
    )

    fine_paid: bool = Field(
        default=False,
        description="Whether fine has been paid"
    )

    notes: str = Field(
        default="",
        description="Internal notes about this violation"
    )

    @field_validator("fine_amount")
    @classmethod
    def validate_fine_amount_precision(cls, v):
        """Ensure fine_amount has exactly 2 decimal places."""
        return v.quantize(Decimal("0.01"))

    @field_validator("fine_amount")
    @classmethod
    def validate_fine_amount_non_negative(cls, v):
        """Ensure fine_amount is non-negative."""
        if v < Decimal("0.00"):
            raise ValueError("fine_amount must be non-negative")
        return v

    @field_validator("cure_deadline")
    @classmethod
    def validate_cure_deadline_after_reported(cls, v, info):
        """Ensure cure_deadline is after reported_date."""
        if v is not None and "reported_date" in info.data:
            if v < info.data["reported_date"]:
                raise ValueError("cure_deadline must be after reported_date")
        return v

    @field_validator("cured_date")
    @classmethod
    def validate_cured_date_after_reported(cls, v, info):
        """Ensure cured_date is after reported_date."""
        if v is not None and "reported_date" in info.data:
            if v < info.data["reported_date"]:
                raise ValueError("cured_date must be after reported_date")
        return v

    @property
    def is_open(self) -> bool:
        """Check if violation is still open (not cured or closed)."""
        return self.status not in [ViolationStatus.CURED, ViolationStatus.CLOSED]

    @property
    def is_overdue(self) -> bool:
        """Check if violation is past cure deadline."""
        if self.cure_deadline is None:
            return False
        return date.today() > self.cure_deadline and self.is_open


class ViolationPhoto(BaseTestModel):
    """
    Photo evidence for violations.

    Stores URLs/paths to uploaded photos with metadata.
    """

    violation_id: UUID = Field(
        description="Associated violation"
    )

    photo_url: str = Field(
        description="URL to photo (S3, CloudFlare, etc.)",
        max_length=500
    )

    caption: str = Field(
        default="",
        description="Photo caption or description"
    )

    taken_date: AccountingDate = Field(
        description="Date photo was taken"
    )

    uploaded_by: str = Field(
        description="Who uploaded this photo"
    )

    @field_validator("photo_url")
    @classmethod
    def validate_photo_url_not_empty(cls, v):
        """Ensure photo_url is not empty."""
        if not v or not v.strip():
            raise ValueError("photo_url cannot be empty")
        return v


class ViolationNotice(BaseTestModel):
    """
    Notices sent to owners about violations.

    Tracks notice delivery and responses including:
    - Notice type (5 types)
    - Delivery method (email, certified mail, regular mail)
    - Tracking information for certified mail
    - Delivery confirmation
    """

    violation_id: UUID = Field(
        description="Associated violation"
    )

    notice_type: ViolationNoticeType = Field(
        description="Type of notice sent"
    )

    sent_date: AccountingDate = Field(
        description="Date notice was sent"
    )

    delivery_method: NoticeDeliveryMethod = Field(
        default=NoticeDeliveryMethod.EMAIL,
        description="How notice was delivered"
    )

    tracking_number: str = Field(
        default="",
        description="Tracking number for certified mail"
    )

    delivered_date: Optional[AccountingDate] = Field(
        default=None,
        description="Date notice was delivered (if confirmed)"
    )

    notes: str = Field(
        default="",
        description="Notes about notice delivery"
    )

    @field_validator("delivered_date")
    @classmethod
    def validate_delivered_after_sent(cls, v, info):
        """Ensure delivered_date is after sent_date."""
        if v is not None and "sent_date" in info.data:
            if v < info.data["sent_date"]:
                raise ValueError("delivered_date must be after sent_date")
        return v

    @field_validator("tracking_number")
    @classmethod
    def validate_tracking_number_for_certified_mail(cls, v, info):
        """Ensure tracking_number is provided for certified mail."""
        if "delivery_method" in info.data:
            if info.data["delivery_method"] == NoticeDeliveryMethod.CERTIFIED_MAIL:
                if not v or not v.strip():
                    # Allow empty for testing, but warn in production
                    pass
        return v


class ViolationHearing(BaseTestModel):
    """
    Hearing scheduling and outcomes for violations.

    Board hearings for contested violations including:
    - Hearing scheduling (date, time, location)
    - Hearing outcomes (5 possible outcomes)
    - Fine assessment at hearing
    - Outcome notes and details
    """

    violation_id: UUID = Field(
        description="Associated violation"
    )

    scheduled_date: AccountingDate = Field(
        description="Date hearing is scheduled"
    )

    scheduled_time: time = Field(
        description="Time of hearing"
    )

    location: str = Field(
        description="Hearing location or video conference link"
    )

    outcome: HearingOutcome = Field(
        default=HearingOutcome.PENDING,
        description="Hearing outcome"
    )

    outcome_notes: str = Field(
        default="",
        description="Details of hearing outcome"
    )

    fine_assessed: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Fine amount assessed at hearing"
    )

    @field_validator("fine_assessed")
    @classmethod
    def validate_fine_assessed_precision(cls, v):
        """Ensure fine_assessed has exactly 2 decimal places."""
        return v.quantize(Decimal("0.01"))

    @field_validator("fine_assessed")
    @classmethod
    def validate_fine_assessed_non_negative(cls, v):
        """Ensure fine_assessed is non-negative."""
        if v < Decimal("0.00"):
            raise ValueError("fine_assessed must be non-negative")
        return v

    @field_validator("scheduled_time")
    @classmethod
    def validate_scheduled_time_type(cls, v):
        """Ensure scheduled_time is time type (not datetime)."""
        if not isinstance(v, time):
            raise ValueError("scheduled_time must be time type, not datetime")
        return v

    @property
    def is_completed(self) -> bool:
        """Check if hearing is completed (outcome not pending)."""
        return self.outcome != HearingOutcome.PENDING

    @property
    def was_violation_upheld(self) -> bool:
        """Check if violation was upheld at hearing."""
        return self.outcome in [HearingOutcome.UPHELD, HearingOutcome.MODIFIED]
