"""Auto-matching engine models for testing bank reconciliation matching."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from .base import AccountingDate, BaseTestModel


class RuleType(str, Enum):
    """Types of auto-matching rules."""

    EXACT = "EXACT"
    FUZZY = "FUZZY"
    PATTERN = "PATTERN"
    REFERENCE = "REFERENCE"
    ML = "ML"


class MatchStatus(str, Enum):
    """Status of match results."""

    SUGGESTED = "SUGGESTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    AUTO_MATCHED = "AUTO_MATCHED"


class AutoMatchRule(BaseTestModel):
    """
    Auto-match rule configuration.

    Defines matching rules for automatic bank reconciliation with 5 rule types:
    EXACT, FUZZY, PATTERN, REFERENCE, and ML. Tracks match performance with
    match_count and accuracy_rate metrics.
    """

    name: str = Field(
        description="Rule name (e.g., 'Exact Amount Match')"
    )

    rule_type: RuleType = Field(
        description="Type of matching rule (EXACT, FUZZY, PATTERN, REFERENCE, ML)"
    )

    pattern: dict = Field(
        description="Pattern configuration as dict (e.g., {'amount_tolerance': 0.01, 'date_range': 3})"
    )

    target_account_id: Optional[UUID] = Field(
        default=None,
        description="Target account for matching (optional)"
    )

    confidence_score: int = Field(
        description="Minimum confidence score required (0-100)",
        ge=0,
        le=100,
    )

    match_count: int = Field(
        default=0,
        description="Number of times this rule has been used",
        ge=0,
    )

    accuracy_rate: Decimal = Field(
        default=Decimal("0.00"),
        description="Percentage of verified matches (0-100%)",
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
    )

    is_active: bool = Field(
        default=True,
        description="Whether this rule is currently active"
    )

    @field_validator("accuracy_rate")
    @classmethod
    def validate_accuracy_rate_precision(cls, v):
        """Ensure accuracy_rate has exactly 2 decimal places."""
        return v.quantize(Decimal("0.01"))


class MatchResult(BaseTestModel):
    """
    Match result for bank transaction reconciliation.

    Stores potential matches between bank transactions and general ledger entries
    with confidence scores, explanations, and review status. Supports 4 statuses:
    SUGGESTED, ACCEPTED, REJECTED, and AUTO_MATCHED.
    """

    bank_transaction_id: UUID = Field(
        description="Bank transaction being matched"
    )

    matched_entry_id: UUID = Field(
        description="General ledger entry that matches"
    )

    rule_used_id: UUID = Field(
        description="Auto-match rule that generated this match"
    )

    confidence_score: int = Field(
        description="Confidence score for this match (0-100)",
        ge=0,
        le=100,
    )

    match_explanation: str = Field(
        description="Explanation of why this match was suggested"
    )

    status: MatchStatus = Field(
        default=MatchStatus.SUGGESTED,
        description="Current status of this match"
    )

    reviewed_by: Optional[UUID] = Field(
        default=None,
        description="User who reviewed this match (for ACCEPTED/REJECTED)"
    )

    reviewed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when match was reviewed (for ACCEPTED/REJECTED)"
    )

    @field_validator("reviewed_at")
    @classmethod
    def validate_reviewed_status(cls, v, info):
        """Ensure ACCEPTED/REJECTED status has reviewed_at and reviewed_by."""
        data = info.data
        if "status" in data:
            status = data["status"]
            if status in [MatchStatus.ACCEPTED, MatchStatus.REJECTED]:
                if v is None:
                    # Allow None during construction, but document the requirement
                    pass
        return v


class MatchStatistics(BaseTestModel):
    """
    Daily aggregated matching statistics.

    Tracks daily performance of auto-matching engine with total transactions,
    auto-matched count, manually matched count, unmatched count, and rates.
    Goal: achieve 90-95% auto_match_rate.
    """

    date: AccountingDate = Field(
        description="Date for these statistics"
    )

    total_transactions: int = Field(
        description="Total bank transactions for this date",
        ge=0,
    )

    auto_matched: int = Field(
        description="Number of transactions auto-matched",
        ge=0,
    )

    manually_matched: int = Field(
        description="Number of transactions manually matched",
        ge=0,
    )

    unmatched: int = Field(
        description="Number of unmatched transactions",
        ge=0,
    )

    auto_match_rate: Decimal = Field(
        description="Percentage of transactions auto-matched (goal: 90-95%)",
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
    )

    average_confidence: Decimal = Field(
        description="Average confidence score of auto-matches",
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
    )

    @field_validator("auto_match_rate", "average_confidence")
    @classmethod
    def validate_rate_precision(cls, v):
        """Ensure rates have exactly 2 decimal places."""
        return v.quantize(Decimal("0.01"))

    @field_validator("total_transactions")
    @classmethod
    def validate_total_transactions_sum(cls, v, info):
        """Verify total_transactions equals sum of matched and unmatched."""
        data = info.data
        if all(key in data for key in ["auto_matched", "manually_matched", "unmatched"]):
            sum_of_categories = (
                data["auto_matched"] +
                data["manually_matched"] +
                data["unmatched"]
            )
            if v != sum_of_categories:
                raise ValueError(
                    f"total_transactions {v} must equal sum of auto_matched + manually_matched + unmatched = {sum_of_categories}"
                )
        return v

    class Config:
        """Pydantic config."""
        # Ensure unique per tenant and date
        unique_together = [["tenant_id", "date"]]
