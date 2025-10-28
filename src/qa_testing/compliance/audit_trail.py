"""Audit trail generation and tracking for financial operations.

This module provides comprehensive audit logging for all financial operations,
enabling complete traceability of who made what changes, when, and why.

Key features:
- Immutable audit log (INSERT-only)
- Complete change history with before/after states
- User activity tracking
- Multi-tenant isolation
- IP address and user agent tracking
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import Field

from ..models.base import BaseTestModel


class AuditEventType(str, Enum):
    """Types of audit events for financial operations."""

    # Transaction events
    TRANSACTION_CREATED = "transaction_created"
    TRANSACTION_POSTED = "transaction_posted"
    TRANSACTION_VOIDED = "transaction_voided"
    TRANSACTION_UPDATED = "transaction_updated"

    # Ledger entry events
    LEDGER_ENTRY_CREATED = "ledger_entry_created"
    LEDGER_ENTRY_REVERSED = "ledger_entry_reversed"

    # Member events
    MEMBER_CREATED = "member_created"
    MEMBER_UPDATED = "member_updated"
    MEMBER_DEACTIVATED = "member_deactivated"

    # Property events
    PROPERTY_CREATED = "property_created"
    PROPERTY_UPDATED = "property_updated"

    # Fund events
    FUND_CREATED = "fund_created"
    FUND_UPDATED = "fund_updated"
    FUND_CLOSED = "fund_closed"

    # Unit events
    UNIT_CREATED = "unit_created"
    UNIT_UPDATED = "unit_updated"

    # Payment events
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_REFUNDED = "payment_refunded"
    PAYMENT_FAILED = "payment_failed"

    # Adjustment events
    ADJUSTMENT_CREATED = "adjustment_created"
    ADJUSTMENT_APPROVED = "adjustment_approved"
    ADJUSTMENT_REJECTED = "adjustment_rejected"

    # System events
    DATA_IMPORT = "data_import"
    DATA_EXPORT = "data_export"
    REPORT_GENERATED = "report_generated"


class AuditEntry(BaseTestModel):
    """
    Single audit trail entry recording a financial operation.

    CRITICAL: Audit entries are IMMUTABLE once created.
    - Never UPDATE an audit entry
    - Never DELETE an audit entry
    - Audit log is INSERT-only for compliance

    This model is used for:
    - Compliance audits (who changed what, when, why)
    - Dispute resolution (prove historical actions)
    - Security investigations (track unauthorized changes)
    - Regulatory reporting (complete audit trail)
    """

    model_config = {"frozen": True}

    # Audit entry identification
    audit_id: UUID = Field(
        default_factory=uuid4,
        description="Unique audit entry identifier"
    )

    # Multi-tenant isolation
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenant isolation")

    # Event information
    event_type: AuditEventType = Field(
        ...,
        description="Type of event that occurred"
    )
    entity_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type of entity changed (Transaction, LedgerEntry, etc.)"
    )
    entity_id: UUID = Field(
        ...,
        description="ID of entity that changed"
    )

    # User and session tracking
    user_id: Optional[UUID] = Field(
        None,
        description="User who made the change (None for system changes)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the change occurred"
    )

    # Change details
    before_state: Optional[dict] = Field(
        None,
        description="State before change (None for creation events)"
    )
    after_state: dict = Field(
        ...,
        description="State after change"
    )
    change_reason: Optional[str] = Field(
        None,
        max_length=1000,
        description="Reason for change (optional)"
    )

    # Session tracking
    ip_address: Optional[str] = Field(
        None,
        max_length=45,  # IPv6 max length
        description="IP address of user making change"
    )
    user_agent: Optional[str] = Field(
        None,
        max_length=500,
        description="User agent (browser/client) making change"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When audit entry was created (should match timestamp)"
    )

    def __str__(self) -> str:
        """String representation."""
        user_str = f"User {self.user_id}" if self.user_id else "System"
        time_str = self.timestamp.isoformat()
        return f"{user_str} {self.event_type.value} {self.entity_type} {self.entity_id} at {time_str}"


class AuditTrailGenerator:
    """
    Generate and query audit trails for financial operations.

    This class provides methods to:
    1. Create audit entries for any financial change
    2. Query complete audit history for entities
    3. Track user activity over time
    4. Generate audit reports

    All audit entries are stored in-memory for testing. In production,
    these would be stored in an append-only database table.
    """

    # In-memory audit log for testing
    # In production, this would be a database table
    _audit_log: list[AuditEntry] = []

    @classmethod
    def create_audit_entry(
        cls,
        tenant_id: UUID,
        event_type: AuditEventType,
        entity: Any,
        user_id: Optional[UUID] = None,
        before_state: Optional[dict] = None,
        change_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEntry:
        """
        Create audit entry for any financial change.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            event_type: Type of event (TRANSACTION_CREATED, etc.)
            entity: Entity that changed (Transaction, LedgerEntry, etc.)
            user_id: User who made the change (None for system)
            before_state: State before change (None for creation)
            change_reason: Why the change was made (optional)
            ip_address: IP address of user (optional)
            user_agent: User agent string (optional)

        Returns:
            AuditEntry: Created audit entry

        Example:
            >>> transaction = Transaction(...)
            >>> entry = AuditTrailGenerator.create_audit_entry(
            ...     tenant_id=tenant_id,
            ...     event_type=AuditEventType.TRANSACTION_CREATED,
            ...     entity=transaction,
            ...     user_id=user_id,
            ...     change_reason="Monthly dues payment"
            ... )
        """
        # Get entity type from class name
        entity_type = type(entity).__name__

        # Get entity ID
        entity_id = entity.id

        # Convert entity to dict for after_state
        after_state = entity.model_dump(mode="json")

        # Create audit entry
        audit_entry = AuditEntry(
            tenant_id=tenant_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            before_state=before_state,
            after_state=after_state,
            change_reason=change_reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Store in audit log
        cls._audit_log.append(audit_entry)

        return audit_entry

    @classmethod
    def get_audit_trail(
        cls,
        entity_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[AuditEntry]:
        """
        Get complete audit trail for entity.

        Args:
            entity_id: ID of entity to get audit trail for
            start_date: Optional start date filter (inclusive)
            end_date: Optional end date filter (inclusive)

        Returns:
            list[AuditEntry]: Audit entries for entity, sorted by timestamp

        Example:
            >>> trail = AuditTrailGenerator.get_audit_trail(
            ...     entity_id=transaction.id,
            ...     start_date=date(2025, 1, 1),
            ...     end_date=date(2025, 12, 31),
            ... )
            >>> print(f"Found {len(trail)} audit entries")
        """
        # Filter by entity_id
        entries = [
            entry for entry in cls._audit_log
            if entry.entity_id == entity_id
        ]

        # Filter by date range if provided
        if start_date:
            entries = [
                entry for entry in entries
                if entry.timestamp.date() >= start_date
            ]

        if end_date:
            entries = [
                entry for entry in entries
                if entry.timestamp.date() <= end_date
            ]

        # Sort by timestamp (oldest first)
        entries.sort(key=lambda e: e.timestamp)

        return entries

    @classmethod
    def get_user_activity(
        cls,
        user_id: UUID,
        start_date: date,
        end_date: date,
        tenant_id: Optional[UUID] = None,
    ) -> list[AuditEntry]:
        """
        Get all changes made by specific user.

        Args:
            user_id: User ID to get activity for
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            tenant_id: Optional tenant filter for multi-tenant isolation

        Returns:
            list[AuditEntry]: Audit entries for user, sorted by timestamp

        Example:
            >>> activity = AuditTrailGenerator.get_user_activity(
            ...     user_id=user_id,
            ...     start_date=date(2025, 10, 1),
            ...     end_date=date(2025, 10, 31),
            ... )
            >>> print(f"User made {len(activity)} changes in October")
        """
        # Filter by user_id
        entries = [
            entry for entry in cls._audit_log
            if entry.user_id == user_id
        ]

        # Filter by tenant_id if provided
        if tenant_id:
            entries = [
                entry for entry in entries
                if entry.tenant_id == tenant_id
            ]

        # Filter by date range
        entries = [
            entry for entry in entries
            if start_date <= entry.timestamp.date() <= end_date
        ]

        # Sort by timestamp (oldest first)
        entries.sort(key=lambda e: e.timestamp)

        return entries

    @classmethod
    def get_all_entries(
        cls,
        tenant_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[AuditEntry]:
        """
        Get all audit entries for tenant.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            start_date: Optional start date filter (inclusive)
            end_date: Optional end date filter (inclusive)

        Returns:
            list[AuditEntry]: All audit entries for tenant, sorted by timestamp

        Example:
            >>> all_entries = AuditTrailGenerator.get_all_entries(
            ...     tenant_id=tenant_id,
            ...     start_date=date(2025, 1, 1),
            ... )
        """
        # Filter by tenant_id
        entries = [
            entry for entry in cls._audit_log
            if entry.tenant_id == tenant_id
        ]

        # Filter by date range if provided
        if start_date:
            entries = [
                entry for entry in entries
                if entry.timestamp.date() >= start_date
            ]

        if end_date:
            entries = [
                entry for entry in entries
                if entry.timestamp.date() <= end_date
            ]

        # Sort by timestamp (oldest first)
        entries.sort(key=lambda e: e.timestamp)

        return entries

    @classmethod
    def clear_audit_log(cls) -> None:
        """
        Clear audit log (for testing only).

        CRITICAL: This should NEVER be called in production.
        Audit logs are immutable and must never be deleted.
        """
        cls._audit_log.clear()

    @classmethod
    def get_entry_count(cls) -> int:
        """Get total number of audit entries (for testing)."""
        return len(cls._audit_log)
