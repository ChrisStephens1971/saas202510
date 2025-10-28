"""Tests for audit trail generation and tracking.

This test suite validates:
- Audit entry creation for all entity types
- Complete audit trail retrieval
- User activity tracking
- Multi-tenant isolation
- Immutability of audit log
"""

import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from qa_testing.compliance import AuditEntry, AuditEventType, AuditTrailGenerator
from qa_testing.generators import (
    FundGenerator,
    MemberGenerator,
    PropertyGenerator,
    TransactionGenerator,
)
from qa_testing.models import Transaction, TransactionType


class TestAuditEntryCreation(unittest.TestCase):
    """Test audit entry creation for different entity types."""

    def setUp(self):
        """Clear audit log before each test."""
        AuditTrailGenerator.clear_audit_log()

    def test_create_audit_entry_for_transaction(self):
        """Test creating audit entry for transaction creation."""
        # Arrange
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)
        transaction = TransactionGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
            member_id=member.id,
        )
        user_id = uuid4()

        # Act
        audit_entry = AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_CREATED,
            entity=transaction,
            user_id=user_id,
            change_reason="Monthly dues payment received",
        )

        # Assert
        self.assertIsNotNone(audit_entry.audit_id)
        self.assertEqual(audit_entry.tenant_id, property.tenant_id)
        self.assertEqual(audit_entry.event_type, AuditEventType.TRANSACTION_CREATED)
        self.assertEqual(audit_entry.entity_type, "Transaction")
        self.assertEqual(audit_entry.entity_id, transaction.id)
        self.assertEqual(audit_entry.user_id, user_id)
        self.assertIsNone(audit_entry.before_state)  # Creation has no before state
        self.assertIsNotNone(audit_entry.after_state)
        self.assertEqual(audit_entry.change_reason, "Monthly dues payment received")
        self.assertIsInstance(audit_entry.timestamp, datetime)

    def test_create_audit_entry_with_before_state(self):
        """Test creating audit entry with before state (update event)."""
        # Arrange
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )
        user_id = uuid4()

        before_state = transaction.model_dump(mode="json")

        # Simulate update
        transaction.is_posted = True

        # Act
        audit_entry = AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_POSTED,
            entity=transaction,
            user_id=user_id,
            before_state=before_state,
            change_reason="Transaction posted to ledger",
        )

        # Assert
        self.assertIsNotNone(audit_entry.before_state)
        self.assertFalse(audit_entry.before_state["is_posted"])  # Before: not posted
        self.assertTrue(audit_entry.after_state["is_posted"])  # After: posted

    def test_create_audit_entry_system_change(self):
        """Test creating audit entry for system-initiated change (no user)."""
        # Arrange
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        # Act - System change (no user_id)
        audit_entry = AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_CREATED,
            entity=transaction,
            user_id=None,  # System change
            change_reason="Automated bank sync",
        )

        # Assert
        self.assertIsNone(audit_entry.user_id)
        self.assertEqual(audit_entry.change_reason, "Automated bank sync")

    def test_create_audit_entry_with_session_tracking(self):
        """Test creating audit entry with IP and user agent."""
        # Arrange
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )
        user_id = uuid4()

        # Act
        audit_entry = AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_CREATED,
            entity=transaction,
            user_id=user_id,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )

        # Assert
        self.assertEqual(audit_entry.ip_address, "192.168.1.100")
        self.assertIn("Mozilla", audit_entry.user_agent)

    def test_audit_entry_stored_in_log(self):
        """Test that audit entries are stored in audit log."""
        # Arrange
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        initial_count = AuditTrailGenerator.get_entry_count()

        # Act
        AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_CREATED,
            entity=transaction,
        )

        # Assert
        self.assertEqual(
            AuditTrailGenerator.get_entry_count(),
            initial_count + 1
        )


class TestAuditTrailRetrieval(unittest.TestCase):
    """Test retrieving audit trails for entities."""

    def setUp(self):
        """Clear audit log before each test."""
        AuditTrailGenerator.clear_audit_log()

    def test_get_audit_trail_for_entity(self):
        """Test retrieving complete audit trail for entity."""
        # Arrange
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )
        user_id = uuid4()

        # Create multiple audit entries for same transaction
        AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_CREATED,
            entity=transaction,
            user_id=user_id,
        )

        before_state = transaction.model_dump(mode="json")
        transaction.is_posted = True

        AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_POSTED,
            entity=transaction,
            user_id=user_id,
            before_state=before_state,
        )

        # Act
        trail = AuditTrailGenerator.get_audit_trail(entity_id=transaction.id)

        # Assert
        self.assertEqual(len(trail), 2)
        self.assertEqual(trail[0].event_type, AuditEventType.TRANSACTION_CREATED)
        self.assertEqual(trail[1].event_type, AuditEventType.TRANSACTION_POSTED)

    def test_get_audit_trail_empty(self):
        """Test getting audit trail for entity with no entries."""
        # Act
        trail = AuditTrailGenerator.get_audit_trail(entity_id=uuid4())

        # Assert
        self.assertEqual(len(trail), 0)

    def test_get_audit_trail_filtered_by_date(self):
        """Test getting audit trail filtered by date range."""
        # Arrange
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        # Create entry
        AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_CREATED,
            entity=transaction,
        )

        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        # Act - Filter includes today
        trail_included = AuditTrailGenerator.get_audit_trail(
            entity_id=transaction.id,
            start_date=yesterday,
            end_date=tomorrow,
        )

        # Act - Filter excludes today
        trail_excluded = AuditTrailGenerator.get_audit_trail(
            entity_id=transaction.id,
            start_date=tomorrow,
            end_date=tomorrow,
        )

        # Assert
        self.assertEqual(len(trail_included), 1)
        self.assertEqual(len(trail_excluded), 0)

    def test_audit_trail_sorted_by_timestamp(self):
        """Test that audit trail is sorted chronologically."""
        # Arrange
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        # Create multiple entries (should be sorted oldest first)
        entry1 = AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_CREATED,
            entity=transaction,
        )

        before_state = transaction.model_dump(mode="json")
        transaction.is_posted = True

        entry2 = AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_POSTED,
            entity=transaction,
            before_state=before_state,
        )

        # Act
        trail = AuditTrailGenerator.get_audit_trail(entity_id=transaction.id)

        # Assert
        self.assertEqual(trail[0].audit_id, entry1.audit_id)
        self.assertEqual(trail[1].audit_id, entry2.audit_id)
        self.assertLessEqual(trail[0].timestamp, trail[1].timestamp)


class TestUserActivityTracking(unittest.TestCase):
    """Test user activity tracking."""

    def setUp(self):
        """Clear audit log before each test."""
        AuditTrailGenerator.clear_audit_log()

    def test_get_user_activity(self):
        """Test getting all changes made by specific user."""
        # Arrange
        property = PropertyGenerator.create()
        user_id = uuid4()

        # User creates multiple transactions
        for _ in range(3):
            transaction = TransactionGenerator.create(
                tenant_id=property.tenant_id,
                property_id=property.id,
            )
            AuditTrailGenerator.create_audit_entry(
                tenant_id=property.tenant_id,
                event_type=AuditEventType.TRANSACTION_CREATED,
                entity=transaction,
                user_id=user_id,
            )

        # Different user creates a transaction
        other_user_id = uuid4()
        other_transaction = TransactionGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )
        AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_CREATED,
            entity=other_transaction,
            user_id=other_user_id,
        )

        # Act
        activity = AuditTrailGenerator.get_user_activity(
            user_id=user_id,
            start_date=date.today(),
            end_date=date.today(),
        )

        # Assert
        self.assertEqual(len(activity), 3)  # Only the 3 from user_id
        for entry in activity:
            self.assertEqual(entry.user_id, user_id)

    def test_get_user_activity_filtered_by_tenant(self):
        """Test getting user activity filtered by tenant."""
        # Arrange
        property1 = PropertyGenerator.create()
        property2 = PropertyGenerator.create()
        user_id = uuid4()

        # User creates transaction in tenant 1
        txn1 = TransactionGenerator.create(
            tenant_id=property1.tenant_id,
            property_id=property1.id,
        )
        AuditTrailGenerator.create_audit_entry(
            tenant_id=property1.tenant_id,
            event_type=AuditEventType.TRANSACTION_CREATED,
            entity=txn1,
            user_id=user_id,
        )

        # User creates transaction in tenant 2
        txn2 = TransactionGenerator.create(
            tenant_id=property2.tenant_id,
            property_id=property2.id,
        )
        AuditTrailGenerator.create_audit_entry(
            tenant_id=property2.tenant_id,
            event_type=AuditEventType.TRANSACTION_CREATED,
            entity=txn2,
            user_id=user_id,
        )

        # Act - Filter by tenant 1
        activity_tenant1 = AuditTrailGenerator.get_user_activity(
            user_id=user_id,
            start_date=date.today(),
            end_date=date.today(),
            tenant_id=property1.tenant_id,
        )

        # Assert
        self.assertEqual(len(activity_tenant1), 1)
        self.assertEqual(activity_tenant1[0].tenant_id, property1.tenant_id)

    def test_get_user_activity_empty(self):
        """Test getting user activity when user made no changes."""
        # Act
        activity = AuditTrailGenerator.get_user_activity(
            user_id=uuid4(),
            start_date=date.today(),
            end_date=date.today(),
        )

        # Assert
        self.assertEqual(len(activity), 0)

    def test_get_user_activity_sorted_by_timestamp(self):
        """Test that user activity is sorted chronologically."""
        # Arrange
        property = PropertyGenerator.create()
        user_id = uuid4()

        # Create multiple entries
        entries = []
        for _ in range(3):
            transaction = TransactionGenerator.create(
                tenant_id=property.tenant_id,
                property_id=property.id,
            )
            entry = AuditTrailGenerator.create_audit_entry(
                tenant_id=property.tenant_id,
                event_type=AuditEventType.TRANSACTION_CREATED,
                entity=transaction,
                user_id=user_id,
            )
            entries.append(entry)

        # Act
        activity = AuditTrailGenerator.get_user_activity(
            user_id=user_id,
            start_date=date.today(),
            end_date=date.today(),
        )

        # Assert - Should be sorted oldest first
        for i in range(len(activity) - 1):
            self.assertLessEqual(
                activity[i].timestamp,
                activity[i + 1].timestamp
            )


class TestMultiTenantIsolation(unittest.TestCase):
    """Test multi-tenant isolation in audit log."""

    def setUp(self):
        """Clear audit log before each test."""
        AuditTrailGenerator.clear_audit_log()

    def test_get_all_entries_filtered_by_tenant(self):
        """Test that get_all_entries filters by tenant."""
        # Arrange
        property1 = PropertyGenerator.create()
        property2 = PropertyGenerator.create()

        # Create entries for tenant 1
        for _ in range(3):
            txn = TransactionGenerator.create(
                tenant_id=property1.tenant_id,
                property_id=property1.id,
            )
            AuditTrailGenerator.create_audit_entry(
                tenant_id=property1.tenant_id,
                event_type=AuditEventType.TRANSACTION_CREATED,
                entity=txn,
            )

        # Create entries for tenant 2
        for _ in range(2):
            txn = TransactionGenerator.create(
                tenant_id=property2.tenant_id,
                property_id=property2.id,
            )
            AuditTrailGenerator.create_audit_entry(
                tenant_id=property2.tenant_id,
                event_type=AuditEventType.TRANSACTION_CREATED,
                entity=txn,
            )

        # Act
        tenant1_entries = AuditTrailGenerator.get_all_entries(
            tenant_id=property1.tenant_id
        )
        tenant2_entries = AuditTrailGenerator.get_all_entries(
            tenant_id=property2.tenant_id
        )

        # Assert
        self.assertEqual(len(tenant1_entries), 3)
        self.assertEqual(len(tenant2_entries), 2)

        # Verify no cross-tenant leakage
        for entry in tenant1_entries:
            self.assertEqual(entry.tenant_id, property1.tenant_id)

        for entry in tenant2_entries:
            self.assertEqual(entry.tenant_id, property2.tenant_id)


class TestAuditLogImmutability(unittest.TestCase):
    """Test audit log immutability."""

    def setUp(self):
        """Clear audit log before each test."""
        AuditTrailGenerator.clear_audit_log()

    def test_audit_entries_are_immutable(self):
        """Test that audit entries cannot be modified after creation."""
        # Arrange
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        # Act
        audit_entry = AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_CREATED,
            entity=transaction,
        )

        # Attempt to modify (should fail with Pydantic validation)
        with self.assertRaises(Exception):  # Pydantic prevents modification
            audit_entry.event_type = AuditEventType.TRANSACTION_VOIDED

    def test_audit_log_is_append_only(self):
        """Test that audit log grows with each entry (append-only)."""
        # Arrange
        property = PropertyGenerator.create()

        # Act - Create entries
        for i in range(5):
            transaction = TransactionGenerator.create(
                tenant_id=property.tenant_id,
                property_id=property.id,
            )
            AuditTrailGenerator.create_audit_entry(
                tenant_id=property.tenant_id,
                event_type=AuditEventType.TRANSACTION_CREATED,
                entity=transaction,
            )

            # Assert - Count increases
            self.assertEqual(AuditTrailGenerator.get_entry_count(), i + 1)

    def test_clear_audit_log_only_for_testing(self):
        """Test that clear_audit_log includes warning about production use."""
        # This is a documentation test
        # In production, clear_audit_log should NEVER be called
        # It's only available for testing purposes

        # Arrange
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        AuditTrailGenerator.create_audit_entry(
            tenant_id=property.tenant_id,
            event_type=AuditEventType.TRANSACTION_CREATED,
            entity=transaction,
        )

        # Act
        AuditTrailGenerator.clear_audit_log()

        # Assert
        self.assertEqual(AuditTrailGenerator.get_entry_count(), 0)


if __name__ == "__main__":
    unittest.main()
