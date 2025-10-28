"""
Tests for Event Store functionality.

Covers:
- Event creation and appending
- Event retrieval and filtering
- Event replay and state reconstruction
- Point-in-time reconstruction
- Snapshot creation and optimization
- Multi-tenant isolation
- Edge cases
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from qa_testing.events import EventStore, EventType, FinancialEvent, Snapshot
from qa_testing.models import Member, Fund, Transaction, LedgerEntry


@pytest.fixture(autouse=True)
def clear_event_store():
    """Clear event store before each test."""
    EventStore.clear()
    yield
    EventStore.clear()


@pytest.fixture
def tenant_id():
    """Create a test tenant ID."""
    return uuid4()


@pytest.fixture
def another_tenant_id():
    """Create another test tenant ID."""
    return uuid4()


@pytest.fixture
def member_id():
    """Create a test member ID."""
    return uuid4()


@pytest.fixture
def fund_id():
    """Create a test fund ID."""
    return uuid4()


@pytest.fixture
def sample_event(tenant_id, member_id):
    """Create a sample financial event."""
    return FinancialEvent(
        event_type=EventType.MEMBER_CREATED,
        tenant_id=tenant_id,
        aggregate_id=member_id,
        aggregate_type="Member",
        data={
            "member_id": str(member_id),
            "name": "John Doe",
            "email": "john@example.com",
            "status": "active"
        },
        metadata={
            "user_id": "admin",
            "ip_address": "192.168.1.1"
        },
        sequence=1
    )


# ==============================================================================
# Test Event Creation and Immutability
# ==============================================================================

class TestEventCreation:
    """Test financial event creation and immutability."""

    def test_create_financial_event(self, tenant_id, member_id):
        """Test creating a financial event."""
        event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            data={"name": "John Doe"},
            sequence=1
        )

        assert event.event_type == EventType.MEMBER_CREATED
        assert event.tenant_id == tenant_id
        assert event.aggregate_id == member_id
        assert event.aggregate_type == "Member"
        assert event.data == {"name": "John Doe"}
        assert event.sequence == 1
        assert event.version == 1  # Default version

    def test_event_immutability(self, sample_event):
        """Test that events are immutable (frozen)."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            sample_event.data = {"modified": "data"}

    def test_event_has_unique_id(self, tenant_id, member_id):
        """Test that each event gets a unique ID."""
        event1 = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            data={},
            sequence=1
        )
        event2 = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            data={},
            sequence=2
        )

        assert event1.event_id != event2.event_id

    def test_event_has_timestamp(self, sample_event):
        """Test that events have timestamps."""
        assert isinstance(sample_event.timestamp, datetime)
        assert sample_event.timestamp <= datetime.now()


# ==============================================================================
# Test Event Appending
# ==============================================================================

class TestEventAppending:
    """Test appending events to event store."""

    def test_append_single_event(self, sample_event):
        """Test appending a single event."""
        EventStore.append(sample_event)

        assert EventStore.get_event_count() == 1
        assert EventStore.get_event_count(sample_event.aggregate_id) == 1

    def test_append_multiple_events(self, tenant_id, member_id):
        """Test appending multiple events for same aggregate."""
        events = [
            FinancialEvent(
                event_type=EventType.MEMBER_CREATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"name": "John Doe"},
                sequence=1
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"name": "John Smith"},
                sequence=2
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"email": "john.smith@example.com"},
                sequence=3
            )
        ]

        for event in events:
            EventStore.append(event)

        assert EventStore.get_event_count() == 3
        assert EventStore.get_event_count(member_id) == 3

    def test_append_events_multiple_aggregates(self, tenant_id, member_id, fund_id):
        """Test appending events for different aggregates."""
        member_event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            data={"name": "John Doe"},
            sequence=1
        )
        fund_event = FinancialEvent(
            event_type=EventType.FUND_CREATED,
            tenant_id=tenant_id,
            aggregate_id=fund_id,
            aggregate_type="Fund",
            data={"name": "Operating Fund"},
            sequence=1
        )

        EventStore.append(member_event)
        EventStore.append(fund_event)

        assert EventStore.get_event_count() == 2
        assert EventStore.get_event_count(member_id) == 1
        assert EventStore.get_event_count(fund_id) == 1


# ==============================================================================
# Test Event Retrieval
# ==============================================================================

class TestEventRetrieval:
    """Test retrieving events from event store."""

    def test_get_events_for_aggregate(self, tenant_id, member_id):
        """Test retrieving all events for an aggregate."""
        events = [
            FinancialEvent(
                event_type=EventType.MEMBER_CREATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"name": "John Doe"},
                sequence=1
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"name": "John Smith"},
                sequence=2
            )
        ]

        for event in events:
            EventStore.append(event)

        retrieved = EventStore.get_events(member_id)

        assert len(retrieved) == 2
        assert retrieved[0].sequence == 1
        assert retrieved[1].sequence == 2

    def test_get_events_with_sequence_range(self, tenant_id, member_id):
        """Test retrieving events within a sequence range."""
        events = [
            FinancialEvent(
                event_type=EventType.MEMBER_CREATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"seq": 1},
                sequence=1
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"seq": 2},
                sequence=2
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"seq": 3},
                sequence=3
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"seq": 4},
                sequence=4
            )
        ]

        for event in events:
            EventStore.append(event)

        # Get events from sequence 2 to 3
        retrieved = EventStore.get_events(member_id, from_sequence=2, to_sequence=3)

        assert len(retrieved) == 2
        assert retrieved[0].sequence == 2
        assert retrieved[1].sequence == 3

    def test_get_events_nonexistent_aggregate(self):
        """Test retrieving events for non-existent aggregate returns empty list."""
        fake_id = uuid4()
        events = EventStore.get_events(fake_id)

        assert events == []

    def test_get_all_events_no_filter(self, tenant_id, member_id, fund_id):
        """Test retrieving all events without filters."""
        member_event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            data={},
            sequence=1
        )
        fund_event = FinancialEvent(
            event_type=EventType.FUND_CREATED,
            tenant_id=tenant_id,
            aggregate_id=fund_id,
            aggregate_type="Fund",
            data={},
            sequence=1
        )

        EventStore.append(member_event)
        EventStore.append(fund_event)

        all_events = EventStore.get_all_events()

        assert len(all_events) == 2

    def test_get_all_events_filter_by_tenant(self, tenant_id, another_tenant_id, member_id):
        """Test filtering events by tenant ID."""
        tenant1_event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            data={},
            sequence=1
        )
        tenant2_event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=another_tenant_id,
            aggregate_id=uuid4(),
            aggregate_type="Member",
            data={},
            sequence=1
        )

        EventStore.append(tenant1_event)
        EventStore.append(tenant2_event)

        tenant1_events = EventStore.get_all_events(tenant_id=tenant_id)

        assert len(tenant1_events) == 1
        assert tenant1_events[0].tenant_id == tenant_id

    def test_get_all_events_filter_by_event_type(self, tenant_id, member_id, fund_id):
        """Test filtering events by event type."""
        member_event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            data={},
            sequence=1
        )
        fund_event = FinancialEvent(
            event_type=EventType.FUND_CREATED,
            tenant_id=tenant_id,
            aggregate_id=fund_id,
            aggregate_type="Fund",
            data={},
            sequence=1
        )

        EventStore.append(member_event)
        EventStore.append(fund_event)

        member_events = EventStore.get_all_events(event_type=EventType.MEMBER_CREATED)

        assert len(member_events) == 1
        assert member_events[0].event_type == EventType.MEMBER_CREATED

    def test_get_all_events_filter_by_timestamp(self, tenant_id, member_id):
        """Test filtering events by timestamp range."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Create event with timestamp from yesterday
        old_event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            timestamp=yesterday,
            data={},
            sequence=1
        )

        EventStore.append(old_event)

        # Filter for events from today onwards
        recent_events = EventStore.get_all_events(from_timestamp=now)
        assert len(recent_events) == 0

        # Filter for events up to tomorrow
        all_events = EventStore.get_all_events(to_timestamp=tomorrow)
        assert len(all_events) == 1


# ==============================================================================
# Test Event Replay
# ==============================================================================

class TestEventReplay:
    """Test event replay for state reconstruction."""

    def test_replay_all_single_event(self, tenant_id, member_id):
        """Test replaying a single event."""
        event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            data={
                "name": "John Doe",
                "email": "john@example.com"
            },
            sequence=1
        )

        EventStore.append(event)

        state = EventStore.replay_all(member_id)

        assert state["name"] == "John Doe"
        assert state["email"] == "john@example.com"
        assert "last_event_id" in state
        assert "last_event_type" in state

    def test_replay_all_multiple_events(self, tenant_id, member_id):
        """Test replaying multiple events builds up state."""
        events = [
            FinancialEvent(
                event_type=EventType.MEMBER_CREATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"name": "John Doe", "email": "john@example.com"},
                sequence=1
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"name": "John Smith"},  # Update name
                sequence=2
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"phone": "555-1234"},  # Add phone
                sequence=3
            )
        ]

        for event in events:
            EventStore.append(event)

        state = EventStore.replay_all(member_id)

        # Final state should have updated name and new phone
        assert state["name"] == "John Smith"
        assert state["email"] == "john@example.com"
        assert state["phone"] == "555-1234"

    def test_replay_empty_stream(self):
        """Test replaying empty event stream returns empty state."""
        fake_id = uuid4()
        state = EventStore.replay_all(fake_id)

        assert state == {}


# ==============================================================================
# Test Point-in-Time Reconstruction
# ==============================================================================

class TestPointInTimeReconstruction:
    """Test reconstructing state at specific points in time."""

    def test_replay_to_date_specific_date(self, tenant_id, member_id):
        """Test replaying events up to a specific date."""
        base_date = date(2024, 1, 1)

        events = [
            FinancialEvent(
                event_type=EventType.MEMBER_CREATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                timestamp=datetime(2024, 1, 1, 10, 0, 0),
                data={"balance": "1000.00"},
                sequence=1
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                timestamp=datetime(2024, 1, 2, 10, 0, 0),
                data={"balance": "1500.00"},
                sequence=2
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                timestamp=datetime(2024, 1, 3, 10, 0, 0),
                data={"balance": "2000.00"},
                sequence=3
            )
        ]

        for event in events:
            EventStore.append(event)

        # Replay to Jan 1 (should include first event only)
        state_jan1 = EventStore.replay_to_date(member_id, date(2024, 1, 1))
        assert state_jan1["balance"] == "1000.00"

        # Replay to Jan 2 (should include first two events)
        state_jan2 = EventStore.replay_to_date(member_id, date(2024, 1, 2))
        assert state_jan2["balance"] == "1500.00"

        # Replay to Jan 3 (should include all events)
        state_jan3 = EventStore.replay_to_date(member_id, date(2024, 1, 3))
        assert state_jan3["balance"] == "2000.00"

    def test_replay_to_date_before_any_events(self, tenant_id, member_id):
        """Test replaying to date before any events exist."""
        event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            timestamp=datetime(2024, 1, 2, 10, 0, 0),
            data={"balance": "1000.00"},
            sequence=1
        )

        EventStore.append(event)

        # Replay to Jan 1 (before event)
        state = EventStore.replay_to_date(member_id, date(2024, 1, 1))

        assert state == {}


# ==============================================================================
# Test Snapshots
# ==============================================================================

class TestSnapshots:
    """Test snapshot creation and retrieval."""

    def test_create_snapshot(self, tenant_id, member_id):
        """Test creating a snapshot of aggregate state."""
        events = [
            FinancialEvent(
                event_type=EventType.MEMBER_CREATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"name": "John Doe", "balance": "1000.00"},
                sequence=1
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"balance": "1500.00"},
                sequence=2
            )
        ]

        for event in events:
            EventStore.append(event)

        snapshot = EventStore.create_snapshot(
            aggregate_id=member_id,
            aggregate_type="Member",
            tenant_id=tenant_id,
            created_by="admin",
            reason="periodic snapshot"
        )

        assert snapshot.aggregate_id == member_id
        assert snapshot.aggregate_type == "Member"
        assert snapshot.tenant_id == tenant_id
        assert snapshot.last_event_sequence == 2
        assert snapshot.state["balance"] == "1500.00"
        assert snapshot.created_by == "admin"
        assert snapshot.snapshot_reason == "periodic snapshot"

    def test_get_snapshot(self, tenant_id, member_id):
        """Test retrieving a snapshot."""
        event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            data={"name": "John Doe"},
            sequence=1
        )

        EventStore.append(event)
        EventStore.create_snapshot(
            aggregate_id=member_id,
            aggregate_type="Member",
            tenant_id=tenant_id
        )

        snapshot = EventStore.get_snapshot(member_id)

        assert snapshot is not None
        assert snapshot.aggregate_id == member_id

    def test_get_snapshot_nonexistent(self):
        """Test retrieving snapshot for non-existent aggregate."""
        fake_id = uuid4()
        snapshot = EventStore.get_snapshot(fake_id)

        assert snapshot is None

    def test_replay_with_snapshot(self, tenant_id, member_id):
        """Test replaying with snapshot optimization."""
        # Create initial events
        events = [
            FinancialEvent(
                event_type=EventType.MEMBER_CREATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"name": "John Doe", "balance": "1000.00"},
                sequence=1
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"balance": "1500.00"},
                sequence=2
            )
        ]

        for event in events:
            EventStore.append(event)

        # Create snapshot after first 2 events
        EventStore.create_snapshot(
            aggregate_id=member_id,
            aggregate_type="Member",
            tenant_id=tenant_id
        )

        # Add more events after snapshot
        new_events = [
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"balance": "2000.00"},
                sequence=3
            ),
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"phone": "555-1234"},
                sequence=4
            )
        ]

        for event in new_events:
            EventStore.append(event)

        # Replay with snapshot should only replay events after snapshot
        state = EventStore.replay_with_snapshot(member_id)

        assert state["name"] == "John Doe"
        assert state["balance"] == "2000.00"
        assert state["phone"] == "555-1234"

    def test_replay_with_snapshot_no_snapshot(self, tenant_id, member_id):
        """Test replay with snapshot when no snapshot exists."""
        event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            data={"name": "John Doe"},
            sequence=1
        )

        EventStore.append(event)

        # Should fall back to replaying all events
        state = EventStore.replay_with_snapshot(member_id)

        assert state["name"] == "John Doe"


# ==============================================================================
# Test Multi-Tenant Isolation
# ==============================================================================

class TestMultiTenantIsolation:
    """Test multi-tenant isolation in event store."""

    def test_events_isolated_by_tenant(self, tenant_id, another_tenant_id):
        """Test that events are properly isolated by tenant."""
        member1_id = uuid4()
        member2_id = uuid4()

        tenant1_event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member1_id,
            aggregate_type="Member",
            data={"name": "Tenant 1 Member"},
            sequence=1
        )
        tenant2_event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=another_tenant_id,
            aggregate_id=member2_id,
            aggregate_type="Member",
            data={"name": "Tenant 2 Member"},
            sequence=1
        )

        EventStore.append(tenant1_event)
        EventStore.append(tenant2_event)

        # Get events for tenant 1 only
        tenant1_events = EventStore.get_all_events(tenant_id=tenant_id)
        assert len(tenant1_events) == 1
        assert tenant1_events[0].data["name"] == "Tenant 1 Member"

        # Get events for tenant 2 only
        tenant2_events = EventStore.get_all_events(tenant_id=another_tenant_id)
        assert len(tenant2_events) == 1
        assert tenant2_events[0].data["name"] == "Tenant 2 Member"


# ==============================================================================
# Test Edge Cases
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_large_event_stream(self, tenant_id, member_id):
        """Test handling large number of events."""
        # Create 100 events
        events = [
            FinancialEvent(
                event_type=EventType.MEMBER_UPDATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"counter": i},
                sequence=i
            )
            for i in range(1, 101)
        ]

        for event in events:
            EventStore.append(event)

        assert EventStore.get_event_count(member_id) == 100

        # Replay should handle large streams
        state = EventStore.replay_all(member_id)
        assert state["counter"] == 100  # Last event (range 1-100)

    def test_event_ordering_preserved(self, tenant_id, member_id):
        """Test that event ordering is preserved."""
        events = [
            FinancialEvent(
                event_type=EventType.MEMBER_CREATED,
                tenant_id=tenant_id,
                aggregate_id=member_id,
                aggregate_type="Member",
                data={"seq": i},
                sequence=i
            )
            for i in range(1, 11)
        ]

        # Append in order
        for event in events:
            EventStore.append(event)

        # Retrieve and verify order
        retrieved = EventStore.get_events(member_id)

        for i, event in enumerate(retrieved, start=1):
            assert event.sequence == i

    def test_clear_event_store(self, tenant_id, member_id):
        """Test clearing the event store (testing only)."""
        event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            data={},
            sequence=1
        )

        EventStore.append(event)
        assert EventStore.get_event_count() == 1

        EventStore.clear()
        assert EventStore.get_event_count() == 0

    def test_snapshot_multiple_aggregates(self, tenant_id):
        """Test creating snapshots for multiple aggregates."""
        member_id = uuid4()
        fund_id = uuid4()

        # Create events for member
        member_event = FinancialEvent(
            event_type=EventType.MEMBER_CREATED,
            tenant_id=tenant_id,
            aggregate_id=member_id,
            aggregate_type="Member",
            data={"name": "John Doe"},
            sequence=1
        )

        # Create events for fund
        fund_event = FinancialEvent(
            event_type=EventType.FUND_CREATED,
            tenant_id=tenant_id,
            aggregate_id=fund_id,
            aggregate_type="Fund",
            data={"name": "Operating Fund"},
            sequence=1
        )

        EventStore.append(member_event)
        EventStore.append(fund_event)

        # Create snapshots for both
        member_snapshot = EventStore.create_snapshot(
            aggregate_id=member_id,
            aggregate_type="Member",
            tenant_id=tenant_id
        )
        fund_snapshot = EventStore.create_snapshot(
            aggregate_id=fund_id,
            aggregate_type="Fund",
            tenant_id=tenant_id
        )

        # Verify both snapshots exist independently
        assert EventStore.get_snapshot(member_id) == member_snapshot
        assert EventStore.get_snapshot(fund_id) == fund_snapshot
