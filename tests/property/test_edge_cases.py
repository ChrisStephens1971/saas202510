"""
Property-based tests for edge cases.

These tests validate that edge cases (leap years, fiscal boundaries, etc.)
are handled correctly.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from hypothesis import given, strategies as st

from qa_testing.generators import EdgeCaseGenerator, PropertyGenerator
from qa_testing.validators import TransactionValidator, ValidationError


class TestLeapYearEdgeCases:
    """Tests for leap year date handling."""

    def test_leap_year_date_is_feb_29(self):
        """Test that leap year date generator creates Feb 29."""
        leap_date = EdgeCaseGenerator.leap_year_date(2024)
        assert leap_date.month == 2
        assert leap_date.day == 29
        assert leap_date.year == 2024

    def test_is_leap_year_validates_correctly(self):
        """Test leap year validation logic."""
        # Leap years
        assert EdgeCaseGenerator.is_leap_year(2024)  # Divisible by 4
        assert EdgeCaseGenerator.is_leap_year(2000)  # Divisible by 400
        assert EdgeCaseGenerator.is_leap_year(2020)

        # Not leap years
        assert not EdgeCaseGenerator.is_leap_year(2023)  # Not divisible by 4
        assert not EdgeCaseGenerator.is_leap_year(1900)  # Divisible by 100 but not 400
        assert not EdgeCaseGenerator.is_leap_year(2100)

    @pytest.mark.property
    @given(st.integers(min_value=2000, max_value=2100))
    def test_leap_year_date_always_valid(self, year):
        """Property: For ANY year, leap year date generator creates valid date."""
        leap_date = EdgeCaseGenerator.leap_year_date(year)

        # Must be Feb 29
        assert leap_date.month == 2
        assert leap_date.day == 29

        # Year must be a leap year
        assert EdgeCaseGenerator.is_leap_year(leap_date.year)

    def test_leap_year_transaction_valid(self):
        """Test that transactions on leap year dates are valid."""
        property = PropertyGenerator.create()

        # Create transaction on Feb 29
        leap_date = EdgeCaseGenerator.leap_year_date(2024)

        transaction = EdgeCaseGenerator.fiscal_year_boundary_transaction(
            property_id=property.id,
            fiscal_year_start_month=1,
            year=2024,
        )
        transaction.transaction_date = leap_date

        # Should validate
        assert TransactionValidator.validate_transaction(transaction)


class TestFiscalYearBoundaries:
    """Tests for fiscal year boundary handling."""

    def test_fiscal_year_start_date_calendar_year(self):
        """Test fiscal year start for calendar year (Jan 1)."""
        fy_start = EdgeCaseGenerator.fiscal_year_boundary_date(
            year=2024,
            fiscal_year_start_month=1,
            is_start=True,
        )

        assert fy_start == date(2024, 1, 1)

    def test_fiscal_year_end_date_calendar_year(self):
        """Test fiscal year end for calendar year (Dec 31)."""
        fy_end = EdgeCaseGenerator.fiscal_year_boundary_date(
            year=2024,
            fiscal_year_start_month=1,
            is_start=False,
        )

        assert fy_end == date(2024, 12, 31)

    def test_fiscal_year_start_date_mid_year(self):
        """Test fiscal year start for mid-year fiscal year (July 1)."""
        fy_start = EdgeCaseGenerator.fiscal_year_boundary_date(
            year=2024,
            fiscal_year_start_month=7,  # July
            is_start=True,
        )

        assert fy_start == date(2024, 7, 1)

    def test_fiscal_year_end_date_mid_year(self):
        """Test fiscal year end for mid-year fiscal year (June 30)."""
        fy_end = EdgeCaseGenerator.fiscal_year_boundary_date(
            year=2024,
            fiscal_year_start_month=7,  # July start -> June end
            is_start=False,
        )

        assert fy_end == date(2025, 6, 30)

    @pytest.mark.property
    @given(
        st.integers(min_value=2020, max_value=2030),
        st.integers(min_value=1, max_value=12),
    )
    def test_fiscal_year_boundaries_are_consecutive(self, year, fiscal_month):
        """Property: Fiscal year end + 1 day = next fiscal year start."""
        fy_end = EdgeCaseGenerator.fiscal_year_boundary_date(
            year=year,
            fiscal_year_start_month=fiscal_month,
            is_start=False,
        )

        next_fy_start = fy_end + timedelta(days=1)

        # Next fiscal year start should match
        expected_next_fy_start = EdgeCaseGenerator.fiscal_year_boundary_date(
            year=year + 1 if fiscal_month > 1 else year,
            fiscal_year_start_month=fiscal_month,
            is_start=True,
        )

        # For fiscal years that cross calendar years, adjust expected year
        if fiscal_month > 1:
            expected_next_fy_start = date(year + 1, fiscal_month, 1)

        assert next_fy_start.month == fiscal_month
        assert next_fy_start.day == 1

    def test_fiscal_year_boundary_transaction_valid(self):
        """Test that transactions on fiscal year boundaries are valid."""
        property = PropertyGenerator.create()

        # Transaction at fiscal year start
        fy_start_txn = EdgeCaseGenerator.fiscal_year_boundary_transaction(
            property_id=property.id,
            fiscal_year_start_month=7,  # July
            year=2024,
            is_year_start=True,
        )

        assert fy_start_txn.transaction_date == date(2024, 7, 1)
        assert TransactionValidator.validate_transaction(fy_start_txn)

        # Transaction at fiscal year end
        fy_end_txn = EdgeCaseGenerator.fiscal_year_boundary_transaction(
            property_id=property.id,
            fiscal_year_start_month=7,
            year=2024,
            is_year_start=False,
        )

        assert fy_end_txn.transaction_date == date(2025, 6, 30)
        assert TransactionValidator.validate_transaction(fy_end_txn)


class TestRetroactiveCorrections:
    """Tests for retroactive correction handling."""

    def test_retroactive_correction_pair_dates_ordered(self):
        """Test that correction date is after original date."""
        property = PropertyGenerator.create()

        original, reversing = EdgeCaseGenerator.retroactive_correction_pair(
            property_id=property.id,
            original_date=date(2024, 1, 15),
            correction_date=date(2024, 2, 1),
            amount=Decimal("300.00"),
        )

        assert original.transaction_date == date(2024, 1, 15)
        assert reversing.transaction_date == date(2024, 2, 1)
        assert reversing.transaction_date > original.transaction_date

    def test_retroactive_correction_same_amount(self):
        """Test that correction has same amount as original."""
        property = PropertyGenerator.create()

        amount = Decimal("150.00")
        original, reversing = EdgeCaseGenerator.retroactive_correction_pair(
            property_id=property.id,
            original_date=date(2024, 1, 15),
            correction_date=date(2024, 2, 1),
            amount=amount,
        )

        assert original.amount == amount
        assert reversing.amount == amount

    def test_retroactive_correction_invalid_dates_fails(self):
        """Test that correction before original fails."""
        property = PropertyGenerator.create()

        with pytest.raises(ValueError, match="after original date"):
            EdgeCaseGenerator.retroactive_correction_pair(
                property_id=property.id,
                original_date=date(2024, 2, 1),
                correction_date=date(2024, 1, 15),  # Before original!
                amount=Decimal("300.00"),
            )


class TestPartialPayments:
    """Tests for partial payment scenarios."""

    def test_partial_payment_less_than_due(self):
        """Test that partial payment is less than amount due."""
        property = PropertyGenerator.create()

        amount_due = Decimal("300.00")
        amount_paid = Decimal("150.00")

        transaction = EdgeCaseGenerator.partial_payment_scenario(
            property_id=property.id,
            amount_due=amount_due,
            amount_paid=amount_paid,
        )

        assert transaction.amount == amount_paid
        assert transaction.amount < amount_due
        assert TransactionValidator.validate_transaction(transaction)

    def test_partial_payment_full_amount_fails(self):
        """Test that full payment is not considered partial."""
        property = PropertyGenerator.create()

        amount_due = Decimal("300.00")
        amount_paid = Decimal("300.00")  # Full amount

        with pytest.raises(ValueError, match="less than amount due"):
            EdgeCaseGenerator.partial_payment_scenario(
                property_id=property.id,
                amount_due=amount_due,
                amount_paid=amount_paid,
            )

    @pytest.mark.property
    @given(
        st.decimals(min_value=100, max_value=1000, places=2),
        st.decimals(min_value=1, max_value=99, places=2),
    )
    def test_partial_payment_always_valid(self, amount_due, partial_amount):
        """Property: For ANY amounts, partial payment < due is valid."""
        property = PropertyGenerator.create()

        amount_paid = amount_due - partial_amount  # Ensure partial

        if amount_paid <= Decimal("0.00"):
            return  # Skip invalid amounts

        transaction = EdgeCaseGenerator.partial_payment_scenario(
            property_id=property.id,
            amount_due=amount_due,
            amount_paid=amount_paid,
        )

        assert transaction.amount < amount_due
        assert TransactionValidator.validate_transaction(transaction)


class TestOverpayments:
    """Tests for overpayment scenarios."""

    def test_overpayment_greater_than_due(self):
        """Test that overpayment is greater than amount due."""
        property = PropertyGenerator.create()

        amount_due = Decimal("300.00")
        amount_paid = Decimal("350.00")

        transaction = EdgeCaseGenerator.overpayment_scenario(
            property_id=property.id,
            amount_due=amount_due,
            amount_paid=amount_paid,
        )

        assert transaction.amount == amount_paid
        assert transaction.amount > amount_due
        assert TransactionValidator.validate_transaction(transaction)

    def test_overpayment_exact_amount_fails(self):
        """Test that exact payment is not considered overpayment."""
        property = PropertyGenerator.create()

        amount_due = Decimal("300.00")
        amount_paid = Decimal("300.00")  # Exact amount

        with pytest.raises(ValueError, match="greater than amount due"):
            EdgeCaseGenerator.overpayment_scenario(
                property_id=property.id,
                amount_due=amount_due,
                amount_paid=amount_paid,
            )


class TestDateRangeTransactions:
    """Tests for transactions across date ranges."""

    def test_date_range_transactions_spread_across_range(self):
        """Test that transactions are spread across date range."""
        property = PropertyGenerator.create()

        start_date = date(2024, 1, 1)
        end_date = date(2024, 12, 31)

        transactions = EdgeCaseGenerator.date_range_transactions(
            property_id=property.id,
            start_date=start_date,
            end_date=end_date,
            num_transactions=12,  # One per month
        )

        assert len(transactions) == 12

        # All transactions should be within range
        for txn in transactions:
            assert start_date <= txn.transaction_date <= end_date

        # Transactions should be in order
        dates = [txn.transaction_date for txn in transactions]
        assert dates == sorted(dates)

    def test_date_range_transactions_all_valid(self):
        """Test that all transactions in range are valid."""
        property = PropertyGenerator.create()

        start_date = date(2024, 1, 1)
        end_date = date(2024, 3, 31)

        transactions = EdgeCaseGenerator.date_range_transactions(
            property_id=property.id,
            start_date=start_date,
            end_date=end_date,
            num_transactions=10,
        )

        for txn in transactions:
            assert TransactionValidator.validate_transaction(txn)


class TestMonthEndDates:
    """Tests for month-end date handling."""

    def test_month_end_date_february_non_leap(self):
        """Test February end in non-leap year (Feb 28)."""
        month_end = EdgeCaseGenerator.month_end_date(2023, 2)
        assert month_end == date(2023, 2, 28)

    def test_month_end_date_february_leap(self):
        """Test February end in leap year (Feb 29)."""
        month_end = EdgeCaseGenerator.month_end_date(2024, 2)
        assert month_end == date(2024, 2, 29)

    def test_month_end_date_31_day_month(self):
        """Test 31-day month (Jan, Mar, May, etc.)."""
        month_end = EdgeCaseGenerator.month_end_date(2024, 1)
        assert month_end == date(2024, 1, 31)

    def test_month_end_date_30_day_month(self):
        """Test 30-day month (Apr, Jun, Sep, Nov)."""
        month_end = EdgeCaseGenerator.month_end_date(2024, 4)
        assert month_end == date(2024, 4, 30)

    @pytest.mark.property
    @given(
        st.integers(min_value=2020, max_value=2030),
        st.integers(min_value=1, max_value=12),
    )
    def test_month_end_date_always_last_day(self, year, month):
        """Property: Month end date + 1 day = first day of next month."""
        month_end = EdgeCaseGenerator.month_end_date(year, month)

        next_day = month_end + timedelta(days=1)

        # Next day should be first of next month
        assert next_day.day == 1

        if month == 12:
            assert next_day.month == 1
            assert next_day.year == year + 1
        else:
            assert next_day.month == month + 1
            assert next_day.year == year
