"""
Property-based tests for audit trail immutability.

These tests validate that the audit trail (ledger entries) is immutable
and maintains complete history for compliance.
"""

from decimal import Decimal

import pytest
from hypothesis import given

from qa_testing.generators import LedgerEntryGenerator, PropertyGenerator, TransactionGenerator
from qa_testing.validators import AccountingValidator, ReconciliationValidator, ValidationError
from tests.strategies import ledger_entry_pair_strategy


class TestLedgerImmutability:
    """Tests for ledger entry immutability."""

    @pytest.mark.property
    @given(ledger_entry_pair_strategy())
    def test_ledger_entry_never_modified(self, entry_pair):
        """
        Property: For ANY ledger entry, it should never be modified after creation.

        This is a CRITICAL compliance requirement for financial audit trails.
        """
        debit, _ = entry_pair

        # Create a copy to represent "original" state
        original = type(debit)(**debit.model_dump())

        # Validate immutability (should pass for identical entry)
        assert AccountingValidator.validate_ledger_immutability(original, debit)

    @pytest.mark.property
    @given(ledger_entry_pair_strategy())
    def test_modified_ledger_entry_fails_validation(self, entry_pair):
        """
        Property: For ANY ledger entry, modifying it should fail validation.
        """
        debit, _ = entry_pair

        # Create original
        original = type(debit)(**debit.model_dump())

        # Modify the entry (simulate corruption/tampering)
        modified = type(debit)(**debit.model_dump())
        modified.amount = modified.amount + Decimal("100.00")

        # Should fail immutability check
        with pytest.raises(ValidationError, match="amount was modified"):
            AccountingValidator.validate_ledger_immutability(original, modified)

    def test_reversing_entry_preserves_original(self):
        """
        Test that reversing entries preserve the original entry.

        Corrections are done via NEW reversing entries, not by modifying originals.
        """
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        # Original entry
        debit_original, credit_original = LedgerEntryGenerator.create_for_payment(
            property_id=property.id,
            transaction=transaction,
            fund_id=property.id,
        )

        # Create reversing entry (for correction)
        correction_txn = TransactionGenerator.create(
            property_id=property.id,
            transaction_type=transaction.transaction_type,
            amount=Decimal("300.00"),
        )

        debit_reversing, credit_reversing = LedgerEntryGenerator.create_for_payment(
            property_id=property.id,
            transaction=correction_txn,
            fund_id=property.id,
        )

        # Mark as reversing
        debit_reversing.is_reversing = True
        debit_reversing.reverses_entry_id = debit_original.id

        # Original should still be unchanged
        assert debit_original.is_reversing is False
        assert debit_original.amount == Decimal("300.00")

        # Reversing entry should reference original
        assert debit_reversing.is_reversing is True
        assert debit_reversing.reverses_entry_id == debit_original.id


class TestAuditTrailCompleteness:
    """Tests for audit trail completeness."""

    def test_all_transactions_have_ledger_entries(self):
        """
        Test that all posted transactions have corresponding ledger entries.

        This ensures no transactions are "lost" in the audit trail.
        """
        property = PropertyGenerator.create()
        fund = PropertyGenerator.create().id  # Mock fund

        # Create 10 transactions
        transactions = []
        all_entries = []

        for i in range(10):
            txn = TransactionGenerator.create_payment(
                property_id=property.id,
                member_id=property.id,
                fund_id=fund,
                amount=Decimal("300.00"),
                is_posted=True,
            )
            transactions.append(txn)

            # Create ledger entries
            debit, credit = LedgerEntryGenerator.create_for_payment(
                property_id=property.id,
                transaction=txn,
                fund_id=fund,
            )
            all_entries.extend([debit, credit])

        # Verify all transactions have entries
        transaction_ids_with_entries = {entry.transaction_id for entry in all_entries}
        transaction_ids = {txn.id for txn in transactions}

        assert transaction_ids_with_entries == transaction_ids

    def test_ledger_entries_maintain_chronological_order(self):
        """
        Test that ledger entries maintain chronological order for audit purposes.
        """
        property = PropertyGenerator.create()
        fund = PropertyGenerator.create().id

        # Create transactions on different dates
        from datetime import date, timedelta

        entries = []
        for i in range(5):
            txn_date = date(2024, 1, 1) + timedelta(days=i * 7)

            txn = TransactionGenerator.create_payment(
                property_id=property.id,
                member_id=property.id,
                fund_id=fund,
                amount=Decimal("300.00"),
                transaction_date=txn_date,
                is_posted=True,
            )

            debit, credit = LedgerEntryGenerator.create_for_payment(
                property_id=property.id,
                transaction=txn,
                fund_id=fund,
            )

            entries.extend([debit, credit])

        # Verify entries are in chronological order
        entry_dates = [e.entry_date for e in entries]
        assert entry_dates == sorted(entry_dates)


class TestReconciliation:
    """Tests for account reconciliation."""

    def test_reconcile_balanced_entries(self):
        """Test that balanced entries reconcile to correct balance."""
        property = PropertyGenerator.create()
        fund = PropertyGenerator.create().id

        # Create 10 payments of $300 each = $3000 net debit (asset increase)
        all_entries = []
        for i in range(10):
            txn = TransactionGenerator.create_payment(
                property_id=property.id,
                member_id=property.id,
                fund_id=fund,
                amount=Decimal("300.00"),
            )

            debit, credit = LedgerEntryGenerator.create_for_payment(
                property_id=property.id,
                transaction=txn,
                fund_id=fund,
            )

            all_entries.extend([debit, credit])

        # For cash account (asset): debits increase, credits decrease
        # All cash debits
        cash_entries = [e for e in all_entries if e.account_code == "1000"]

        # Expected balance = sum of debits - sum of credits
        expected_balance = sum(e.debit_amount - e.credit_amount for e in cash_entries)

        # Should be $3000 (10 * $300 debits)
        assert expected_balance == Decimal("3000.00")

        # Reconcile
        assert ReconciliationValidator.reconcile_account_balance(
            cash_entries,
            expected_balance,
        )

    def test_reconcile_unbalanced_entries_fails(self):
        """Test that unbalanced entries fail reconciliation."""
        property = PropertyGenerator.create()
        txn = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        debit, credit = LedgerEntryGenerator.create_for_payment(
            property_id=property.id,
            transaction=txn,
            fund_id=property.id,
        )

        # Modify to make unbalanced
        credit.amount = Decimal("250.00")

        cash_entries = [e for e in [debit, credit] if e.account_code == "1000"]
        expected_balance = Decimal("300.00")

        # Should fail reconciliation
        with pytest.raises(ValidationError, match="reconciliation failed"):
            ReconciliationValidator.reconcile_account_balance(
                cash_entries,
                expected_balance,
            )

    def test_reconcile_with_refunds(self):
        """Test reconciliation with both payments and refunds."""
        property = PropertyGenerator.create()
        fund = PropertyGenerator.create().id

        all_entries = []

        # 5 payments of $300 = $1500 debit
        for i in range(5):
            txn = TransactionGenerator.create_payment(
                property_id=property.id,
                member_id=property.id,
                fund_id=fund,
                amount=Decimal("300.00"),
            )

            debit, credit = LedgerEntryGenerator.create_for_payment(
                property_id=property.id,
                transaction=txn,
                fund_id=fund,
            )

            all_entries.extend([debit, credit])

        # 2 refunds of $150 = $300 credit
        for i in range(2):
            txn = TransactionGenerator.create_refund(
                property_id=property.id,
                member_id=property.id,
                fund_id=fund,
                amount=Decimal("150.00"),
            )

            debit, credit = LedgerEntryGenerator.create_for_refund(
                property_id=property.id,
                transaction=txn,
                fund_id=fund,
            )

            all_entries.extend([debit, credit])

        # Cash account balance
        cash_entries = [e for e in all_entries if e.account_code == "1000"]

        # Expected: $1500 (payments) - $300 (refunds) = $1200
        expected_balance = Decimal("1200.00")

        assert ReconciliationValidator.reconcile_account_balance(
            cash_entries,
            expected_balance,
        )
