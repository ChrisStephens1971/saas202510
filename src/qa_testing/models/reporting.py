"""Reporting models for testing advanced reporting functionality."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from .base import AccountingDate, BaseTestModel


class ReportType(str, Enum):
    """Types of financial reports available."""

    GENERAL_LEDGER = "GENERAL_LEDGER"
    TRIAL_BALANCE = "TRIAL_BALANCE"
    INCOME_STATEMENT = "INCOME_STATEMENT"
    BALANCE_SHEET = "BALANCE_SHEET"
    CASH_FLOW = "CASH_FLOW"
    AR_AGING = "AR_AGING"
    OWNER_LEDGER = "OWNER_LEDGER"
    BUDGET_VARIANCE = "BUDGET_VARIANCE"
    RESERVE_FUNDING = "RESERVE_FUNDING"


class ExecutionStatus(str, Enum):
    """Report execution status values."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CustomReport(BaseTestModel):
    """
    User-defined custom report with saved filters, columns, and sort order.

    Allows users to create and save report configurations for repeated use.
    Reports can be private or shared publicly within the tenant.
    """

    name: str = Field(
        description="Report name (e.g., 'Monthly Income Statement - Pool Fund')"
    )

    report_type: ReportType = Field(
        description="Type of financial report"
    )

    columns: List[str] = Field(
        description="List of columns to display (e.g., ['date', 'account', 'amount'])"
    )

    filters: Dict[str, str] = Field(
        default_factory=dict,
        description="Report filters as key-value pairs (e.g., {'fund': 'uuid', 'date_from': '2025-01-01'})"
    )

    sort_by: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Sort order as list of field/direction dicts (e.g., [{'field': 'date', 'direction': 'desc'}])"
    )

    is_public: bool = Field(
        default=False,
        description="Whether report is shared publicly within tenant"
    )

    is_favorite: bool = Field(
        default=False,
        description="Whether user has marked this as a favorite report"
    )

    created_by: UUID = Field(
        description="User who created this custom report"
    )

    description: str = Field(
        default="",
        description="Optional description of report purpose and filters"
    )

    @field_validator("columns")
    @classmethod
    def validate_columns_not_empty(cls, v):
        """Ensure at least one column is selected."""
        if not v or len(v) == 0:
            raise ValueError("columns must contain at least one column")
        return v

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by_structure(cls, v):
        """Ensure sort_by entries have required fields."""
        for sort_item in v:
            if "field" not in sort_item or "direction" not in sort_item:
                raise ValueError("sort_by items must have 'field' and 'direction' keys")
            if sort_item["direction"] not in ["asc", "desc"]:
                raise ValueError("sort_by direction must be 'asc' or 'desc'")
        return v


class ReportExecution(BaseTestModel):
    """
    History of report executions with caching and performance tracking.

    Tracks each time a report is run, including execution time, row count,
    and cached results for performance optimization.
    """

    custom_report_id: UUID = Field(
        description="Custom report that was executed"
    )

    status: ExecutionStatus = Field(
        default=ExecutionStatus.PENDING,
        description="Current execution status"
    )

    started_at: datetime = Field(
        description="When execution started (datetime for precise tracking)"
    )

    completed_at: Optional[datetime] = Field(
        default=None,
        description="When execution completed or failed (datetime for precise tracking)"
    )

    row_count: int = Field(
        default=0,
        description="Number of rows in report result",
        ge=0,
    )

    execution_time_ms: int = Field(
        default=0,
        description="Execution time in milliseconds",
        ge=0,
    )

    error_message: str = Field(
        default="",
        description="Error message if execution failed"
    )

    result_cache: Optional[Dict] = Field(
        default=None,
        description="Cached report results as JSON (optional)"
    )

    parameters: Dict[str, str] = Field(
        default_factory=dict,
        description="Runtime parameters used for this execution (e.g., date ranges)"
    )

    executed_by: UUID = Field(
        description="User who executed this report"
    )

    @field_validator("completed_at")
    @classmethod
    def validate_completed_after_started(cls, v, info):
        """Ensure completed_at is after started_at."""
        if v is not None and "started_at" in info.data:
            if v < info.data["started_at"]:
                raise ValueError("completed_at must be after started_at")
        return v

    @field_validator("execution_time_ms")
    @classmethod
    def validate_execution_time_matches_duration(cls, v, info):
        """Verify execution time roughly matches completed_at - started_at."""
        data = info.data
        if v > 0 and "started_at" in data and "completed_at" in data and data.get("completed_at"):
            duration_ms = int((data["completed_at"] - data["started_at"]).total_seconds() * 1000)
            # Allow small rounding differences (within 100ms)
            if abs(v - duration_ms) > 100:
                raise ValueError(
                    f"execution_time_ms {v} does not match calculated duration {duration_ms}"
                )
        return v

    @field_validator("status")
    @classmethod
    def validate_status_transitions(cls, v, info):
        """Validate status field logic."""
        data = info.data

        # If status is COMPLETED, must have completed_at
        if v == ExecutionStatus.COMPLETED:
            if "completed_at" in data and data.get("completed_at") is None:
                raise ValueError("COMPLETED status requires completed_at timestamp")

        # If status is FAILED, should have error_message
        if v == ExecutionStatus.FAILED:
            if "error_message" in data and not data.get("error_message"):
                raise ValueError("FAILED status should have error_message")

        return v

    def is_completed(self) -> bool:
        """Check if execution completed successfully."""
        return self.status == ExecutionStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if execution failed."""
        return self.status == ExecutionStatus.FAILED

    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.status == ExecutionStatus.RUNNING

    def is_cached(self) -> bool:
        """Check if results are cached."""
        return self.result_cache is not None and len(self.result_cache) > 0
