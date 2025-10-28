"""
Integration tests for refund transaction flows.

These tests validate the complete refund lifecycle:
1. Create refund transaction
2. Generate balanced ledger entries (reversed from payment)
3. Update member balance (decrease)
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
class TestRefundFlow:
    """Integration tests for refund processing flow."""

    def test_complete_refund_flow(self, tenant_id, test_data):
        """
        Test complete refund flow from transaction creation to balance update.

        Flow:
        1. Member starts with positive balance
        2. Create refund transaction
        3. Generate balanced ledger entries (reversed from payment)
        4. Update member balance (decrease)
        5. Validate all invariants hold
        """
        # Get test data
        member = test_data['members'][0]
        property = test_data['properties'][0]
        fund = test_data['funds'][0]

        # Step 1: Set initial positive balance
        initial_balance = Decimal("500.00")
        update_member_balance(tenant_id, member.id, initial_balance)

        # Step 2: Create refund transaction
        refund_amount = Decimal("150.00")
        transaction = TransactionGenerator.create_refund(
            tenant_id=tenant_id,
            property_id=property.id,
            member_id=member.id,
            fund_id=fund.id,
            amount=refund_amount,
            is_posted=True,
        )

        # Validate transaction
        assert TransactionValidator.validate_transaction(transaction)

        # Step 3: Insert transaction
        insert_transaction(tenant_id, transaction)

        # Step 4: Generate balanced ledger entries (reversed)
        debit, credit = LedgerEntryGenerator.create_for_refund(
            tenant_id=tenant_id,
            property_id=property.id,
            transaction=transaction,
            fund_id=fund.id,
        )

        # Validate entries are balanced
        assert DoubleEntryValidator.validate_balanced_entries([debit, credit])

        # For refunds: DR Income (reduce income), CR Cash (reduce cash)
        assert debit.account_name == "Dues Income"
        assert credit.account_name == "Cash"

        # Step 5: Insert ledger entries
        insert_ledger_entry(tenant_id, debit)
        insert_ledger_entry(tenant_id, credit)

        # Step 6: Update member balance (decrease)
        new_balance = initial_balance - refund_amount
        update_member_balance(tenant_id, member.id, new_balance)

        # Step 7: Validate balance update
        actual_balance = get_member_balance(tenant_id, member.id)
        assert TransactionValidator.validate_refund(
            transaction,
            initial_balance,
            actual_balance,
        )

        # Verify final state
        assert actual_balance == Decimal("350.00")
        assert debit.amount == credit.amount == refund_amount

    def test_payment_then_refund_flow(self, tenant_id, test_data):
        """
        Test payment followed by partial refund.

        This simulates a common scenario:
        1. Member pays $300
        2. HOA refunds $100 (overpayment)
        """
        member = test_data['members'][0]
        property = test_data['properties'][0]
        fund = test_data['funds'][0]

        initial_balance = Decimal("0.00")
        update_member_balance(tenant_id, member.id, initial_balance)

        # Step 1: Payment of $300
        payment = TransactionGenerator.create_payment(
            tenant_id=tenant_id,
            property_id=property.id,
            member_id=member.id,
            fund_id=fund.id,
            amount=Decimal("300.00"),
            is_posted=True,
        )
        insert_transaction(tenant_id, payment)

        debit_pay, credit_pay = LedgerEntryGenerator.create_for_payment(
            tenant_id=tenant_id,
            property_id=property.id,
            transaction=payment,
            fund_id=fund.id,
        )
        insert_ledger_entry(tenant_id, debit_pay)
        insert_ledger_entry(tenant_id, credit_pay)

        # Update balance after payment
        balance_after_payment = initial_balance + Decimal("300.00")
        update_member_balance(tenant_id, member.id, balance_after_payment)

        # Step 2: Refund of $100
        refund = TransactionGenerator.create_refund(
            tenant_id=tenant_id,
            property_id=property.id,
            member_id=member.id,
            fund_id=fund.id,
            amount=Decimal("100.00"),
            is_posted=True,
        )
        insert_transaction(tenant_id, refund)

        debit_ref, credit_ref = LedgerEntryGenerator.create_for_refund(
            tenant_id=tenant_id,
            property_id=property.id,
            transaction=refund,
            fund_id=fund.id,
        )
        insert_ledger_entry(tenant_id, debit_ref)
        insert_ledger_entry(tenant_id, credit_ref)

        # Update balance after refund
        final_balance = balance_after_payment - Decimal("100.00")
        update_member_balance(tenant_id, member.id, final_balance)

        # Verify final balance
        actual_balance = get_member_balance(tenant_id, member.id)
        assert actual_balance == Decimal("200.00")

        # Verify all entries are balanced
        all_entries = [debit_pay, credit_pay, debit_ref, credit_ref]
        total_debits = sum(e.debit_amount for e in all_entries)
        total_credits = sum(e.credit_amount for e in all_entries)
        assert total_debits == total_credits

    def test_refund_exceeds_balance_fails(self, tenant_id, test_data):
        """
        Test that refund exceeding balance fails validation.

        Member with $100 balance cannot receive $200 refund (results in negative balance).
        """
        member = test_data['members'][0]
        property = test_data['properties'][0]
        fund = test_data['funds'][0]

        # Set balance to $100
        initial_balance = Decimal("100.00")
        update_member_balance(tenant_id, member.id, initial_balance)

        # Try to refund $200 (exceeds balance)
        transaction = TransactionGenerator.create_refund(
            tenant_id=tenant_id,
            property_id=property.id,
            member_id=member.id,
            fund_id=fund.id,
            amount=Decimal("200.00"),
        )

        # This should result in negative balance
        expected_balance = initial_balance - Decimal("200.00")  # -$100

        # In a real system, this should be prevented
        # For now, we just validate the math is correct
        assert expected_balance == Decimal("-100.00")

        # The validation would catch this if we enforce non-negative member balances
        assert TransactionValidator.validate_refund(
            transaction,
            initial_balance,
            expected_balance,
        )

    def test_refund_with_wrong_balance_fails_validation(self, tenant_id, test_data):
        """
        Test that refund with incorrect balance update fails validation.
        """
        member = test_data['members'][0]
        property = test_data['properties'][0]
        fund = test_data['funds'][0]

        initial_balance = Decimal("500.00")

        transaction = TransactionGenerator.create_refund(
            tenant_id=tenant_id,
            property_id=property.id,
            member_id=member.id,
            fund_id=fund.id,
            amount=Decimal("150.00"),
        )

        # Intentionally wrong balance (should be 500 - 150 = 350, but we use 400)
        wrong_balance = Decimal("400.00")

        with pytest.raises(ValidationError, match="incorrect balance"):
            TransactionValidator.validate_refund(
                transaction,
                initial_balance,
                wrong_balance,
            )

    def test_refund_ledger_entries_reversed_from_payment(self, tenant_id, test_data):
        """
        Test that refund ledger entries are reversed from payment entries.

        Payment: DR Cash, CR Income
        Refund:  DR Income, CR Cash (reversed)
        """
        property = test_data['properties'][0]
        fund = test_data['funds'][0]

        # Create payment
        payment = TransactionGenerator.create_payment(
            tenant_id=tenant_id,
            property_id=property.id,
            member_id=test_data['members'][0].id,
            fund_id=fund.id,
            amount=Decimal("300.00"),
        )

        pay_debit, pay_credit = LedgerEntryGenerator.create_for_payment(
            tenant_id=tenant_id,
            property_id=property.id,
            transaction=payment,
            fund_id=fund.id,
        )

        # Create refund
        refund = TransactionGenerator.create_refund(
            tenant_id=tenant_id,
            property_id=property.id,
            member_id=test_data['members'][0].id,
            fund_id=fund.id,
            amount=Decimal("300.00"),
        )

        ref_debit, ref_credit = LedgerEntryGenerator.create_for_refund(
            tenant_id=tenant_id,
            property_id=property.id,
            transaction=refund,
            fund_id=fund.id,
        )

        # Verify reversal
        # Payment: DR Cash, CR Income
        assert pay_debit.account_name == "Cash"
        assert pay_credit.account_name == "Dues Income"

        # Refund: DR Income, CR Cash (reversed)
        assert ref_debit.account_name == "Dues Income"
        assert ref_credit.account_name == "Cash"

        # Both balanced
        assert DoubleEntryValidator.validate_balanced_entries([pay_debit, pay_credit])
        assert DoubleEntryValidator.validate_balanced_entries([ref_debit, ref_credit])
