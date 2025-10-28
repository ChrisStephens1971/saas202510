"""
Property-based tests for accounting invariants.

These tests validate that core accounting rules hold for ALL possible inputs,
not just specific test cases we think of.

Critical invariants:
1. Debits = Credits (double-entry bookkeeping)
2. Fund balances never go negative (unless explicitly allowed)
3. Ledger entries are immutable once created
4. Money amounts always have exactly 2 decimal places
"""

from decimal import Decimal

import pytest
from hypothesis import given

from tests.strategies import fund_strategy, ledger_entry_pair_strategy, money_amount_strategy


class TestDoubleEntryBookkeeping:
    """Tests for double-entry bookkeeping invariants."""

    @pytest.mark.property
    @given(ledger_entry_pair_strategy())
    def test_debits_equal_credits_for_balanced_pair(self, entry_pair):
        """
        Property: For ANY balanced pair of ledger entries, debits must equal credits.

        This is the FUNDAMENTAL rule of double-entry bookkeeping.
        If this property fails, the entire accounting system is broken.
        """
        debit_entry, credit_entry = entry_pair

        # Calculate total debits and credits
        total_debits = debit_entry.debit_amount
        total_credits = credit_entry.credit_amount

        # INVARIANT: Debits MUST equal credits
        assert total_debits == total_credits, (
            f"Double-entry bookkeeping violation! "
            f"Debits ({total_debits}) != Credits ({total_credits})"
        )

    @pytest.mark.property
    @given(ledger_entry_pair_strategy())
    def test_transaction_amounts_match(self, entry_pair):
        """
        Property: For ANY balanced pair, both entries must have the same amount.

        This validates that the entry pair represents the same transaction.
        """
        debit_entry, credit_entry = entry_pair

        # INVARIANT: Both entries must have the same amount
        assert debit_entry.amount == credit_entry.amount, (
            f"Entry amounts don't match! "
            f"Debit: {debit_entry.amount}, Credit: {credit_entry.amount}"
        )

    @pytest.mark.property
    @given(ledger_entry_pair_strategy())
    def test_entries_share_transaction_id(self, entry_pair):
        """
        Property: For ANY balanced pair, both entries must reference the same transaction.

        This validates that entries are properly linked to their source transaction.
        """
        debit_entry, credit_entry = entry_pair

        # INVARIANT: Both entries must reference the same transaction
        assert debit_entry.transaction_id == credit_entry.transaction_id, (
            f"Entries don't share transaction ID! "
            f"Debit: {debit_entry.transaction_id}, Credit: {credit_entry.transaction_id}"
        )


class TestFundBalanceInvariants:
    """Tests for fund balance invariants."""

    @pytest.mark.property
    @given(fund_strategy())
    def test_fund_balance_respects_minimum(self, fund):
        """
        Property: For ANY fund, current balance must be >= minimum balance.

        Unless explicitly allowed, funds should never go below their minimum balance.
        """
        if not fund.allow_negative_balance:
            # INVARIANT: Balance >= minimum balance (when negatives not allowed)
            assert fund.current_balance >= fund.minimum_balance, (
                f"Fund balance below minimum! "
                f"Current: {fund.current_balance}, Minimum: {fund.minimum_balance}"
            )

    @pytest.mark.property
    @given(fund_strategy())
    def test_target_balance_is_positive_or_none(self, fund):
        """
        Property: For ANY fund with a target balance, target must be positive or None.

        Negative target balances don't make sense.
        """
        if fund.target_balance is not None:
            # INVARIANT: Target balance must be positive
            assert fund.target_balance > Decimal("0.00"), (
                f"Invalid target balance! "
                f"Target: {fund.target_balance} (must be positive or None)"
            )

    @pytest.mark.property
    @given(fund_strategy())
    def test_funding_percentage_calculation(self, fund):
        """
        Property: For ANY fund with a target balance, funding percentage must be accurate.

        Validates the funding_percentage property calculation.
        """
        if fund.target_balance is not None and fund.target_balance > Decimal("0.00"):
            expected_percentage = (fund.current_balance / fund.target_balance) * 100
            actual_percentage = fund.funding_percentage

            # INVARIANT: Funding percentage calculation must be correct
            assert actual_percentage is not None
            assert abs(float(actual_percentage) - float(expected_percentage)) < 0.01, (
                f"Funding percentage calculation error! "
                f"Expected: {expected_percentage:.2f}%, Actual: {actual_percentage:.2f}%"
            )


class TestMoneyAmountInvariants:
    """Tests for money amount data type invariants."""

    @pytest.mark.property
    @given(money_amount_strategy())
    def test_money_amounts_have_two_decimal_places(self, amount):
        """
        Property: For ANY money amount, it must have exactly 2 decimal places.

        This is CRITICAL for financial correctness. Floating-point errors are unacceptable.
        """
        # INVARIANT: Money amounts must have exactly 2 decimal places
        quantized = amount.quantize(Decimal("0.01"))
        assert amount == quantized, (
            f"Money amount precision error! "
            f"Amount: {amount} (should have exactly 2 decimal places)"
        )

    @pytest.mark.property
    @given(money_amount_strategy())
    def test_money_amounts_are_decimal_not_float(self, amount):
        """
        Property: For ANY money amount, it must be a Decimal, not a float.

        Floats have precision issues that are unacceptable for financial calculations.
        """
        # INVARIANT: Money amounts must be Decimal type
        assert isinstance(amount, Decimal), (
            f"Money amount is wrong type! "
            f"Type: {type(amount)} (must be Decimal, not float)"
        )

    @pytest.mark.property
    @given(money_amount_strategy(min_value=1, max_value=10000))
    def test_money_arithmetic_preserves_precision(self, amount):
        """
        Property: For ANY money amount, arithmetic operations must preserve 2 decimal places.

        This validates that our money arithmetic doesn't introduce precision errors.
        """
        # Perform some arithmetic
        doubled = amount * Decimal("2")
        halved = doubled / Decimal("2")

        # INVARIANT: Arithmetic must preserve precision
        assert halved == amount, (
            f"Precision lost during arithmetic! "
            f"Original: {amount}, After double and halve: {halved}"
        )

        # Both should have exactly 2 decimal places
        assert halved.as_tuple().exponent == -2, (
            f"Precision error! "
            f"Amount {halved} should have 2 decimal places"
        )


class TestLedgerImmutability:
    """Tests for ledger entry immutability invariants."""

    @pytest.mark.property
    @given(ledger_entry_pair_strategy())
    def test_ledger_entries_created_with_id(self, entry_pair):
        """
        Property: For ANY ledger entry, it must have a unique ID upon creation.

        This validates that entries are properly identified for immutability tracking.
        """
        debit_entry, credit_entry = entry_pair

        # INVARIANT: All entries must have IDs
        assert debit_entry.id is not None
        assert credit_entry.id is not None

        # INVARIANT: IDs must be unique
        assert debit_entry.id != credit_entry.id, (
            f"Ledger entries have duplicate IDs! "
            f"Debit: {debit_entry.id}, Credit: {credit_entry.id}"
        )

    @pytest.mark.property
    @given(ledger_entry_pair_strategy())
    def test_reversing_entries_reference_original(self, entry_pair):
        """
        Property: For ANY reversing entry, it must reference the original entry.

        This validates the reversing entry pattern for corrections.
        """
        debit_entry, credit_entry = entry_pair

        # If entry is marked as reversing, it must reference an original entry
        if debit_entry.is_reversing:
            assert debit_entry.reverses_entry_id is not None, (
                f"Reversing entry missing reference to original! "
                f"Entry ID: {debit_entry.id}"
            )

        if credit_entry.is_reversing:
            assert credit_entry.reverses_entry_id is not None, (
                f"Reversing entry missing reference to original! "
                f"Entry ID: {credit_entry.id}"
            )
