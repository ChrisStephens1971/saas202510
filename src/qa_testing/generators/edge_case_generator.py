"""
Edge case generators for testing boundary conditions.

These generators create test scenarios for edge cases that commonly cause bugs:
- Timezone transitions
- Leap years (Feb 29)
- Fiscal year boundaries
- Month-end/year-end dates
- Retroactive corrections
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from faker import Faker

from qa_testing.models import Transaction, TransactionType

fake = Faker()


class EdgeCaseGenerator:
    """
    Generator for edge case test scenarios.

    Usage:
        # Generate leap year date
        leap_date = EdgeCaseGenerator.leap_year_date(year=2024)

        # Generate fiscal year boundary transaction
        transaction = EdgeCaseGenerator.fiscal_year_boundary_transaction(
            property_id=property.id,
            fiscal_year_start_month=7,  # July
        )
    """

    @staticmethod
    def leap_year_date(year: Optional[int] = None) -> date:
        """
        Generate February 29 date for a leap year.

        Args:
            year: Leap year (must be divisible by 4, with century rules)
                 Defaults to 2024

        Returns:
            Date object for Feb 29 of leap year
        """
        if year is None:
            # Use a recent leap year
            year = 2024

        # Validate it's a leap year
        if not EdgeCaseGenerator.is_leap_year(year):
            # Find next leap year
            while not EdgeCaseGenerator.is_leap_year(year):
                year += 1

        return date(year, 2, 29)

    @staticmethod
    def is_leap_year(year: int) -> bool:
        """
        Check if a year is a leap year.

        Rules:
        - Divisible by 4: leap year
        - BUT divisible by 100: not a leap year
        - BUT divisible by 400: leap year

        Args:
            year: Year to check

        Returns:
            True if leap year
        """
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

    @staticmethod
    def month_end_date(year: int, month: int) -> date:
        """
        Generate the last day of a month.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Last day of the month
        """
        # Get first day of next month, then subtract 1 day
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)

        return next_month - timedelta(days=1)

    @staticmethod
    def year_end_date(year: int) -> date:
        """
        Generate December 31 for a year.

        Args:
            year: Year

        Returns:
            Dec 31 of that year
        """
        return date(year, 12, 31)

    @staticmethod
    def fiscal_year_boundary_date(
        year: int,
        fiscal_year_start_month: int,
        is_start: bool = True
    ) -> date:
        """
        Generate fiscal year start or end date.

        Args:
            year: Calendar year
            fiscal_year_start_month: Month fiscal year starts (1-12)
            is_start: True for start date, False for end date

        Returns:
            Fiscal year boundary date
        """
        if is_start:
            # First day of fiscal year
            return date(year, fiscal_year_start_month, 1)
        else:
            # Last day of fiscal year (day before next fiscal year starts)
            if fiscal_year_start_month == 1:
                # Fiscal year = calendar year
                return date(year, 12, 31)
            else:
                # Last day of month before next fiscal year
                next_fy_month = fiscal_year_start_month
                next_fy_year = year + 1

                # Get last day of previous month
                first_day_next_fy = date(next_fy_year, next_fy_month, 1)
                last_day_current_fy = first_day_next_fy - timedelta(days=1)

                return last_day_current_fy

    @staticmethod
    def fiscal_year_boundary_transaction(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        fiscal_year_start_month: int = 1,
        year: int = 2024,
        amount: Optional[Decimal] = None,
        is_year_start: bool = True,
    ) -> Transaction:
        """
        Generate transaction on fiscal year boundary.

        Args:
            tenant_id: Tenant ID
            property_id: Property ID
            fiscal_year_start_month: Month fiscal year starts
            year: Year
            amount: Transaction amount
            is_year_start: True for start of fiscal year, False for end

        Returns:
            Transaction on fiscal year boundary
        """
        from qa_testing.generators.transaction_generator import TransactionGenerator

        transaction_date = EdgeCaseGenerator.fiscal_year_boundary_date(
            year,
            fiscal_year_start_month,
            is_start=is_year_start,
        )

        amount = amount or Decimal("300.00")

        return TransactionGenerator.create(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_type=TransactionType.DUES_PAYMENT,
            amount=amount,
            transaction_date=transaction_date,
            is_posted=True,
        )

    @staticmethod
    def retroactive_correction_pair(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        original_date: date,
        correction_date: date,
        amount: Decimal,
    ) -> tuple[Transaction, Transaction]:
        """
        Generate pair of transactions for retroactive correction.

        Corrections are done via reversing entries:
        1. Original transaction (in the past)
        2. Reversing transaction (correction, dated later)

        Args:
            tenant_id: Tenant ID
            property_id: Property ID
            original_date: Date of original transaction
            correction_date: Date of correction (must be after original)
            amount: Amount to correct

        Returns:
            Tuple of (original_transaction, reversing_transaction)
        """
        from qa_testing.generators.transaction_generator import TransactionGenerator

        if correction_date <= original_date:
            raise ValueError("Correction date must be after original date")

        # Original transaction (mistake)
        original = TransactionGenerator.create(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_type=TransactionType.DUES_PAYMENT,
            amount=amount,
            transaction_date=original_date,
            is_posted=True,
        )

        # Reversing transaction (correction)
        reversing = TransactionGenerator.create(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_type=TransactionType.ADJUSTMENT,
            amount=amount,
            transaction_date=correction_date,
            is_posted=True,
        )

        return (original, reversing)

    @staticmethod
    def partial_payment_scenario(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        amount_due: Decimal,
        amount_paid: Decimal,
    ) -> Transaction:
        """
        Generate partial payment transaction.

        Args:
            tenant_id: Tenant ID
            property_id: Property ID
            amount_due: Total amount due
            amount_paid: Amount actually paid (less than due)

        Returns:
            Partial payment transaction
        """
        from qa_testing.generators.transaction_generator import TransactionGenerator

        if amount_paid >= amount_due:
            raise ValueError("Partial payment must be less than amount due")

        return TransactionGenerator.create(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_type=TransactionType.DUES_PAYMENT,
            amount=amount_paid,
            description=f"Partial payment (${amount_paid} of ${amount_due} due)",
            is_posted=True,
        )

    @staticmethod
    def overpayment_scenario(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        amount_due: Decimal,
        amount_paid: Decimal,
    ) -> Transaction:
        """
        Generate overpayment transaction.

        Args:
            tenant_id: Tenant ID
            property_id: Property ID
            amount_due: Total amount due
            amount_paid: Amount actually paid (more than due)

        Returns:
            Overpayment transaction
        """
        from qa_testing.generators.transaction_generator import TransactionGenerator

        if amount_paid <= amount_due:
            raise ValueError("Overpayment must be greater than amount due")

        overpayment = amount_paid - amount_due

        return TransactionGenerator.create(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_type=TransactionType.DUES_PAYMENT,
            amount=amount_paid,
            description=f"Overpayment (${amount_paid}, ${overpayment} credit)",
            is_posted=True,
        )

    @staticmethod
    def date_range_transactions(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        start_date: date,
        end_date: date,
        num_transactions: int = 10,
    ) -> list[Transaction]:
        """
        Generate transactions across a date range.

        Useful for testing date queries and point-in-time reconstruction.

        Args:
            tenant_id: Tenant ID
            property_id: Property ID
            start_date: Start of range
            end_date: End of range
            num_transactions: Number of transactions to generate

        Returns:
            List of transactions spread across date range
        """
        from qa_testing.generators.transaction_generator import TransactionGenerator

        transactions = []
        date_range = (end_date - start_date).days

        for i in range(num_transactions):
            # Spread transactions evenly across range
            days_offset = int((date_range * i) / num_transactions)
            transaction_date = start_date + timedelta(days=days_offset)

            transaction = TransactionGenerator.create(
                tenant_id=tenant_id,
                property_id=property_id,
                transaction_date=transaction_date,
                is_posted=True,
            )
            transactions.append(transaction)

        return transactions
