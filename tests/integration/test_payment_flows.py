"""
Integration tests for payment transaction flows.

These tests validate the complete payment lifecycle:
1. Create payment transaction
2. Generate balanced ledger entries
3. Update member balance
4. Validate double-entry bookkeeping
5. Verify database state
"""

from decimal import Decimal

import pytest

from qa_testing.database.fixtures import (
    get_member_balance,
    insert_ledger_entry,
    insert_transaction,
    update_member_balance,
)
from qa_testing.generators import LedgerEntryGenerator, TransactionGenerator
from qa_testing.validators import DoubleEntryValidator, TransactionValidator, ValidationError


@pytest.mark.integration
class TestPaymentFlow:
    """Integration tests for payment processing flow."""

    def test_complete_payment_flow(self, tenant_id, test_data):
        """
        Test complete payment flow from transaction creation to balance update.

        Flow:
        1. Member starts with balance
        2. Create payment transaction
        3. Generate balanced ledger entries
        4. Update member balance
        5. Validate all invariants hold
        """
        # Get test data
        member = test_data['members'][0]
        property = test_data['properties'][0]
        fund = test_data['funds'][0]  # Operating fund

        # Step 1: Get initial balance
        initial_balance = get_member_balance(tenant_id, member.id)

        # Step 2: Create payment transaction
        payment_amount = Decimal("300.00")
        transaction = TransactionGenerator.create_payment(
            tenant_id=tenant_id,
            property_id=property.id,
            member_id=member.id,
            unit_id=test_data['units'][0].id,
            fund_id=fund.id,
            amount=payment_amount,
            is_posted=True,
        )

        # Validate transaction
        assert TransactionValidator.validate_transaction(transaction)

        # Step 3: Insert transaction
        insert_transaction(tenant_id, transaction)

        # Step 4: Generate balanced ledger entries
        debit, credit = LedgerEntryGenerator.create_for_payment(
            tenant_id=tenant_id,
            property_id=property.id,
            transaction=transaction,
            fund_id=fund.id,
        )

        # Validate entries are balanced
        assert DoubleEntryValidator.validate_balanced_entries([debit, credit])
        assert DoubleEntryValidator.validate_entry_pair(debit, credit)

        # Step 5: Insert ledger entries
        insert_ledger_entry(tenant_id, debit)
        insert_ledger_entry(tenant_id, credit)

        # Step 6: Update member balance
        new_balance = initial_balance + payment_amount
        update_member_balance(tenant_id, member.id, new_balance)

        # Step 7: Validate balance update
        actual_balance = get_member_balance(tenant_id, member.id)
        assert TransactionValidator.validate_payment(
            transaction,
            initial_balance,
            actual_balance,
        )

        # Verify final state
        assert actual_balance == new_balance
        assert debit.amount == credit.amount == payment_amount
        assert debit.is_debit is True
        assert credit.is_debit is False

    def test_multiple_payments_maintain_balance(self, tenant_id, test_data):
        """
        Test that multiple payments correctly accumulate balance.

        This validates that the system maintains correct balances
        across multiple transactions.
        """
        member = test_data['members'][0]
        property = test_data['properties'][0]
        fund = test_data['funds'][0]

        initial_balance = get_member_balance(tenant_id, member.id)
        total_payments = Decimal("0.00")

        # Process 5 payments
        for i in range(5):
            payment_amount = Decimal("100.00") * (i + 1)  # $100, $200, $300, $400, $500

            # Create and insert transaction
            transaction = TransactionGenerator.create_payment(
                tenant_id=tenant_id,
                property_id=property.id,
                member_id=member.id,
                fund_id=fund.id,
                amount=payment_amount,
                is_posted=True,
            )
            insert_transaction(tenant_id, transaction)

            # Create and insert ledger entries
            debit, credit = LedgerEntryGenerator.create_for_payment(
                tenant_id=tenant_id,
                property_id=property.id,
                transaction=transaction,
                fund_id=fund.id,
            )
            insert_ledger_entry(tenant_id, debit)
            insert_ledger_entry(tenant_id, credit)

            # Update balance
            total_payments += payment_amount
            new_balance = initial_balance + total_payments
            update_member_balance(tenant_id, member.id, new_balance)

        # Verify final balance
        final_balance = get_member_balance(tenant_id, member.id)
        expected_balance = initial_balance + total_payments
        assert final_balance == expected_balance
        assert total_payments == Decimal("1500.00")  # 100+200+300+400+500

    def test_payment_with_wrong_amount_fails_validation(self, tenant_id, test_data):
        """
        Test that payment with incorrect balance update fails validation.

        This ensures validators catch errors in balance calculations.
        """
        member = test_data['members'][0]
        property = test_data['properties'][0]
        fund = test_data['funds'][0]

        initial_balance = get_member_balance(tenant_id, member.id)

        transaction = TransactionGenerator.create_payment(
            tenant_id=tenant_id,
            property_id=property.id,
            member_id=member.id,
            fund_id=fund.id,
            amount=Decimal("300.00"),
        )

        # Intentionally wrong balance (should be initial + 300, but we use initial + 250)
        wrong_balance = initial_balance + Decimal("250.00")

        with pytest.raises(ValidationError, match="incorrect balance"):
            TransactionValidator.validate_payment(
                transaction,
                initial_balance,
                wrong_balance,
            )

    def test_unbalanced_entries_fail_validation(self, tenant_id, test_data):
        """
        Test that unbalanced ledger entries fail validation.

        This is a critical invariant: debits must always equal credits.
        """
        property = test_data['properties'][0]
        fund = test_data['funds'][0]

        transaction = TransactionGenerator.create_payment(
            tenant_id=tenant_id,
            property_id=property.id,
            member_id=test_data['members'][0].id,
            fund_id=fund.id,
            amount=Decimal("300.00"),
        )

        debit, credit = LedgerEntryGenerator.create_for_payment(
            tenant_id=tenant_id,
            property_id=property.id,
            transaction=transaction,
            fund_id=fund.id,
        )

        # Intentionally unbalance the entries
        credit.amount = Decimal("250.00")

        with pytest.raises(ValidationError, match="not balanced"):
            DoubleEntryValidator.validate_balanced_entries([debit, credit])

    def test_payment_decimal_precision(self, tenant_id, test_data):
        """
        Test that payment amounts maintain exactly 2 decimal places.

        This validates our NUMERIC(15,2) data type requirement.
        """
        property = test_data['properties'][0]
        fund = test_data['funds'][0]

        # Create payment with exact 2 decimal places
        transaction = TransactionGenerator.create_payment(
            tenant_id=tenant_id,
            property_id=property.id,
            member_id=test_data['members'][0].id,
            fund_id=fund.id,
            amount=Decimal("123.45"),
        )

        # Validate precision
        assert transaction.amount.as_tuple().exponent == -2

        # Create ledger entries
        debit, credit = LedgerEntryGenerator.create_for_payment(
            tenant_id=tenant_id,
            property_id=property.id,
            transaction=transaction,
            fund_id=fund.id,
        )

        # Validate ledger entry precision
        assert debit.amount.as_tuple().exponent == -2
        assert credit.amount.as_tuple().exponent == -2
        assert debit.amount == credit.amount == Decimal("123.45")
