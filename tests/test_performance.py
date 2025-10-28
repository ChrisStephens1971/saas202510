"""
Performance tests for QA/Testing infrastructure.

These tests ensure that test data generation and validation
perform well at scale (1000+ transactions).
"""

import time
from decimal import Decimal

import pytest

from qa_testing.generators import (
    FundGenerator,
    LedgerEntryGenerator,
    MemberGenerator,
    PropertyGenerator,
    TransactionGenerator,
)
from qa_testing.validators import DoubleEntryValidator, TransactionValidator


@pytest.mark.slow
class TestGeneratorPerformance:
    """Performance tests for test data generators."""

    def test_generate_1000_members_under_5_seconds(self):
        """Test that generating 1000 members takes < 5 seconds."""
        property = PropertyGenerator.create()

        start_time = time.time()

        members = MemberGenerator.create_batch(
            1000,
            property_id=property.id,
        )

        elapsed_time = time.time() - start_time

        assert len(members) == 1000
        assert elapsed_time < 5.0, f"Generated 1000 members in {elapsed_time:.2f}s (should be < 5s)"

        print(f"\n✓ Generated 1000 members in {elapsed_time:.2f}s")

    def test_generate_1000_transactions_under_5_seconds(self):
        """Test that generating 1000 transactions takes < 5 seconds."""
        property = PropertyGenerator.create()

        start_time = time.time()

        transactions = TransactionGenerator.create_batch(
            1000,
            property_id=property.id,
        )

        elapsed_time = time.time() - start_time

        assert len(transactions) == 1000
        assert elapsed_time < 5.0, f"Generated 1000 transactions in {elapsed_time:.2f}s (should be < 5s)"

        print(f"\n✓ Generated 1000 transactions in {elapsed_time:.2f}s")

    def test_generate_1000_ledger_entry_pairs_under_10_seconds(self):
        """Test that generating 1000 ledger entry pairs takes < 10 seconds."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        start_time = time.time()

        entry_pairs = []
        for i in range(1000):
            transaction = TransactionGenerator.create_payment(
                property_id=property.id,
                member_id=property.id,  # Mock
                fund_id=fund.id,
                amount=Decimal("300.00"),
            )

            debit, credit = LedgerEntryGenerator.create_for_payment(
                property_id=property.id,
                transaction=transaction,
                fund_id=fund.id,
            )

            entry_pairs.append((debit, credit))

        elapsed_time = time.time() - start_time

        assert len(entry_pairs) == 1000
        assert elapsed_time < 10.0, f"Generated 1000 entry pairs in {elapsed_time:.2f}s (should be < 10s)"

        print(f"\n✓ Generated 1000 ledger entry pairs in {elapsed_time:.2f}s")


@pytest.mark.slow
class TestValidatorPerformance:
    """Performance tests for validators."""

    def test_validate_1000_transactions_under_2_seconds(self):
        """Test that validating 1000 transactions takes < 2 seconds."""
        property = PropertyGenerator.create()

        transactions = TransactionGenerator.create_batch(
            1000,
            property_id=property.id,
        )

        start_time = time.time()

        for txn in transactions:
            TransactionValidator.validate_transaction(txn)

        elapsed_time = time.time() - start_time

        assert elapsed_time < 2.0, f"Validated 1000 transactions in {elapsed_time:.2f}s (should be < 2s)"

        print(f"\n✓ Validated 1000 transactions in {elapsed_time:.2f}s")

    def test_validate_1000_ledger_entry_pairs_under_3_seconds(self):
        """Test that validating 1000 entry pairs takes < 3 seconds."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        # Generate entry pairs
        entry_pairs = []
        for i in range(1000):
            transaction = TransactionGenerator.create_payment(
                property_id=property.id,
                member_id=property.id,
                fund_id=fund.id,
                amount=Decimal("300.00"),
            )

            debit, credit = LedgerEntryGenerator.create_for_payment(
                property_id=property.id,
                transaction=transaction,
                fund_id=fund.id,
            )

            entry_pairs.append((debit, credit))

        start_time = time.time()

        for debit, credit in entry_pairs:
            DoubleEntryValidator.validate_entry_pair(debit, credit)

        elapsed_time = time.time() - start_time

        assert elapsed_time < 3.0, f"Validated 1000 entry pairs in {elapsed_time:.2f}s (should be < 3s)"

        print(f"\n✓ Validated 1000 ledger entry pairs in {elapsed_time:.2f}s")

    def test_validate_10000_entries_balanced_under_5_seconds(self):
        """Test that validating 10,000 entries are balanced takes < 5 seconds."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        # Generate 10,000 entries (5,000 pairs)
        all_entries = []
        for i in range(5000):
            transaction = TransactionGenerator.create_payment(
                property_id=property.id,
                member_id=property.id,
                fund_id=fund.id,
                amount=Decimal("300.00"),
            )

            debit, credit = LedgerEntryGenerator.create_for_payment(
                property_id=property.id,
                transaction=transaction,
                fund_id=fund.id,
            )

            all_entries.extend([debit, credit])

        start_time = time.time()

        DoubleEntryValidator.validate_balanced_entries(all_entries)

        elapsed_time = time.time() - start_time

        assert len(all_entries) == 10000
        assert elapsed_time < 5.0, f"Validated 10,000 entries in {elapsed_time:.2f}s (should be < 5s)"

        print(f"\n✓ Validated 10,000 ledger entries balanced in {elapsed_time:.2f}s")


@pytest.mark.slow
class TestEndToEndPerformance:
    """End-to-end performance tests."""

    def test_complete_workflow_1000_payments_under_30_seconds(self):
        """Test complete payment workflow for 1000 payments < 30 seconds."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)
        fund = FundGenerator.create(property_id=property.id)

        start_time = time.time()

        for i in range(1000):
            # 1. Create transaction
            transaction = TransactionGenerator.create_payment(
                property_id=property.id,
                member_id=member.id,
                fund_id=fund.id,
                amount=Decimal("300.00"),
            )

            # 2. Validate transaction
            TransactionValidator.validate_transaction(transaction)

            # 3. Create ledger entries
            debit, credit = LedgerEntryGenerator.create_for_payment(
                property_id=property.id,
                transaction=transaction,
                fund_id=fund.id,
            )

            # 4. Validate entries
            DoubleEntryValidator.validate_entry_pair(debit, credit)

        elapsed_time = time.time() - start_time

        assert elapsed_time < 30.0, f"Completed 1000 payments in {elapsed_time:.2f}s (should be < 30s)"

        print(f"\n✓ Completed 1000 payment workflows in {elapsed_time:.2f}s")
        print(f"  Average: {(elapsed_time / 1000) * 1000:.2f}ms per payment")


@pytest.mark.slow
class TestScalabilityMetrics:
    """Tests to measure scalability."""

    def test_measure_transactions_per_second(self):
        """Measure how many transactions can be generated per second."""
        property = PropertyGenerator.create()

        num_transactions = 10000
        start_time = time.time()

        transactions = TransactionGenerator.create_batch(
            num_transactions,
            property_id=property.id,
        )

        elapsed_time = time.time() - start_time
        transactions_per_second = num_transactions / elapsed_time

        print(f"\n✓ Generated {transactions_per_second:.0f} transactions/second")
        print(f"  Total: {num_transactions} transactions in {elapsed_time:.2f}s")

        # Should be at least 1000/second
        assert transactions_per_second > 1000, f"Only {transactions_per_second:.0f} txn/s (should be > 1000/s)"

    def test_measure_validations_per_second(self):
        """Measure how many validations can be performed per second."""
        property = PropertyGenerator.create()

        # Pre-generate transactions
        num_transactions = 10000
        transactions = TransactionGenerator.create_batch(
            num_transactions,
            property_id=property.id,
        )

        start_time = time.time()

        for txn in transactions:
            TransactionValidator.validate_transaction(txn)

        elapsed_time = time.time() - start_time
        validations_per_second = num_transactions / elapsed_time

        print(f"\n✓ Validated {validations_per_second:.0f} transactions/second")
        print(f"  Total: {num_transactions} validations in {elapsed_time:.2f}s")

        # Should be at least 3000/second
        assert validations_per_second > 3000, f"Only {validations_per_second:.0f} val/s (should be > 3000/s)"

    def test_memory_efficiency_large_batch(self):
        """Test that large batches don't consume excessive memory."""
        import sys

        property = PropertyGenerator.create()

        # Generate 10,000 transactions
        transactions = TransactionGenerator.create_batch(
            10000,
            property_id=property.id,
        )

        # Measure approximate size
        size_bytes = sys.getsizeof(transactions)
        size_mb = size_bytes / (1024 * 1024)

        print(f"\n✓ 10,000 transactions occupy ~{size_mb:.2f} MB")

        # Should be reasonable (< 50 MB for 10k transactions)
        assert size_mb < 50, f"10,000 transactions use {size_mb:.2f} MB (should be < 50 MB)"
