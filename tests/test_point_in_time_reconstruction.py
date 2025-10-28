"""
Point-in-time reconstruction tests.

These tests verify that financial state can be accurately reconstructed
at any historical date using immutable ledger entries.

CRITICAL REQUIREMENT: Auditors must be able to see exact financial state
at any historical date for compliance and dispute resolution.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from qa_testing.generators import (
    FundGenerator,
    LedgerEntryGenerator,
    MemberGenerator,
    PropertyGenerator,
    TransactionGenerator,
)
from qa_testing.models import LedgerEntry, Transaction, TransactionType
from qa_testing.utils import (
    BalanceHistory,
    FundBalanceSnapshot,
    MemberBalanceSnapshot,
    PointInTimeReconstructor,
    PropertyFinancialSnapshot,
    TransactionSummary,
)


class TestMemberBalanceReconstruction:
    """Tests for member balance reconstruction at specific dates."""

    def test_reconstruct_member_with_no_transactions(self):
        """Test reconstructing member balance with no transactions."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        snapshot = PointInTimeReconstructor.reconstruct_member_balance(
            tenant_id=property.tenant_id,
            member_id=member.id,
            as_of_date=date.today(),
            transactions=[],
        )

        # No transactions = zero balance
        assert snapshot.total_owed == Decimal("0.00")
        assert snapshot.total_paid == Decimal("0.00")
        assert snapshot.current_balance == Decimal("0.00")
        assert snapshot.num_transactions == 0

    def test_reconstruct_member_with_payment(self):
        """Test reconstructing member balance after payment."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        # Create payment transaction
        payment = Transaction(
            tenant_id=property.tenant_id,
            property_id=property.id,
            member_id=member.id,
            transaction_type=TransactionType.DUES_PAYMENT,
            description="March 2024 dues payment",
            transaction_date=date(2024, 3, 1),
            amount=Decimal("300.00"),
            is_posted=True,
        )

        snapshot = PointInTimeReconstructor.reconstruct_member_balance(
            tenant_id=property.tenant_id,
            member_id=member.id,
            as_of_date=date(2024, 3, 31),
            transactions=[payment],
        )

        # Payment increases total_paid
        assert snapshot.total_paid == Decimal("300.00")
        assert snapshot.total_owed == Decimal("0.00")
        assert snapshot.current_balance == Decimal("300.00")
        assert snapshot.num_transactions == 1

    def test_reconstruct_member_with_charge_and_payment(self):
        """Test reconstructing member balance with charge and payment."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        # Create late fee charge
        late_fee = Transaction(
            tenant_id=property.tenant_id,
            property_id=property.id,
            member_id=member.id,
            transaction_type=TransactionType.LATE_FEE,
            description="Late fee",
            transaction_date=date(2024, 3, 15),
            amount=Decimal("25.00"),
            is_posted=True,
        )

        # Create payment
        payment = Transaction(
            tenant_id=property.tenant_id,
            property_id=property.id,
            member_id=member.id,
            transaction_type=TransactionType.DUES_PAYMENT,
            description="March 2024 dues payment",
            transaction_date=date(2024, 3, 20),
            amount=Decimal("300.00"),
            is_posted=True,
        )

        snapshot = PointInTimeReconstructor.reconstruct_member_balance(
            tenant_id=property.tenant_id,
            member_id=member.id,
            as_of_date=date(2024, 3, 31),
            transactions=[late_fee, payment],
        )

        # Late fee increases owed, payment increases paid
        assert snapshot.total_owed == Decimal("25.00")
        assert snapshot.total_paid == Decimal("300.00")
        assert snapshot.current_balance == Decimal("275.00")
        assert snapshot.num_transactions == 2

    def test_reconstruct_at_different_dates(self):
        """Test reconstructing balance at different historical dates."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        # Create transactions over time
        transactions = [
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="January payment",
                transaction_date=date(2024, 1, 1),
                amount=Decimal("300.00"),
                is_posted=True,
            ),
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="February payment",
                transaction_date=date(2024, 2, 1),
                amount=Decimal("300.00"),
                is_posted=True,
            ),
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="March payment",
                transaction_date=date(2024, 3, 1),
                amount=Decimal("300.00"),
                is_posted=True,
            ),
        ]

        # Reconstruct at January 31 (1 payment)
        snapshot_jan = PointInTimeReconstructor.reconstruct_member_balance(
            tenant_id=property.tenant_id,
            member_id=member.id,
            as_of_date=date(2024, 1, 31),
            transactions=transactions,
        )
        assert snapshot_jan.total_paid == Decimal("300.00")
        assert snapshot_jan.num_transactions == 1

        # Reconstruct at February 28 (2 payments)
        snapshot_feb = PointInTimeReconstructor.reconstruct_member_balance(
            tenant_id=property.tenant_id,
            member_id=member.id,
            as_of_date=date(2024, 2, 28),
            transactions=transactions,
        )
        assert snapshot_feb.total_paid == Decimal("600.00")
        assert snapshot_feb.num_transactions == 2

        # Reconstruct at March 31 (3 payments)
        snapshot_mar = PointInTimeReconstructor.reconstruct_member_balance(
            tenant_id=property.tenant_id,
            member_id=member.id,
            as_of_date=date(2024, 3, 31),
            transactions=transactions,
        )
        assert snapshot_mar.total_paid == Decimal("900.00")
        assert snapshot_mar.num_transactions == 3

    def test_void_transactions_excluded(self):
        """Test that void transactions are excluded from reconstruction."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        # Create payment and void it
        payment = Transaction(
            tenant_id=property.tenant_id,
            property_id=property.id,
            member_id=member.id,
            transaction_type=TransactionType.DUES_PAYMENT,
            description="Payment",
            transaction_date=date(2024, 3, 1),
            amount=Decimal("300.00"),
            is_posted=True,
            is_void=True,  # VOID
        )

        snapshot = PointInTimeReconstructor.reconstruct_member_balance(
            tenant_id=property.tenant_id,
            member_id=member.id,
            as_of_date=date(2024, 3, 31),
            transactions=[payment],
        )

        # Void transaction should be excluded
        assert snapshot.total_paid == Decimal("0.00")
        assert snapshot.num_transactions == 0


class TestFundBalanceReconstruction:
    """Tests for fund balance reconstruction using double-entry."""

    def test_reconstruct_fund_with_no_entries(self):
        """Test reconstructing fund balance with no ledger entries."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        snapshot = PointInTimeReconstructor.reconstruct_fund_balance(
            tenant_id=property.tenant_id,
            fund_id=fund.id,
            as_of_date=date.today(),
            ledger_entries=[],
        )

        # No entries = zero balance
        assert snapshot.total_debits == Decimal("0.00")
        assert snapshot.total_credits == Decimal("0.00")
        assert snapshot.current_balance == Decimal("0.00")
        assert snapshot.num_debit_entries == 0
        assert snapshot.num_credit_entries == 0

    def test_reconstruct_fund_with_credit_entry(self):
        """Test fund balance with credit entry (increases balance)."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        # Credit entry (member payment increases fund balance)
        credit_entry = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=property.tenant_id,  # Dummy transaction ID
            entry_date=date(2024, 3, 1),
            description="Member payment",
            amount=Decimal("300.00"),
            is_debit=False,  # CREDIT
            account_code="2000",
            account_name="Member Deposits",
        )

        snapshot = PointInTimeReconstructor.reconstruct_fund_balance(
            tenant_id=property.tenant_id,
            fund_id=fund.id,
            as_of_date=date(2024, 3, 31),
            ledger_entries=[credit_entry],
        )

        # Credit increases balance
        assert snapshot.total_credits == Decimal("300.00")
        assert snapshot.total_debits == Decimal("0.00")
        assert snapshot.current_balance == Decimal("300.00")
        assert snapshot.num_credit_entries == 1

    def test_reconstruct_fund_with_debit_entry(self):
        """Test fund balance with debit entry (decreases balance)."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        # Debit entry (expense payment decreases fund balance)
        debit_entry = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=property.tenant_id,
            entry_date=date(2024, 3, 1),
            description="Vendor payment",
            amount=Decimal("500.00"),
            is_debit=True,  # DEBIT
            account_code="6000",
            account_name="Maintenance Expense",
        )

        snapshot = PointInTimeReconstructor.reconstruct_fund_balance(
            tenant_id=property.tenant_id,
            fund_id=fund.id,
            as_of_date=date(2024, 3, 31),
            ledger_entries=[debit_entry],
        )

        # Debit decreases balance
        assert snapshot.total_debits == Decimal("500.00")
        assert snapshot.total_credits == Decimal("0.00")
        assert snapshot.current_balance == Decimal("-500.00")
        assert snapshot.num_debit_entries == 1

    def test_reconstruct_fund_with_multiple_entries(self):
        """Test fund balance with multiple debits and credits."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        entries = [
            # Credit: Member payment
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 3, 1),
                description="Member payment 1",
                amount=Decimal("300.00"),
                is_debit=False,
                account_code="2000",
                account_name="Member Deposits",
            ),
            # Credit: Member payment
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 3, 5),
                description="Member payment 2",
                amount=Decimal("300.00"),
                is_debit=False,
                account_code="2000",
                account_name="Member Deposits",
            ),
            # Debit: Vendor payment
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 3, 10),
                description="Vendor payment",
                amount=Decimal("150.00"),
                is_debit=True,
                account_code="6000",
                account_name="Maintenance Expense",
            ),
        ]

        snapshot = PointInTimeReconstructor.reconstruct_fund_balance(
            tenant_id=property.tenant_id,
            fund_id=fund.id,
            as_of_date=date(2024, 3, 31),
            ledger_entries=entries,
        )

        # Balance = Credits - Debits = 600 - 150 = 450
        assert snapshot.total_credits == Decimal("600.00")
        assert snapshot.total_debits == Decimal("150.00")
        assert snapshot.current_balance == Decimal("450.00")
        assert snapshot.num_credit_entries == 2
        assert snapshot.num_debit_entries == 1

    def test_reconstruct_fund_at_different_dates(self):
        """Test reconstructing fund balance at different dates."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        entries = [
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 1, 1),
                description="January payment",
                amount=Decimal("300.00"),
                is_debit=False,
                account_code="2000",
                account_name="Member Deposits",
            ),
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 2, 1),
                description="February payment",
                amount=Decimal("300.00"),
                is_debit=False,
                account_code="2000",
                account_name="Member Deposits",
            ),
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 3, 1),
                description="March payment",
                amount=Decimal("300.00"),
                is_debit=False,
                account_code="2000",
                account_name="Member Deposits",
            ),
        ]

        # January 31: $300
        snapshot_jan = PointInTimeReconstructor.reconstruct_fund_balance(
            tenant_id=property.tenant_id,
            fund_id=fund.id,
            as_of_date=date(2024, 1, 31),
            ledger_entries=entries,
        )
        assert snapshot_jan.current_balance == Decimal("300.00")

        # February 28: $600
        snapshot_feb = PointInTimeReconstructor.reconstruct_fund_balance(
            tenant_id=property.tenant_id,
            fund_id=fund.id,
            as_of_date=date(2024, 2, 28),
            ledger_entries=entries,
        )
        assert snapshot_feb.current_balance == Decimal("600.00")

        # March 31: $900
        snapshot_mar = PointInTimeReconstructor.reconstruct_fund_balance(
            tenant_id=property.tenant_id,
            fund_id=fund.id,
            as_of_date=date(2024, 3, 31),
            ledger_entries=entries,
        )
        assert snapshot_mar.current_balance == Decimal("900.00")


class TestTransactionHistory:
    """Tests for transaction history queries."""

    def test_get_transaction_history_empty(self):
        """Test getting transaction history with no transactions."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        history = PointInTimeReconstructor.get_transaction_history(
            member_id=member.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            transactions=[],
        )

        assert len(history) == 0

    def test_get_transaction_history_filters_by_date(self):
        """Test that transaction history filters by date range."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        transactions = [
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="Before range",
                transaction_date=date(2023, 12, 1),
                amount=Decimal("300.00"),
                is_posted=True,
            ),
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="In range",
                transaction_date=date(2024, 1, 15),
                amount=Decimal("300.00"),
                is_posted=True,
            ),
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="After range",
                transaction_date=date(2024, 2, 1),
                amount=Decimal("300.00"),
                is_posted=True,
            ),
        ]

        history = PointInTimeReconstructor.get_transaction_history(
            member_id=member.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            transactions=transactions,
        )

        # Only the transaction in January
        assert len(history) == 1
        assert history[0].description == "In range"

    def test_get_transaction_history_sorted_by_date(self):
        """Test that transaction history is sorted by date."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        # Create transactions out of order
        transactions = [
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="Third",
                transaction_date=date(2024, 1, 15),
                amount=Decimal("300.00"),
                is_posted=True,
            ),
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="First",
                transaction_date=date(2024, 1, 1),
                amount=Decimal("300.00"),
                is_posted=True,
            ),
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="Second",
                transaction_date=date(2024, 1, 10),
                amount=Decimal("300.00"),
                is_posted=True,
            ),
        ]

        history = PointInTimeReconstructor.get_transaction_history(
            member_id=member.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            transactions=transactions,
        )

        # Should be sorted oldest to newest
        assert len(history) == 3
        assert history[0].description == "First"
        assert history[1].description == "Second"
        assert history[2].description == "Third"

    def test_get_transaction_history_excludes_void(self):
        """Test that transaction history excludes void transactions."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        transactions = [
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="Valid",
                transaction_date=date(2024, 1, 1),
                amount=Decimal("300.00"),
                is_posted=True,
                is_void=False,
            ),
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="Void",
                transaction_date=date(2024, 1, 15),
                amount=Decimal("300.00"),
                is_posted=True,
                is_void=True,
            ),
        ]

        history = PointInTimeReconstructor.get_transaction_history(
            member_id=member.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            transactions=transactions,
        )

        # Only the valid transaction
        assert len(history) == 1
        assert history[0].description == "Valid"


class TestFundBalanceHistory:
    """Tests for fund balance history tracking."""

    def test_get_fund_balance_history_with_no_entries(self):
        """Test balance history with no ledger entries."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        history = PointInTimeReconstructor.get_fund_balance_history(
            tenant_id=property.tenant_id,
            fund_id=fund.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            ledger_entries=[],
        )

        assert history.opening_balance == Decimal("0.00")
        assert history.closing_balance == Decimal("0.00")
        assert history.net_change == Decimal("0.00")
        assert len(history.balance_points) == 0

    def test_get_fund_balance_history_tracks_changes(self):
        """Test that balance history tracks changes over time."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        entries = [
            # Day 1: +$300
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 1, 1),
                description="Payment 1",
                amount=Decimal("300.00"),
                is_debit=False,
                account_code="2000",
                account_name="Member Deposits",
            ),
            # Day 15: +$300
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 1, 15),
                description="Payment 2",
                amount=Decimal("300.00"),
                is_debit=False,
                account_code="2000",
                account_name="Member Deposits",
            ),
            # Day 20: -$150
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 1, 20),
                description="Expense",
                amount=Decimal("150.00"),
                is_debit=True,
                account_code="6000",
                account_name="Maintenance",
            ),
        ]

        history = PointInTimeReconstructor.get_fund_balance_history(
            tenant_id=property.tenant_id,
            fund_id=fund.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            ledger_entries=entries,
        )

        # Check balance points
        assert len(history.balance_points) == 3
        assert history.balance_points[date(2024, 1, 1)] == Decimal("300.00")
        assert history.balance_points[date(2024, 1, 15)] == Decimal("600.00")
        assert history.balance_points[date(2024, 1, 20)] == Decimal("450.00")

        # Check opening and closing
        assert history.opening_balance == Decimal("0.00")
        assert history.closing_balance == Decimal("450.00")
        assert history.net_change == Decimal("450.00")

    def test_get_fund_balance_history_net_change(self):
        """Test that net change is correctly calculated."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        # Create entry before range to establish opening balance
        entries_before = [
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund.id,
                transaction_id=property.tenant_id,
                entry_date=date(2023, 12, 1),
                description="Prior balance",
                amount=Decimal("1000.00"),
                is_debit=False,
                account_code="2000",
                account_name="Member Deposits",
            ),
        ]

        # Entries in range
        entries_in_range = [
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 1, 15),
                description="New payment",
                amount=Decimal("300.00"),
                is_debit=False,
                account_code="2000",
                account_name="Member Deposits",
            ),
        ]

        all_entries = entries_before + entries_in_range

        history = PointInTimeReconstructor.get_fund_balance_history(
            tenant_id=property.tenant_id,
            fund_id=fund.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            ledger_entries=all_entries,
        )

        # Opening: $1000 (from December)
        # Closing: $1300 (December + January)
        # Net change: $300
        assert history.opening_balance == Decimal("1000.00")
        assert history.closing_balance == Decimal("1300.00")
        assert history.net_change == Decimal("300.00")


class TestPropertySnapshot:
    """Tests for property-wide financial snapshots."""

    def test_reconstruct_property_snapshot_empty(self):
        """Test property snapshot with no data."""
        property = PropertyGenerator.create()

        snapshot = PointInTimeReconstructor.reconstruct_property_snapshot(
            tenant_id=property.tenant_id,
            property_id=property.id,
            as_of_date=date.today(),
            transactions=[],
            ledger_entries=[],
            member_ids=[],
            fund_ids=[],
        )

        assert snapshot.total_fund_balance == Decimal("0.00")
        assert snapshot.total_member_receivables == Decimal("0.00")
        assert snapshot.num_active_members == 0
        assert snapshot.num_funds == 0

    def test_reconstruct_property_snapshot_with_data(self):
        """Test property snapshot with funds and members."""
        property = PropertyGenerator.create()

        # Create funds
        fund1 = FundGenerator.create(property_id=property.id)
        fund2 = FundGenerator.create(property_id=property.id)

        # Create members
        member1 = MemberGenerator.create(property_id=property.id)
        member2 = MemberGenerator.create(property_id=property.id)

        # Create ledger entries for funds
        ledger_entries = [
            # Fund 1: $500
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund1.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 1, 1),
                description="Fund 1 deposit",
                amount=Decimal("500.00"),
                is_debit=False,
                account_code="2000",
                account_name="Deposits",
            ),
            # Fund 2: $1000
            LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund2.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 1, 1),
                description="Fund 2 deposit",
                amount=Decimal("1000.00"),
                is_debit=False,
                account_code="2000",
                account_name="Deposits",
            ),
        ]

        # Create transactions for members (member owes money)
        transactions = [
            # Member 1: owes $25 (late fee)
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member1.id,
                transaction_type=TransactionType.LATE_FEE,
                description="Late fee",
                transaction_date=date(2024, 1, 1),
                amount=Decimal("25.00"),
                is_posted=True,
            ),
        ]

        snapshot = PointInTimeReconstructor.reconstruct_property_snapshot(
            tenant_id=property.tenant_id,
            property_id=property.id,
            as_of_date=date(2024, 1, 31),
            transactions=transactions,
            ledger_entries=ledger_entries,
            member_ids=[member1.id, member2.id],
            fund_ids=[fund1.id, fund2.id],
        )

        # Total fund balance: $500 + $1000 = $1500
        assert snapshot.total_fund_balance == Decimal("1500.00")

        # Member 1 owes $25 (negative balance)
        assert snapshot.total_member_receivables == Decimal("25.00")

        # Counts
        assert snapshot.num_active_members == 2
        assert snapshot.num_funds == 2


class TestTransactionSummary:
    """Tests for transaction summary reporting."""

    def test_get_transaction_summary_empty(self):
        """Test transaction summary with no transactions."""
        property = PropertyGenerator.create()

        summary = PointInTimeReconstructor.get_transaction_summary(
            tenant_id=property.tenant_id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            transactions=[],
        )

        assert summary.total_transactions == 0
        assert summary.num_income == 0
        assert summary.num_expenses == 0
        assert summary.total_income == Decimal("0.00")
        assert summary.total_expenses == Decimal("0.00")
        assert summary.net_income == Decimal("0.00")

    def test_get_transaction_summary_categorizes_income(self):
        """Test that summary correctly categorizes income."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        transactions = [
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="Dues",
                transaction_date=date(2024, 1, 1),
                amount=Decimal("300.00"),
                is_posted=True,
            ),
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.LATE_FEE,
                description="Late fee",
                transaction_date=date(2024, 1, 15),
                amount=Decimal("25.00"),
                is_posted=True,
            ),
        ]

        summary = PointInTimeReconstructor.get_transaction_summary(
            tenant_id=property.tenant_id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            transactions=transactions,
        )

        assert summary.num_income == 2
        assert summary.total_income == Decimal("325.00")
        assert summary.num_expenses == 0
        assert summary.net_income == Decimal("325.00")

    def test_get_transaction_summary_categorizes_expenses(self):
        """Test that summary correctly categorizes expenses."""
        property = PropertyGenerator.create()

        transactions = [
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                transaction_type=TransactionType.VENDOR_PAYMENT,
                description="Vendor",
                transaction_date=date(2024, 1, 1),
                amount=Decimal("500.00"),
                is_posted=True,
            ),
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                transaction_type=TransactionType.UTILITY,
                description="Utility",
                transaction_date=date(2024, 1, 15),
                amount=Decimal("150.00"),
                is_posted=True,
            ),
        ]

        summary = PointInTimeReconstructor.get_transaction_summary(
            tenant_id=property.tenant_id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            transactions=transactions,
        )

        assert summary.num_expenses == 2
        assert summary.total_expenses == Decimal("650.00")
        assert summary.num_income == 0
        assert summary.net_income == Decimal("-650.00")

    def test_get_transaction_summary_net_income(self):
        """Test that net income is correctly calculated."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        transactions = [
            # Income: $300
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                member_id=member.id,
                transaction_type=TransactionType.DUES_PAYMENT,
                description="Dues",
                transaction_date=date(2024, 1, 1),
                amount=Decimal("300.00"),
                is_posted=True,
            ),
            # Expense: $150
            Transaction(
                tenant_id=property.tenant_id,
                property_id=property.id,
                transaction_type=TransactionType.MAINTENANCE,
                description="Maintenance",
                transaction_date=date(2024, 1, 15),
                amount=Decimal("150.00"),
                is_posted=True,
            ),
        ]

        summary = PointInTimeReconstructor.get_transaction_summary(
            tenant_id=property.tenant_id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            transactions=transactions,
        )

        # Net income = $300 - $150 = $150
        assert summary.total_income == Decimal("300.00")
        assert summary.total_expenses == Decimal("150.00")
        assert summary.net_income == Decimal("150.00")


class TestReconstructionAccuracy:
    """Tests for reconstruction accuracy and edge cases."""

    @pytest.mark.property
    @given(
        st.lists(
            st.decimals(
                min_value=Decimal("0.01"),
                max_value=Decimal("1000.00"),
                places=2,
            ),
            min_size=1,
            max_size=100,
        )
    )
    def test_reconstruction_uses_decimal_precision(self, amounts):
        """Property: Reconstruction always uses exact Decimal precision."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        # Create ledger entries with given amounts
        entries = []
        for i, amount in enumerate(amounts):
            # Ensure exactly 2 decimal places
            amount = amount.quantize(Decimal("0.01"))

            entry = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
                fund_id=fund.id,
                transaction_id=property.tenant_id,
                entry_date=date(2024, 1, 1) + timedelta(days=i),
                description=f"Entry {i}",
                amount=amount,
                is_debit=False,
                account_code="2000",
                account_name="Deposits",
            )
            entries.append(entry)

        snapshot = PointInTimeReconstructor.reconstruct_fund_balance(
            tenant_id=property.tenant_id,
            fund_id=fund.id,
            as_of_date=date(2024, 12, 31),
            ledger_entries=entries,
        )

        # All balances should have exactly 2 decimal places
        assert snapshot.total_credits.as_tuple().exponent == -2
        assert snapshot.current_balance.as_tuple().exponent == -2

        # Should not be float
        assert isinstance(snapshot.current_balance, Decimal)
        assert not isinstance(snapshot.current_balance, float)

    def test_reconstruction_handles_retroactive_corrections(self):
        """Test that reconstruction handles retroactive corrections."""
        property = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property.id)

        # Original entry
        original_entry = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=property.tenant_id,
            entry_date=date(2024, 1, 1),
            description="Original payment",
            amount=Decimal("300.00"),
            is_debit=False,
            account_code="2000",
            account_name="Deposits",
        )

        # Reversing entry (added later, but dated same day)
        reversing_entry = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=property.tenant_id,
            entry_date=date(2024, 1, 1),
            description="Reverse original payment",
            amount=Decimal("300.00"),
            is_debit=True,  # Opposite side
            account_code="2000",
            account_name="Deposits",
            is_reversing=True,
            reverses_entry_id=original_entry.id,
        )

        # Corrected entry
        corrected_entry = LedgerEntry(
            tenant_id=property.tenant_id,
            property_id=property.id,
            fund_id=fund.id,
            transaction_id=property.tenant_id,
            entry_date=date(2024, 1, 1),
            description="Corrected payment",
            amount=Decimal("350.00"),  # Correct amount
            is_debit=False,
            account_code="2000",
            account_name="Deposits",
        )

        # Reconstruct with all entries
        snapshot = PointInTimeReconstructor.reconstruct_fund_balance(
            tenant_id=property.tenant_id,
            fund_id=fund.id,
            as_of_date=date(2024, 1, 31),
            ledger_entries=[original_entry, reversing_entry, corrected_entry],
        )

        # Balance should reflect corrected amount
        # Credits: $300 (original) + $350 (corrected) = $650
        # Debits: $300 (reversing) = $300
        # Balance: $650 - $300 = $350
        assert snapshot.current_balance == Decimal("350.00")

    def test_reconstruction_date_boundary_conditions(self):
        """Test reconstruction at date boundaries (midnight, leap year)."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        # Transaction on Feb 29, 2024 (leap year)
        leap_day_txn = Transaction(
            tenant_id=property.tenant_id,
            property_id=property.id,
            member_id=member.id,
            transaction_type=TransactionType.DUES_PAYMENT,
            description="Leap day payment",
            transaction_date=date(2024, 2, 29),
            amount=Decimal("300.00"),
            is_posted=True,
        )

        # Reconstruct on leap day
        snapshot = PointInTimeReconstructor.reconstruct_member_balance(
            tenant_id=property.tenant_id,
            member_id=member.id,
            as_of_date=date(2024, 2, 29),
            transactions=[leap_day_txn],
        )

        assert snapshot.total_paid == Decimal("300.00")
        assert snapshot.as_of_date == date(2024, 2, 29)
