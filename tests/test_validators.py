"""
Tests for accounting validators.

These tests validate that our validators correctly catch accounting errors.
"""

from decimal import Decimal

import pytest

from qa_testing.generators import LedgerEntryGenerator, PropertyGenerator, TransactionGenerator
from qa_testing.models import Fund, FundType, LedgerEntry
from qa_testing.validators import (
    AccountingValidator,
    DoubleEntryValidator,
    TransactionValidator,
    ValidationError,
)


class TestDoubleEntryValidator:
    """Tests for double-entry bookkeeping validator."""

    def test_validates_balanced_entries(self):
        """Test that balanced entries pass validation."""
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,  # Using property ID as mock member ID
            amount=Decimal("300.00"),
        )

        debit, credit = LedgerEntryGenerator.create_for_payment(
            property_id=property.id,
            transaction=transaction,
            fund_id=property.id,  # Using property ID as mock fund ID
        )

        # Should not raise
        assert DoubleEntryValidator.validate_balanced_entries([debit, credit])

    def test_rejects_unbalanced_entries(self):
        """Test that unbalanced entries fail validation."""
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        debit, credit = LedgerEntryGenerator.create_for_payment(
            property_id=property.id,
            transaction=transaction,
            fund_id=property.id,
        )

        # Modify credit amount to make unbalanced
        credit.amount = Decimal("250.00")

        with pytest.raises(ValidationError, match="not balanced"):
            DoubleEntryValidator.validate_balanced_entries([debit, credit])

    def test_validates_entry_pair(self):
        """Test that valid entry pair passes validation."""
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        debit, credit = LedgerEntryGenerator.create_for_payment(
            property_id=property.id,
            transaction=transaction,
            fund_id=property.id,
        )

        # Should not raise
        assert DoubleEntryValidator.validate_entry_pair(debit, credit)

    def test_rejects_mismatched_amounts(self):
        """Test that mismatched amounts fail validation."""
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        debit, credit = LedgerEntryGenerator.create_for_payment(
            property_id=property.id,
            transaction=transaction,
            fund_id=property.id,
        )

        # Modify amounts
        debit.amount = Decimal("300.00")
        credit.amount = Decimal("250.00")

        with pytest.raises(ValidationError, match="amounts don't match"):
            DoubleEntryValidator.validate_entry_pair(debit, credit)

    def test_rejects_different_transactions(self):
        """Test that entries from different transactions fail validation."""
        property = PropertyGenerator.create()

        transaction1 = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )
        transaction2 = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        debit, _ = LedgerEntryGenerator.create_for_payment(
            property_id=property.id,
            transaction=transaction1,
            fund_id=property.id,
        )
        _, credit = LedgerEntryGenerator.create_for_payment(
            property_id=property.id,
            transaction=transaction2,
            fund_id=property.id,
        )

        with pytest.raises(ValidationError, match="different transactions"):
            DoubleEntryValidator.validate_entry_pair(debit, credit)


class TestTransactionValidator:
    """Tests for transaction validator."""

    def test_validates_valid_transaction(self):
        """Test that valid transaction passes validation."""
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        # Should not raise
        assert TransactionValidator.validate_transaction(transaction)

    def test_rejects_negative_amount(self):
        """Test that negative amount fails validation."""
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        # Modify to negative
        transaction.amount = Decimal("-100.00")

        with pytest.raises(ValidationError, match="non-positive amount"):
            TransactionValidator.validate_transaction(transaction)

    def test_rejects_wrong_decimal_places(self):
        """Test that wrong decimal places fail validation."""
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        # Modify to 3 decimal places
        transaction.amount = Decimal("300.123")

        with pytest.raises(ValidationError, match="wrong precision"):
            TransactionValidator.validate_transaction(transaction)

    def test_validates_payment_balance_update(self):
        """Test that payment balance update is validated correctly."""
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        balance_before = Decimal("100.00")
        balance_after = Decimal("400.00")

        # Should not raise
        assert TransactionValidator.validate_payment(
            transaction,
            balance_before,
            balance_after,
        )

    def test_rejects_incorrect_payment_balance(self):
        """Test that incorrect payment balance fails validation."""
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        balance_before = Decimal("100.00")
        balance_after = Decimal("350.00")  # Wrong!

        with pytest.raises(ValidationError, match="incorrect balance"):
            TransactionValidator.validate_payment(
                transaction,
                balance_before,
                balance_after,
            )


class TestAccountingValidator:
    """Tests for accounting validator."""

    def test_validates_fund_balance_above_minimum(self):
        """Test that fund balance above minimum passes validation."""
        fund = Fund(
            tenant_id=PropertyGenerator.create().id,
            property_id=PropertyGenerator.create().id,
            name="Operating Fund",
            fund_type=FundType.OPERATING,
            current_balance=Decimal("10000.00"),
            minimum_balance=Decimal("0.00"),
            allow_negative_balance=False,
        )

        # Should not raise
        assert AccountingValidator.validate_fund_balance(fund)

    def test_rejects_fund_balance_below_minimum(self):
        """Test that fund balance below minimum fails validation."""
        fund = Fund(
            tenant_id=PropertyGenerator.create().id,
            property_id=PropertyGenerator.create().id,
            name="Operating Fund",
            fund_type=FundType.OPERATING,
            current_balance=Decimal("-1000.00"),
            minimum_balance=Decimal("0.00"),
            allow_negative_balance=False,
        )

        with pytest.raises(ValidationError, match="below minimum"):
            AccountingValidator.validate_fund_balance(fund)

    def test_validates_accounting_equation(self):
        """Test that valid accounting equation passes validation."""
        assets = Decimal("100000.00")
        liabilities = Decimal("30000.00")
        equity = Decimal("70000.00")

        # Should not raise (Assets = Liabilities + Equity)
        assert AccountingValidator.validate_accounting_equation(
            assets,
            liabilities,
            equity,
        )

    def test_rejects_unbalanced_accounting_equation(self):
        """Test that unbalanced accounting equation fails validation."""
        assets = Decimal("100000.00")
        liabilities = Decimal("30000.00")
        equity = Decimal("60000.00")  # Wrong! Should be 70000

        with pytest.raises(ValidationError, match="equation violated"):
            AccountingValidator.validate_accounting_equation(
                assets,
                liabilities,
                equity,
            )

    def test_validates_ledger_immutability(self):
        """Test that unchanged entry passes immutability check."""
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        debit, _ = LedgerEntryGenerator.create_for_payment(
            property_id=property.id,
            transaction=transaction,
            fund_id=property.id,
        )

        # Should not raise (same entry)
        assert AccountingValidator.validate_ledger_immutability(debit, debit)

    def test_rejects_modified_entry_amount(self):
        """Test that modified entry amount fails immutability check."""
        property = PropertyGenerator.create()
        transaction = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
        )

        original, _ = LedgerEntryGenerator.create_for_payment(
            property_id=property.id,
            transaction=transaction,
            fund_id=property.id,
        )

        # Create modified copy
        modified = LedgerEntry(**original.model_dump())
        modified.amount = Decimal("250.00")

        with pytest.raises(ValidationError, match="amount was modified"):
            AccountingValidator.validate_ledger_immutability(original, modified)
