"""
Point-in-time reconstruction utilities for financial data.

These utilities enable reconstruction of financial state at any historical date,
which is critical for:
- Audit compliance (show state at audit date)
- Dispute resolution (prove balance at specific date)
- Regulatory reporting (historical snapshots)
- Retroactive corrections (recalculate after adjustments)

CRITICAL: All reconstruction uses immutable ledger entries.
- Never UPDATE or DELETE ledger entries
- State is always reconstructable from INSERT-only audit trail
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from qa_testing.models import BaseTestModel, LedgerEntry, MoneyAmount, Transaction


class MemberBalanceSnapshot(BaseTestModel):
    """
    Snapshot of member balance at a specific date.

    This represents the financial state of a member as of a specific date,
    reconstructed from immutable transaction history.
    """

    # Multi-tenant isolation
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenant isolation")

    member_id: UUID = Field(..., description="Member ID")
    as_of_date: date = Field(..., description="Date of snapshot")

    # Balance components
    total_owed: MoneyAmount = Field(
        ...,
        description="Total amount owed by member as of date"
    )
    total_paid: MoneyAmount = Field(
        ...,
        description="Total amount paid by member as of date"
    )
    current_balance: MoneyAmount = Field(
        ...,
        description="Current balance (total_paid - total_owed)"
    )

    # Transaction counts
    num_transactions: int = Field(
        default=0,
        ge=0,
        description="Number of transactions up to date"
    )

    # Metadata
    reconstruction_timestamp: Optional[date] = Field(
        None,
        description="When this snapshot was reconstructed"
    )


class FundBalanceSnapshot(BaseTestModel):
    """
    Snapshot of fund balance at a specific date.

    This represents the financial state of a fund as of a specific date,
    reconstructed from immutable ledger entries using double-entry bookkeeping.
    """

    # Multi-tenant isolation
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenant isolation")

    fund_id: UUID = Field(..., description="Fund ID")
    as_of_date: date = Field(..., description="Date of snapshot")

    # Balance components (double-entry)
    total_debits: MoneyAmount = Field(
        ...,
        description="Sum of all debit entries as of date"
    )
    total_credits: MoneyAmount = Field(
        ...,
        description="Sum of all credit entries as of date"
    )
    current_balance: MoneyAmount = Field(
        ...,
        description="Fund balance (credits - debits for liability accounts)"
    )

    # Entry counts
    num_debit_entries: int = Field(default=0, ge=0)
    num_credit_entries: int = Field(default=0, ge=0)

    # Metadata
    reconstruction_timestamp: Optional[date] = Field(
        None,
        description="When this snapshot was reconstructed"
    )


class PropertyFinancialSnapshot(BaseTestModel):
    """
    Complete financial snapshot for a property at a specific date.

    This provides a comprehensive view of all financial data for a property,
    useful for:
    - Monthly/quarterly financial statements
    - Audit reports
    - Board presentations
    - Regulatory filings
    """

    # Multi-tenant isolation
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenant isolation")

    property_id: UUID = Field(..., description="Property ID")
    as_of_date: date = Field(..., description="Date of snapshot")

    # Fund balances
    fund_balances: dict[UUID, MoneyAmount] = Field(
        default_factory=dict,
        description="Fund ID -> current balance mapping"
    )
    total_fund_balance: MoneyAmount = Field(
        Decimal("0.00"),
        description="Sum of all fund balances"
    )

    # Member balances
    member_balances: dict[UUID, MoneyAmount] = Field(
        default_factory=dict,
        description="Member ID -> current balance mapping"
    )
    total_member_receivables: MoneyAmount = Field(
        Decimal("0.00"),
        description="Sum of all negative member balances (amounts owed)"
    )

    # Counts
    num_active_members: int = Field(default=0, ge=0)
    num_funds: int = Field(default=0, ge=0)

    # Metadata
    reconstruction_timestamp: Optional[date] = Field(
        None,
        description="When this snapshot was reconstructed"
    )


class BalanceHistory(BaseTestModel):
    """
    Balance history showing changes over time.

    This tracks how a balance changed over a date range,
    useful for:
    - Trend analysis
    - Variance reporting
    - Cash flow analysis
    """

    # Multi-tenant isolation
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenant isolation")

    start_date: date = Field(..., description="Start of date range")
    end_date: date = Field(..., description="End of date range")

    # Balance points (date -> balance)
    balance_points: dict[date, MoneyAmount] = Field(
        default_factory=dict,
        description="Date -> balance mapping showing changes"
    )

    # Opening and closing
    opening_balance: MoneyAmount = Field(
        ...,
        description="Balance at start_date"
    )
    closing_balance: MoneyAmount = Field(
        ...,
        description="Balance at end_date"
    )
    net_change: MoneyAmount = Field(
        ...,
        description="Change in balance (closing - opening)"
    )

    # Metadata
    num_transactions: int = Field(
        default=0,
        ge=0,
        description="Number of transactions in range"
    )


class TransactionSummary(BaseTestModel):
    """
    Summary of transactions for a date range.

    Useful for:
    - Activity reports
    - Revenue analysis
    - Expense tracking
    """

    # Multi-tenant isolation
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenant isolation")

    start_date: date = Field(..., description="Start of date range")
    end_date: date = Field(..., description="End of date range")

    # Transaction counts
    total_transactions: int = Field(default=0, ge=0)
    num_income: int = Field(default=0, ge=0, description="Income transactions")
    num_expenses: int = Field(default=0, ge=0, description="Expense transactions")

    # Amounts
    total_income: MoneyAmount = Field(Decimal("0.00"))
    total_expenses: MoneyAmount = Field(Decimal("0.00"))
    net_income: MoneyAmount = Field(
        Decimal("0.00"),
        description="Net income (total_income - total_expenses)"
    )


class PointInTimeReconstructor:
    """
    Utility class for reconstructing financial state at any historical date.

    CRITICAL PRINCIPLES:
    1. All reconstruction uses immutable ledger entries
    2. State is always reconstructable from INSERT-only audit trail
    3. No queries that modify data (SELECT only)
    4. Use DATE for all date comparisons (not TIMESTAMP)
    5. Use Decimal for all money calculations

    Usage:
        # Reconstruct member balance at specific date
        balance = PointInTimeReconstructor.reconstruct_member_balance(
            member_id=member.id,
            as_of_date=date(2024, 12, 31),
            transactions=all_transactions
        )

        # Get fund balance history
        history = PointInTimeReconstructor.get_fund_balance_history(
            fund_id=fund.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            ledger_entries=all_entries
        )
    """

    @staticmethod
    def reconstruct_member_balance(
        tenant_id: UUID,
        member_id: UUID,
        as_of_date: date,
        transactions: list[Transaction],
    ) -> MemberBalanceSnapshot:
        """
        Reconstruct member balance at a specific date.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            member_id: Member to reconstruct balance for
            as_of_date: Date to reconstruct balance at
            transactions: All transactions (will filter by date)

        Returns:
            MemberBalanceSnapshot with balance as of date

        Example:
            >>> snapshot = PointInTimeReconstructor.reconstruct_member_balance(
            ...     tenant_id=property.tenant_id,
            ...     member_id=member.id,
            ...     as_of_date=date(2024, 12, 31),
            ...     transactions=all_transactions
            ... )
            >>> print(f"Balance: ${snapshot.current_balance}")
            Balance: $-300.00  # Member owes $300
        """
        # Filter transactions for this member up to date
        relevant_txns = [
            txn for txn in transactions
            if txn.member_id == member_id
            and txn.transaction_date <= as_of_date
            and not txn.is_void
        ]

        # Calculate balances
        total_owed = Decimal("0.00")
        total_paid = Decimal("0.00")

        for txn in relevant_txns:
            # Income transactions (dues, assessments, fees) increase amount owed
            if txn.transaction_type.value in [
                "dues_payment",
                "assessment_payment",
                "late_fee",
                "transfer_fee",
                "other_income",
            ]:
                # If it's a payment from member, it's money paid
                if "payment" in txn.transaction_type.value:
                    total_paid += txn.amount
                else:
                    # If it's a charge (late fee), it's money owed
                    total_owed += txn.amount

            # Refunds decrease amount paid
            elif txn.transaction_type.value == "refund":
                total_paid -= txn.amount

            # Adjustments can go either way
            elif txn.transaction_type.value == "adjustment":
                # Positive adjustments increase owed, negative decrease
                if txn.amount > 0:
                    total_owed += txn.amount
                else:
                    total_owed -= abs(txn.amount)

        # Ensure 2 decimal places
        total_owed = total_owed.quantize(Decimal("0.01"))
        total_paid = total_paid.quantize(Decimal("0.01"))
        current_balance = (total_paid - total_owed).quantize(Decimal("0.01"))

        return MemberBalanceSnapshot(
            tenant_id=tenant_id,
            member_id=member_id,
            as_of_date=as_of_date,
            total_owed=total_owed,
            total_paid=total_paid,
            current_balance=current_balance,
            num_transactions=len(relevant_txns),
            reconstruction_timestamp=date.today(),
        )

    @staticmethod
    def reconstruct_fund_balance(
        tenant_id: UUID,
        fund_id: UUID,
        as_of_date: date,
        ledger_entries: list[LedgerEntry],
    ) -> FundBalanceSnapshot:
        """
        Reconstruct fund balance at a specific date using double-entry bookkeeping.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            fund_id: Fund to reconstruct balance for
            as_of_date: Date to reconstruct balance at
            ledger_entries: All ledger entries (will filter by date)

        Returns:
            FundBalanceSnapshot with balance as of date

        Example:
            >>> snapshot = PointInTimeReconstructor.reconstruct_fund_balance(
            ...     tenant_id=property.tenant_id,
            ...     fund_id=fund.id,
            ...     as_of_date=date(2024, 12, 31),
            ...     ledger_entries=all_entries
            ... )
            >>> print(f"Fund balance: ${snapshot.current_balance}")
            Fund balance: $25000.00
        """
        # Filter entries for this fund up to date
        relevant_entries = [
            entry for entry in ledger_entries
            if entry.fund_id == fund_id
            and entry.entry_date <= as_of_date
        ]

        # Sum debits and credits
        total_debits = Decimal("0.00")
        total_credits = Decimal("0.00")
        num_debit_entries = 0
        num_credit_entries = 0

        for entry in relevant_entries:
            if entry.is_debit:
                total_debits += entry.amount
                num_debit_entries += 1
            else:
                total_credits += entry.amount
                num_credit_entries += 1

        # For HOA funds (liability accounts), credits increase balance
        # Balance = Credits - Debits
        current_balance = (total_credits - total_debits).quantize(Decimal("0.01"))

        return FundBalanceSnapshot(
            tenant_id=tenant_id,
            fund_id=fund_id,
            as_of_date=as_of_date,
            total_debits=total_debits.quantize(Decimal("0.01")),
            total_credits=total_credits.quantize(Decimal("0.01")),
            current_balance=current_balance,
            num_debit_entries=num_debit_entries,
            num_credit_entries=num_credit_entries,
            reconstruction_timestamp=date.today(),
        )

    @staticmethod
    def get_transaction_history(
        member_id: UUID,
        start_date: date,
        end_date: date,
        transactions: list[Transaction],
    ) -> list[Transaction]:
        """
        Get transaction history for a member within date range.

        Args:
            member_id: Member to get history for
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            transactions: All transactions (will filter)

        Returns:
            List of transactions in date range, sorted by date

        Example:
            >>> history = PointInTimeReconstructor.get_transaction_history(
            ...     member_id=member.id,
            ...     start_date=date(2024, 1, 1),
            ...     end_date=date(2024, 12, 31),
            ...     transactions=all_transactions
            ... )
            >>> print(f"Found {len(history)} transactions")
            Found 24 transactions
        """
        # Filter transactions
        relevant = [
            txn for txn in transactions
            if txn.member_id == member_id
            and start_date <= txn.transaction_date <= end_date
            and not txn.is_void
        ]

        # Sort by date (oldest first)
        relevant.sort(key=lambda t: t.transaction_date)

        return relevant

    @staticmethod
    def get_fund_balance_history(
        tenant_id: UUID,
        fund_id: UUID,
        start_date: date,
        end_date: date,
        ledger_entries: list[LedgerEntry],
    ) -> BalanceHistory:
        """
        Get fund balance history showing changes over time.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            fund_id: Fund to get history for
            start_date: Start of date range
            end_date: End of date range
            ledger_entries: All ledger entries (will filter)

        Returns:
            BalanceHistory with balance at each transaction date

        Example:
            >>> history = PointInTimeReconstructor.get_fund_balance_history(
            ...     tenant_id=property.tenant_id,
            ...     fund_id=fund.id,
            ...     start_date=date(2024, 1, 1),
            ...     end_date=date(2024, 12, 31),
            ...     ledger_entries=all_entries
            ... )
            >>> print(f"Changed by ${history.net_change}")
            Changed by $5000.00
        """
        # Get opening balance (balance at start_date - 1 day)
        from datetime import timedelta
        day_before_start = start_date - timedelta(days=1)

        opening_snapshot = PointInTimeReconstructor.reconstruct_fund_balance(
            tenant_id=tenant_id,
            fund_id=fund_id,
            as_of_date=day_before_start,
            ledger_entries=ledger_entries,
        )
        opening_balance = opening_snapshot.current_balance

        # Get closing balance (balance at end_date)
        closing_snapshot = PointInTimeReconstructor.reconstruct_fund_balance(
            tenant_id=tenant_id,
            fund_id=fund_id,
            as_of_date=end_date,
            ledger_entries=ledger_entries,
        )
        closing_balance = closing_snapshot.current_balance

        # Get all entries in range
        relevant_entries = [
            entry for entry in ledger_entries
            if entry.fund_id == fund_id
            and start_date <= entry.entry_date <= end_date
        ]

        # Build balance points (balance at each date with entries)
        balance_points: dict[date, Decimal] = {}

        # Get unique dates
        unique_dates = sorted(set(entry.entry_date for entry in relevant_entries))

        for entry_date in unique_dates:
            snapshot = PointInTimeReconstructor.reconstruct_fund_balance(
                tenant_id=tenant_id,
                fund_id=fund_id,
                as_of_date=entry_date,
                ledger_entries=ledger_entries,
            )
            balance_points[entry_date] = snapshot.current_balance

        # Calculate net change
        net_change = (closing_balance - opening_balance).quantize(Decimal("0.01"))

        return BalanceHistory(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            balance_points=balance_points,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            net_change=net_change,
            num_transactions=len(relevant_entries),
        )

    @staticmethod
    def reconstruct_property_snapshot(
        tenant_id: UUID,
        property_id: UUID,
        as_of_date: date,
        transactions: list[Transaction],
        ledger_entries: list[LedgerEntry],
        member_ids: list[UUID],
        fund_ids: list[UUID],
    ) -> PropertyFinancialSnapshot:
        """
        Reconstruct complete financial snapshot for a property.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            property_id: Property to reconstruct snapshot for
            as_of_date: Date to reconstruct at
            transactions: All transactions
            ledger_entries: All ledger entries
            member_ids: List of member IDs for this property
            fund_ids: List of fund IDs for this property

        Returns:
            PropertyFinancialSnapshot with complete financial state

        Example:
            >>> snapshot = PointInTimeReconstructor.reconstruct_property_snapshot(
            ...     tenant_id=property.tenant_id,
            ...     property_id=property.id,
            ...     as_of_date=date(2024, 12, 31),
            ...     transactions=all_transactions,
            ...     ledger_entries=all_entries,
            ...     member_ids=[m.id for m in members],
            ...     fund_ids=[f.id for f in funds]
            ... )
            >>> print(f"Total funds: ${snapshot.total_fund_balance}")
            Total funds: $50000.00
        """
        # Reconstruct fund balances
        fund_balances: dict[UUID, Decimal] = {}
        for fund_id in fund_ids:
            snapshot = PointInTimeReconstructor.reconstruct_fund_balance(
                tenant_id=tenant_id,
                fund_id=fund_id,
                as_of_date=as_of_date,
                ledger_entries=ledger_entries,
            )
            fund_balances[fund_id] = snapshot.current_balance

        total_fund_balance = sum(fund_balances.values(), Decimal("0.00"))

        # Reconstruct member balances
        member_balances: dict[UUID, Decimal] = {}
        total_member_receivables = Decimal("0.00")

        for member_id in member_ids:
            snapshot = PointInTimeReconstructor.reconstruct_member_balance(
                tenant_id=tenant_id,
                member_id=member_id,
                as_of_date=as_of_date,
                transactions=transactions,
            )
            member_balances[member_id] = snapshot.current_balance

            # Count negative balances (amounts owed)
            if snapshot.current_balance < 0:
                total_member_receivables += abs(snapshot.current_balance)

        return PropertyFinancialSnapshot(
            tenant_id=tenant_id,
            property_id=property_id,
            as_of_date=as_of_date,
            fund_balances=fund_balances,
            total_fund_balance=total_fund_balance.quantize(Decimal("0.01")),
            member_balances=member_balances,
            total_member_receivables=total_member_receivables.quantize(Decimal("0.01")),
            num_active_members=len(member_ids),
            num_funds=len(fund_ids),
            reconstruction_timestamp=date.today(),
        )

    @staticmethod
    def get_transaction_summary(
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        transactions: list[Transaction],
    ) -> TransactionSummary:
        """
        Get summary of transactions for a date range.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            start_date: Start of date range
            end_date: End of date range
            transactions: All transactions (will filter)

        Returns:
            TransactionSummary with counts and totals

        Example:
            >>> summary = PointInTimeReconstructor.get_transaction_summary(
            ...     tenant_id=property.tenant_id,
            ...     start_date=date(2024, 1, 1),
            ...     end_date=date(2024, 12, 31),
            ...     transactions=all_transactions
            ... )
            >>> print(f"Net income: ${summary.net_income}")
            Net income: $12000.00
        """
        # Filter transactions in range
        relevant = [
            txn for txn in transactions
            if start_date <= txn.transaction_date <= end_date
            and not txn.is_void
        ]

        # Categorize and sum
        total_income = Decimal("0.00")
        total_expenses = Decimal("0.00")
        num_income = 0
        num_expenses = 0

        # Income transaction types
        income_types = {
            "dues_payment",
            "assessment_payment",
            "late_fee",
            "transfer_fee",
            "other_income",
        }

        # Expense transaction types
        expense_types = {
            "vendor_payment",
            "utility",
            "maintenance",
            "insurance",
            "management_fee",
            "other_expense",
            "bank_fee",
        }

        for txn in relevant:
            if txn.transaction_type.value in income_types:
                total_income += txn.amount
                num_income += 1
            elif txn.transaction_type.value in expense_types:
                total_expenses += txn.amount
                num_expenses += 1

        net_income = (total_income - total_expenses).quantize(Decimal("0.01"))

        return TransactionSummary(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            total_transactions=len(relevant),
            num_income=num_income,
            num_expenses=num_expenses,
            total_income=total_income.quantize(Decimal("0.01")),
            total_expenses=total_expenses.quantize(Decimal("0.01")),
            net_income=net_income,
        )
