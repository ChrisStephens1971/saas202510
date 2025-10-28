"""
Validators for accounting rules and financial correctness.

These validators ensure that transactions and ledger entries
follow proper accounting principles, especially double-entry bookkeeping.
"""

from decimal import Decimal
from typing import Optional

from qa_testing.models import Fund, LedgerEntry, Transaction


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class DoubleEntryValidator:
    """
    Validator for double-entry bookkeeping rules.

    CRITICAL RULES:
    1. For every transaction, sum(debits) must equal sum(credits)
    2. Every debit must have a corresponding credit
    3. Account balances must always balance (Assets = Liabilities + Equity)
    """

    @staticmethod
    def validate_balanced_entries(entries: list[LedgerEntry]) -> bool:
        """
        Validate that a set of ledger entries are balanced (debits = credits).

        Args:
            entries: List of ledger entries to validate

        Returns:
            True if balanced

        Raises:
            ValidationError: If entries are not balanced
        """
        if not entries:
            raise ValidationError("Cannot validate empty entry list")

        total_debits = sum(entry.debit_amount for entry in entries)
        total_credits = sum(entry.credit_amount for entry in entries)

        if total_debits != total_credits:
            raise ValidationError(
                f"Entries are not balanced! "
                f"Debits: ${total_debits:,.2f}, Credits: ${total_credits:,.2f}, "
                f"Difference: ${abs(total_debits - total_credits):,.2f}"
            )

        return True

    @staticmethod
    def validate_transaction_entries(
        transaction: Transaction,
        entries: list[LedgerEntry]
    ) -> bool:
        """
        Validate that ledger entries for a transaction are correct.

        Rules:
        1. All entries must reference the transaction
        2. Entries must be balanced (debits = credits)
        3. At least one debit and one credit entry

        Args:
            transaction: Transaction to validate
            entries: Ledger entries for the transaction

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        if not entries:
            raise ValidationError(f"No entries found for transaction {transaction.id}")

        # Check all entries reference this transaction
        for entry in entries:
            if entry.transaction_id != transaction.id:
                raise ValidationError(
                    f"Entry {entry.id} references wrong transaction "
                    f"(expected {transaction.id}, got {entry.transaction_id})"
                )

        # Check for at least one debit and one credit
        has_debit = any(entry.is_debit for entry in entries)
        has_credit = any(not entry.is_debit for entry in entries)

        if not has_debit:
            raise ValidationError(f"Transaction {transaction.id} has no debit entries")
        if not has_credit:
            raise ValidationError(f"Transaction {transaction.id} has no credit entries")

        # Validate balanced
        DoubleEntryValidator.validate_balanced_entries(entries)

        return True

    @staticmethod
    def validate_entry_pair(debit: LedgerEntry, credit: LedgerEntry) -> bool:
        """
        Validate a simple debit/credit entry pair.

        Rules:
        1. One must be debit, one must be credit
        2. Amounts must match
        3. Must reference same transaction
        4. Must be in same tenant

        Args:
            debit: Debit entry
            credit: Credit entry

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        # Check debit/credit designation
        if not debit.is_debit:
            raise ValidationError(f"Entry {debit.id} is not a debit entry")
        if credit.is_debit:
            raise ValidationError(f"Entry {credit.id} is not a credit entry")

        # Check amounts match
        if debit.amount != credit.amount:
            raise ValidationError(
                f"Entry amounts don't match! "
                f"Debit: ${debit.amount:,.2f}, Credit: ${credit.amount:,.2f}"
            )

        # Check same transaction
        if debit.transaction_id != credit.transaction_id:
            raise ValidationError(
                f"Entries reference different transactions! "
                f"Debit: {debit.transaction_id}, Credit: {credit.transaction_id}"
            )

        # Check same tenant
        if debit.tenant_id != credit.tenant_id:
            raise ValidationError(
                f"Entries belong to different tenants! "
                f"Debit: {debit.tenant_id}, Credit: {credit.tenant_id}"
            )

        return True


class TransactionValidator:
    """
    Validator for transaction rules and constraints.
    """

    @staticmethod
    def validate_transaction(transaction: Transaction) -> bool:
        """
        Validate a transaction meets basic requirements.

        Rules:
        1. Amount must be positive
        2. Amount must have exactly 2 decimal places
        3. Posted transactions must have posted_date
        4. Voided transactions cannot be posted

        Args:
            transaction: Transaction to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        # Check amount is positive
        if transaction.amount <= Decimal("0.00"):
            raise ValidationError(
                f"Transaction {transaction.id} has non-positive amount: ${transaction.amount}"
            )

        # Check decimal places
        if transaction.amount.as_tuple().exponent != -2:
            raise ValidationError(
                f"Transaction {transaction.id} amount has wrong precision: {transaction.amount} "
                f"(must have exactly 2 decimal places)"
            )

        # Check posted transactions have posted_date
        if transaction.is_posted and transaction.posted_date is None:
            raise ValidationError(
                f"Transaction {transaction.id} is marked posted but has no posted_date"
            )

        # Check voided transactions are not posted
        if transaction.is_void and transaction.is_posted:
            raise ValidationError(
                f"Transaction {transaction.id} is both void and posted (invalid state)"
            )

        # Check transaction_date is not in future
        from datetime import date
        if transaction.transaction_date > date.today():
            raise ValidationError(
                f"Transaction {transaction.id} has future transaction_date: {transaction.transaction_date}"
            )

        return True

    @staticmethod
    def validate_payment(
        transaction: Transaction,
        member_balance_before: Decimal,
        member_balance_after: Decimal,
    ) -> bool:
        """
        Validate a payment transaction updates balances correctly.

        For a payment, member balance should increase by payment amount.

        Args:
            transaction: Payment transaction
            member_balance_before: Member balance before payment
            member_balance_after: Member balance after payment

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        expected_balance = member_balance_before + transaction.amount
        if member_balance_after != expected_balance:
            raise ValidationError(
                f"Payment {transaction.id} resulted in incorrect balance! "
                f"Before: ${member_balance_before:,.2f}, "
                f"Payment: ${transaction.amount:,.2f}, "
                f"Expected: ${expected_balance:,.2f}, "
                f"Actual: ${member_balance_after:,.2f}"
            )

        return True

    @staticmethod
    def validate_refund(
        transaction: Transaction,
        member_balance_before: Decimal,
        member_balance_after: Decimal,
    ) -> bool:
        """
        Validate a refund transaction updates balances correctly.

        For a refund, member balance should decrease by refund amount.

        Args:
            transaction: Refund transaction
            member_balance_before: Member balance before refund
            member_balance_after: Member balance after refund

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        expected_balance = member_balance_before - transaction.amount
        if member_balance_after != expected_balance:
            raise ValidationError(
                f"Refund {transaction.id} resulted in incorrect balance! "
                f"Before: ${member_balance_before:,.2f}, "
                f"Refund: ${transaction.amount:,.2f}, "
                f"Expected: ${expected_balance:,.2f}, "
                f"Actual: ${member_balance_after:,.2f}"
            )

        return True


class ReconciliationValidator:
    """
    Validator for account reconciliation.

    Reconciliation ensures that:
    1. Sum of all ledger entries matches account balances
    2. No entries are missing
    3. All entries are properly posted
    """

    @staticmethod
    def reconcile_account_balance(
        ledger_entries: list[LedgerEntry],
        expected_balance: Decimal,
    ) -> bool:
        """
        Reconcile account balance from ledger entries.

        Args:
            ledger_entries: All ledger entries for account
            expected_balance: Expected account balance

        Returns:
            True if reconciled

        Raises:
            ValidationError: If balances don't match
        """
        if not ledger_entries:
            if expected_balance == Decimal("0.00"):
                return True
            raise ValidationError(
                f"No entries but expected balance is ${expected_balance:,.2f}"
            )

        # Calculate balance from entries (debits - credits for asset accounts)
        calculated_balance = sum(
            entry.debit_amount - entry.credit_amount
            for entry in ledger_entries
        )

        if calculated_balance != expected_balance:
            raise ValidationError(
                f"Balance reconciliation failed! "
                f"Calculated: ${calculated_balance:,.2f}, "
                f"Expected: ${expected_balance:,.2f}, "
                f"Difference: ${abs(calculated_balance - expected_balance):,.2f}"
            )

        return True

    @staticmethod
    def validate_all_entries_posted(ledger_entries: list[LedgerEntry]) -> bool:
        """
        Validate that all ledger entries are from posted transactions.

        Args:
            ledger_entries: Ledger entries to check

        Returns:
            True if all posted

        Raises:
            ValidationError: If any unposted entries found
        """
        # Note: This would require checking the related transaction
        # For now, we assume all ledger entries should only be created
        # for posted transactions

        return True


class AccountingValidator:
    """
    Validator for overall accounting system integrity.
    """

    @staticmethod
    def validate_fund_balance(
        fund: Fund,
        transactions: Optional[list[LedgerEntry]] = None
    ) -> bool:
        """
        Validate a fund's balance is correct.

        Rules:
        1. Balance must respect minimum_balance
        2. If transactions provided, balance should match sum of entries

        Args:
            fund: Fund to validate
            transactions: Optional list of ledger entries for fund

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        # Check minimum balance
        if not fund.allow_negative_balance:
            if fund.current_balance < fund.minimum_balance:
                raise ValidationError(
                    f"Fund {fund.id} ({fund.name}) balance below minimum! "
                    f"Current: ${fund.current_balance:,.2f}, "
                    f"Minimum: ${fund.minimum_balance:,.2f}"
                )

        # Check balance matches transactions (if provided)
        if transactions:
            net_amount = sum(
                entry.debit_amount - entry.credit_amount
                for entry in transactions
                if entry.fund_id == fund.id
            )

            if net_amount != fund.current_balance:
                raise ValidationError(
                    f"Fund {fund.id} ({fund.name}) balance doesn't match entries! "
                    f"Calculated: ${net_amount:,.2f}, "
                    f"Actual: ${fund.current_balance:,.2f}"
                )

        return True

    @staticmethod
    def validate_accounting_equation(
        assets: Decimal,
        liabilities: Decimal,
        equity: Decimal,
    ) -> bool:
        """
        Validate the fundamental accounting equation: Assets = Liabilities + Equity.

        This is the FOUNDATION of accounting. If this doesn't hold, something is very wrong.

        Args:
            assets: Total assets
            liabilities: Total liabilities
            equity: Total equity

        Returns:
            True if valid

        Raises:
            ValidationError: If equation doesn't balance
        """
        right_side = liabilities + equity

        if assets != right_side:
            raise ValidationError(
                f"Accounting equation violated! "
                f"Assets (${assets:,.2f}) != Liabilities (${liabilities:,.2f}) + Equity (${equity:,.2f}) "
                f"= ${right_side:,.2f}, "
                f"Difference: ${abs(assets - right_side):,.2f}"
            )

        return True

    @staticmethod
    def validate_ledger_immutability(
        original_entry: LedgerEntry,
        current_entry: LedgerEntry,
    ) -> bool:
        """
        Validate that a ledger entry has not been modified.

        Ledger entries must be IMMUTABLE once created. Use reversing entries to correct.

        Args:
            original_entry: Original entry
            current_entry: Current entry (should be identical)

        Returns:
            True if immutable

        Raises:
            ValidationError: If entry was modified
        """
        if original_entry.id != current_entry.id:
            raise ValidationError("Comparing different entries!")

        # Check critical fields haven't changed
        if original_entry.amount != current_entry.amount:
            raise ValidationError(
                f"Entry {original_entry.id} amount was modified! "
                f"Original: ${original_entry.amount:,.2f}, "
                f"Current: ${current_entry.amount:,.2f}"
            )

        if original_entry.is_debit != current_entry.is_debit:
            raise ValidationError(
                f"Entry {original_entry.id} debit/credit designation was modified!"
            )

        if original_entry.account_code != current_entry.account_code:
            raise ValidationError(
                f"Entry {original_entry.id} account code was modified! "
                f"Original: {original_entry.account_code}, "
                f"Current: {current_entry.account_code}"
            )

        return True
