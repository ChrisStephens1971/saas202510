"""Tests for immutability verification.

This test suite validates:
- Detection of ledger entry updates (should never happen)
- Detection of ledger entry deletes (should never happen)
- Reversing entry pattern validation
- Immutability report generation
- Property-based testing for append-only invariant
"""

import unittest
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from qa_testing.compliance import ImmutabilityReport, ImmutabilityValidator
from qa_testing.generators import FundGenerator, PropertyGenerator
from qa_testing.models import LedgerEntry


class TestNoUpdates(unittest.TestCase):
    """Test detection of ledger entry updates."""

    def test_verify_no_updates_clean_ledger(self):
        """Test that clean ledger passes update check."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        entries = [
            LedgerEntry(
                tenant_id=property.tenant_id,
                property_id=property.id,
                fund_id=fund.id,
                transaction_id=uuid4(),
                entry_date=date.today(),
                description="Test entry",
                amount=Decimal("100.00"),
                is_debit=True,
                account_code="1000",
                account_name="Cash",
            )
            for _ in range(5)
        ]

        # Act
        is_valid = ImmutabilityValidator.verify_no_updates(entries)

        # Assert
        self.assertTrue(is_valid)

    def test_verify_no_updates_empty_ledger(self):
        """Test that empty ledger passes update check."""
        # Act
        is_valid = ImmutabilityValidator.verify_no_updates([])

        # Assert
        self.assertTrue(is_valid)


class TestNoDeletes(unittest.TestCase):
    """Test detection of ledger entry deletes."""

    def test_verify_no_deletes_all_present(self):
        """Test that ledger with all entries passes delete check."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        entries = [
            LedgerEntry(
                tenant_id=property.tenant_id,
                property_id=property.id,
                fund_id=fund.id,
                transaction_id=uuid4(),
                entry_date=date.today(),
                description=f"Test entry {i}",
                amount=Decimal("100.00"),
                is_debit=True,
                account_code="1000",
                account_name="Cash",
            )
            for i in range(5)
        ]

        expected_ids = [entry.id for entry in entries]

        # Act
        is_valid = ImmutabilityValidator.verify_no_deletes(expected_ids, entries)

        # Assert
        self.assertTrue(is_valid)

    def test_verify_no_deletes_entry_missing(self):
        """Test that missing entry is detected."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        entries = [
            LedgerEntry(
                tenant_id=property.tenant_id,
                property_id=property.id,
                fund_id=fund.id,
                transaction_id=uuid4(),
                entry_date=date.today(),
                description=f"Test entry {i}",
                amount=Decimal("100.00"),
                is_debit=True,
                account_code="1000",
                account_name="Cash",
            )
            for i in range(5)
        ]

        # Simulate deletion - remove one entry
        deleted_entry = entries.pop(2)
        expected_ids = [entry.id for entry in entries] + [deleted_entry.id]

        # Act
        is_valid = ImmutabilityValidator.verify_no_deletes(expected_ids, entries)

        # Assert
        self.assertFalse(is_valid)  # Should detect missing entry

    def test_verify_no_deletes_multiple_missing(self):
        """Test that multiple missing entries are detected."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        entries = [
            LedgerEntry(
                tenant_id=property.tenant_id,
                property_id=property.id,
                fund_id=fund.id,
                transaction_id=uuid4(),
                entry_date=date.today(),
                description=f"Test entry {i}",
                amount=Decimal("100.00"),
                is_debit=True,
                account_code="1000",
                account_name="Cash",
            )
            for i in range(5)
        ]

        all_ids = [entry.id for entry in entries]

        # Simulate deletion - keep only first 2 entries
        entries = entries[:2]

        # Act
        is_valid = ImmutabilityValidator.verify_no_deletes(all_ids, entries)

        # Assert
        self.assertFalse(is_valid)  # Should detect 3 missing entries

    def test_verify_no_deletes_empty_expected(self):
        """Test that empty expected list passes."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        entries = [
            LedgerEntry(
                tenant_id=property.tenant_id,
                property_id=property.id,
                fund_id=fund.id,
                transaction_id=uuid4(),
                entry_date=date.today(),
                description="Test entry",
                amount=Decimal("100.00"),
                is_debit=True,
                account_code="1000",
                account_name="Cash",
            )
        ]

        # Act - No expected IDs means nothing should be missing
        is_valid = ImmutabilityValidator.verify_no_deletes([], entries)

        # Assert
        self.assertTrue(is_valid)


class TestCorrectionPattern(unittest.TestCase):
    """Test reversing entry pattern validation."""

    def test_verify_correction_pattern_valid(self):
        """Test that valid correction pattern passes."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )
        transaction_id = uuid4()

        # Original entry (incorrect)
        original = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=transaction_id,
            entry_date=date.today(),
            description="Original entry (incorrect)",
            amount=Decimal("100.00"),
            is_debit=True,
            account_code="1000",
            account_name="Cash",
        )

        # Reversing entry
        reversing = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=transaction_id,
            entry_date=date.today(),
            description="Reversing entry",
            amount=Decimal("100.00"),
            is_debit=False,  # Opposite of original
            account_code="1000",
            account_name="Cash",
            is_reversing=True,
            reverses_entry_id=original.id,
        )

        # New correct entry
        correct = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=transaction_id,
            entry_date=date.today(),
            description="Correct entry",
            amount=Decimal("150.00"),
            is_debit=True,
            account_code="1000",
            account_name="Cash",
        )

        # Act
        is_valid = ImmutabilityValidator.verify_correction_pattern(
            original, [reversing, correct]
        )

        # Assert
        self.assertTrue(is_valid)

    def test_verify_correction_pattern_missing_reversing_entry(self):
        """Test that missing reversing entry is detected."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        original = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=uuid4(),
            entry_date=date.today(),
            description="Original entry",
            amount=Decimal("100.00"),
            is_debit=True,
            account_code="1000",
            account_name="Cash",
        )

        # Only new entry, no reversing entry
        new_entry = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=uuid4(),
            entry_date=date.today(),
            description="New entry",
            amount=Decimal("150.00"),
            is_debit=True,
            account_code="1000",
            account_name="Cash",
        )

        # Act
        is_valid = ImmutabilityValidator.verify_correction_pattern(
            original, [new_entry]
        )

        # Assert
        self.assertFalse(is_valid)  # Should detect missing reversing entry

    def test_verify_correction_pattern_wrong_amount(self):
        """Test that reversing entry with wrong amount is detected."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        original = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=uuid4(),
            entry_date=date.today(),
            description="Original entry",
            amount=Decimal("100.00"),
            is_debit=True,
            account_code="1000",
            account_name="Cash",
        )

        # Reversing entry with WRONG amount
        reversing = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=uuid4(),
            entry_date=date.today(),
            description="Reversing entry",
            amount=Decimal("50.00"),  # WRONG - should be 100.00
            is_debit=False,
            account_code="1000",
            account_name="Cash",
            is_reversing=True,
            reverses_entry_id=original.id,
        )

        # Act
        is_valid = ImmutabilityValidator.verify_correction_pattern(
            original, [reversing]
        )

        # Assert
        self.assertFalse(is_valid)  # Should detect wrong amount

    def test_verify_correction_pattern_same_debit_credit(self):
        """Test that reversing entry must have opposite debit/credit."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        original = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=uuid4(),
            entry_date=date.today(),
            description="Original entry",
            amount=Decimal("100.00"),
            is_debit=True,
            account_code="1000",
            account_name="Cash",
        )

        # Reversing entry with SAME debit/credit (should be opposite)
        reversing = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=uuid4(),
            entry_date=date.today(),
            description="Reversing entry",
            amount=Decimal("100.00"),
            is_debit=True,  # WRONG - should be False (credit)
            account_code="1000",
            account_name="Cash",
            is_reversing=True,
            reverses_entry_id=original.id,
        )

        # Act
        is_valid = ImmutabilityValidator.verify_correction_pattern(
            original, [reversing]
        )

        # Assert
        self.assertFalse(is_valid)  # Should detect same debit/credit

    def test_verify_correction_pattern_different_fund(self):
        """Test that reversing entry must be in same fund."""
        # Arrange
        property = PropertyGenerator.create()
        fund1 = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )
        fund2 = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        original = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund1.id,
            transaction_id=uuid4(),
            entry_date=date.today(),
            description="Original entry",
            amount=Decimal("100.00"),
            is_debit=True,
            account_code="1000",
            account_name="Cash",
        )

        # Reversing entry in DIFFERENT fund
        reversing = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund2.id,  # WRONG - should be fund1.id
            transaction_id=uuid4(),
            entry_date=date.today(),
            description="Reversing entry",
            amount=Decimal("100.00"),
            is_debit=False,
            account_code="1000",
            account_name="Cash",
            is_reversing=True,
            reverses_entry_id=original.id,
        )

        # Act
        is_valid = ImmutabilityValidator.verify_correction_pattern(
            original, [reversing]
        )

        # Assert
        self.assertFalse(is_valid)  # Should detect different fund

    def test_verify_correction_pattern_empty_corrections(self):
        """Test that empty correction list is detected."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        original = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=uuid4(),
            entry_date=date.today(),
            description="Original entry",
            amount=Decimal("100.00"),
            is_debit=True,
            account_code="1000",
            account_name="Cash",
        )

        # Act
        is_valid = ImmutabilityValidator.verify_correction_pattern(original, [])

        # Assert
        self.assertFalse(is_valid)  # Should detect empty corrections


class TestImmutabilityReport(unittest.TestCase):
    """Test immutability report generation."""

    def test_generate_report_clean_ledger(self):
        """Test report generation for clean ledger."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        entries = [
            LedgerEntry(
                tenant_id=property.tenant_id,
                property_id=property.id,
                fund_id=fund.id,
                transaction_id=uuid4(),
                entry_date=date.today(),
                description=f"Entry {i}",
                amount=Decimal("100.00"),
                is_debit=i % 2 == 0,
                account_code="1000",
                account_name="Cash",
            )
            for i in range(10)
        ]

        # Act
        report = ImmutabilityValidator.generate_immutability_report(
            tenant_id=property.tenant_id,
            ledger_entries=entries,
        )

        # Assert
        self.assertEqual(report.tenant_id, property.tenant_id)
        self.assertEqual(report.total_entries, 10)
        self.assertEqual(report.entries_with_updates, 0)
        self.assertEqual(report.entries_deleted, 0)
        self.assertEqual(report.reversing_entries, 0)
        self.assertTrue(report.is_immutable)
        self.assertEqual(len(report.violations), 0)
        self.assertIsNotNone(report.report_date)

    def test_generate_report_with_reversing_entries(self):
        """Test report counts reversing entries correctly."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        original_id = uuid4()

        entries = [
            LedgerEntry(
                tenant_id=property.tenant_id,
                property_id=property.id,
                fund_id=fund.id,
                transaction_id=uuid4(),
                entry_date=date.today(),
                description="Original entry",
                amount=Decimal("100.00"),
                is_debit=True,
                account_code="1000",
                account_name="Cash",
                id=original_id,
            ),
            LedgerEntry(
                tenant_id=property.tenant_id,
                property_id=property.id,
                fund_id=fund.id,
                transaction_id=uuid4(),
                entry_date=date.today(),
                description="Reversing entry",
                amount=Decimal("100.00"),
                is_debit=False,
                account_code="1000",
                account_name="Cash",
                is_reversing=True,
                reverses_entry_id=original_id,
            ),
        ]

        # Act
        report = ImmutabilityValidator.generate_immutability_report(
            tenant_id=property.tenant_id,
            ledger_entries=entries,
        )

        # Assert
        self.assertEqual(report.reversing_entries, 1)
        self.assertTrue(report.is_immutable)

    def test_generate_report_with_deletes(self):
        """Test report detects deleted entries."""
        # Arrange
        property = PropertyGenerator.create()
        fund = FundGenerator.create(
            tenant_id=property.tenant_id,
            property_id=property.id,
        )

        entries = [
            LedgerEntry(
                tenant_id=property.tenant_id,
                property_id=property.id,
                fund_id=fund.id,
                transaction_id=uuid4(),
                entry_date=date.today(),
                description=f"Entry {i}",
                amount=Decimal("100.00"),
                is_debit=True,
                account_code="1000",
                account_name="Cash",
            )
            for i in range(5)
        ]

        all_ids = [entry.id for entry in entries]

        # Simulate deletion
        deleted_entries = entries[:2]  # Delete first 2
        remaining_entries = entries[2:]  # Keep last 3

        # Act
        report = ImmutabilityValidator.generate_immutability_report(
            tenant_id=property.tenant_id,
            ledger_entries=remaining_entries,
            expected_entry_ids=all_ids,
        )

        # Assert
        self.assertEqual(report.entries_deleted, 2)
        self.assertFalse(report.is_immutable)
        self.assertGreater(len(report.violations), 0)
        self.assertIn("deleted", report.violations[0])

    def test_generate_report_empty_ledger(self):
        """Test report for empty ledger."""
        # Arrange
        property = PropertyGenerator.create()

        # Act
        report = ImmutabilityValidator.generate_immutability_report(
            tenant_id=property.tenant_id,
            ledger_entries=[],
        )

        # Assert
        self.assertEqual(report.total_entries, 0)
        self.assertTrue(report.is_immutable)
        self.assertEqual(len(report.violations), 0)
        self.assertIsNone(report.oldest_entry_date)
        self.assertIsNone(report.newest_entry_date)


if __name__ == "__main__":
    unittest.main()
