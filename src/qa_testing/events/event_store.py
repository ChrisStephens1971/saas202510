"""
Event Store for Financial Event Sourcing

Implements event sourcing pattern for complete audit trail and state reconstruction.

Key Concepts:
- Events are immutable facts about what happened
- Events are append-only (never modified or deleted)
- Current state is derived by replaying events
- Snapshots optimize performance for long event streams

Use Cases:
- Complete audit trail of all financial changes
- Point-in-time state reconstruction
- Event replay for debugging and testing
- Temporal queries (what was the state at date X?)
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of financial events that can occur."""

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

    # Payment events
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_REFUNDED = "payment_refunded"
    PAYMENT_FAILED = "payment_failed"

    # Balance events
    BALANCE_CALCULATED = "balance_calculated"
    BALANCE_ADJUSTED = "balance_adjusted"

    # System events
    SNAPSHOT_CREATED = "snapshot_created"
    DATA_MIGRATION = "data_migration"


class FinancialEvent(BaseModel):
    """
    Immutable financial event in event stream.

    Events are facts about what happened in the system. They are:
    - Immutable (frozen=True)
    - Append-only (never modified or deleted)
    - Timestamped with creation time
    - Linked to aggregate (entity they apply to)
    - Versioned for schema evolution
    """

    model_config = {"frozen": True}  # Immutable

    # Event identity
    event_id: UUID = Field(default_factory=uuid4, description="Unique event ID")
    event_type: EventType = Field(..., description="Type of event")

    # Multi-tenant isolation
    tenant_id: UUID = Field(..., description="Tenant ID for isolation")

    # Aggregate identity (entity this event applies to)
    aggregate_id: UUID = Field(..., description="ID of entity this event applies to")
    aggregate_type: str = Field(..., description="Type of aggregate (Transaction, Member, etc.)")

    # Temporal information
    timestamp: datetime = Field(default_factory=datetime.now, description="When event occurred")

    # Event data
    data: dict[str, Any] = Field(..., description="Event payload (what changed)")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Context (user, IP, etc.)")

    # Versioning
    version: int = Field(default=1, description="Event schema version")

    # Sequence (for ordering within aggregate)
    sequence: int = Field(..., description="Sequence number within aggregate stream")


class Snapshot(BaseModel):
    """
    Snapshot of aggregate state at a point in time.

    Snapshots optimize performance by avoiding replay of entire event stream.
    """

    snapshot_id: UUID = Field(default_factory=uuid4)
    aggregate_id: UUID
    aggregate_type: str
    tenant_id: UUID

    # State at this point
    state: dict[str, Any]

    # Position in event stream
    last_event_sequence: int
    snapshot_timestamp: datetime = Field(default_factory=datetime.now)

    # Metadata
    created_by: Optional[str] = None
    snapshot_reason: Optional[str] = None


class EventStore:
    """
    Event store for financial event sourcing.

    Provides:
    - Append-only event storage
    - Event retrieval by aggregate
    - Event replay for state reconstruction
    - Snapshot creation and retrieval
    - Temporal queries
    """

    # In-memory storage (for testing - use database in production)
    _events: dict[UUID, list[FinancialEvent]] = {}  # aggregate_id -> events
    _snapshots: dict[UUID, Snapshot] = {}  # aggregate_id -> latest snapshot
    _all_events: list[FinancialEvent] = []  # All events in order

    @classmethod
    def append(cls, event: FinancialEvent) -> None:
        """
        Append event to store.

        Events are immutable and append-only. Once appended, they cannot
        be modified or deleted.

        Args:
            event: FinancialEvent to append
        """
        # Add to aggregate stream
        if event.aggregate_id not in cls._events:
            cls._events[event.aggregate_id] = []
        cls._events[event.aggregate_id].append(event)

        # Add to global stream
        cls._all_events.append(event)

    @classmethod
    def get_events(
        cls,
        aggregate_id: UUID,
        from_sequence: int = 0,
        to_sequence: Optional[int] = None,
    ) -> list[FinancialEvent]:
        """
        Get events for an aggregate.

        Args:
            aggregate_id: Aggregate ID to get events for
            from_sequence: Start from this sequence (inclusive)
            to_sequence: End at this sequence (inclusive), None = all

        Returns:
            List of events for aggregate, ordered by sequence
        """
        if aggregate_id not in cls._events:
            return []

        events = cls._events[aggregate_id]

        # Filter by sequence range
        filtered = [
            e for e in events
            if e.sequence >= from_sequence
            and (to_sequence is None or e.sequence <= to_sequence)
        ]

        # Sort by sequence
        filtered.sort(key=lambda e: e.sequence)

        return filtered

    @classmethod
    def get_all_events(
        cls,
        tenant_id: Optional[UUID] = None,
        event_type: Optional[EventType] = None,
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None,
    ) -> list[FinancialEvent]:
        """
        Get all events with optional filtering.

        Args:
            tenant_id: Filter by tenant
            event_type: Filter by event type
            from_timestamp: Filter events after this time
            to_timestamp: Filter events before this time

        Returns:
            List of events matching filters, ordered by timestamp
        """
        events = cls._all_events

        # Filter by tenant
        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]

        # Filter by event type
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        # Filter by timestamp
        if from_timestamp:
            events = [e for e in events if e.timestamp >= from_timestamp]
        if to_timestamp:
            events = [e for e in events if e.timestamp <= to_timestamp]

        # Sort by timestamp
        events_sorted = sorted(events, key=lambda e: e.timestamp)

        return events_sorted

    @classmethod
    def replay_to_date(
        cls,
        aggregate_id: UUID,
        as_of_date: date,
    ) -> dict[str, Any]:
        """
        Replay events to reconstruct state at a specific date.

        Args:
            aggregate_id: Aggregate to reconstruct
            as_of_date: Date to reconstruct state at (end of day)

        Returns:
            State of aggregate as of that date
        """
        # Get all events up to end of that day
        end_of_day = datetime(as_of_date.year, as_of_date.month, as_of_date.day, 23, 59, 59)

        events = cls.get_events(aggregate_id)
        events_to_date = [e for e in events if e.timestamp <= end_of_day]

        # Replay events to build state
        state: dict[str, Any] = {}

        for event in events_to_date:
            # Apply event to state
            state = cls._apply_event(state, event)

        return state

    @classmethod
    def replay_all(cls, aggregate_id: UUID) -> dict[str, Any]:
        """
        Replay all events to get current state.

        Args:
            aggregate_id: Aggregate to reconstruct

        Returns:
            Current state of aggregate
        """
        events = cls.get_events(aggregate_id)

        state: dict[str, Any] = {}

        for event in events:
            state = cls._apply_event(state, event)

        return state

    @classmethod
    def replay_with_snapshot(cls, aggregate_id: UUID) -> dict[str, Any]:
        """
        Replay events using snapshot for optimization.

        If snapshot exists, start from snapshot state and replay events
        after snapshot. Otherwise, replay all events.

        Args:
            aggregate_id: Aggregate to reconstruct

        Returns:
            Current state of aggregate
        """
        # Check for snapshot
        snapshot = cls.get_snapshot(aggregate_id)

        if snapshot:
            # Start from snapshot state
            state = snapshot.state.copy()

            # Replay events after snapshot
            events = cls.get_events(
                aggregate_id,
                from_sequence=snapshot.last_event_sequence + 1
            )
        else:
            # No snapshot - replay all
            state = {}
            events = cls.get_events(aggregate_id)

        # Apply events
        for event in events:
            state = cls._apply_event(state, event)

        return state

    @classmethod
    def create_snapshot(
        cls,
        aggregate_id: UUID,
        aggregate_type: str,
        tenant_id: UUID,
        created_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Snapshot:
        """
        Create snapshot of current aggregate state.

        Args:
            aggregate_id: Aggregate to snapshot
            aggregate_type: Type of aggregate
            tenant_id: Tenant ID
            created_by: User who created snapshot
            reason: Reason for snapshot creation

        Returns:
            Created snapshot
        """
        # Get current state
        state = cls.replay_all(aggregate_id)

        # Get last event sequence
        events = cls.get_events(aggregate_id)
        last_sequence = events[-1].sequence if events else 0

        # Create snapshot
        snapshot = Snapshot(
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            tenant_id=tenant_id,
            state=state,
            last_event_sequence=last_sequence,
            created_by=created_by,
            snapshot_reason=reason,
        )

        # Store snapshot
        cls._snapshots[aggregate_id] = snapshot

        return snapshot

    @classmethod
    def get_snapshot(cls, aggregate_id: UUID) -> Optional[Snapshot]:
        """
        Get latest snapshot for aggregate.

        Args:
            aggregate_id: Aggregate ID

        Returns:
            Latest snapshot, or None if no snapshot exists
        """
        return cls._snapshots.get(aggregate_id)

    @classmethod
    def get_event_count(cls, aggregate_id: Optional[UUID] = None) -> int:
        """
        Get count of events.

        Args:
            aggregate_id: Optional aggregate to count events for

        Returns:
            Count of events
        """
        if aggregate_id:
            return len(cls._events.get(aggregate_id, []))
        else:
            return len(cls._all_events)

    @classmethod
    def clear(cls) -> None:
        """
        Clear all events and snapshots.

        WARNING: This is for testing only. In production, events should
        never be deleted.
        """
        cls._events.clear()
        cls._snapshots.clear()
        cls._all_events.clear()

    @staticmethod
    def _apply_event(state: dict[str, Any], event: FinancialEvent) -> dict[str, Any]:
        """
        Apply event to state.

        This is a simple merge strategy. In production, you'd have
        event-specific logic for each event type.

        Args:
            state: Current state
            event: Event to apply

        Returns:
            New state after applying event
        """
        # Create new state (immutable pattern)
        new_state = state.copy()

        # Merge event data into state
        new_state.update(event.data)

        # Add event metadata
        new_state["last_event_id"] = str(event.event_id)
        new_state["last_event_type"] = event.event_type.value
        new_state["last_updated"] = event.timestamp.isoformat()

        return new_state
