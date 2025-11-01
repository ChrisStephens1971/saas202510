"""Delinquency data generator for testing delinquency scenarios."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from qa_testing.models import Delinquency
from qa_testing.generators.ar_collections_generator import DelinquencyStatus


class DelinquencyGenerator:
    """
    Generator for creating Delinquency test data.

    Usage:
        # Create a delinquency record
        delinquency = DelinquencyGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            days_delinquent=45,
            total_amount_due=Decimal("500.00"),
            status=DelinquencyStatus.LATE_30,
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: UUID,
        member_id: UUID,
        days_delinquent: int,
        total_amount_due: Decimal,
        status: Optional[str] = None,
        due_date: Optional[date] = None,
        last_payment_date: Optional[date] = None,
    ) -> Delinquency:
        """
        Create a Delinquency record.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            member_id: Member with delinquent balance
            days_delinquent: Number of days account is past due
            total_amount_due: Total amount currently due
            status: Delinquency status (if not provided, calculated from days_delinquent)
            due_date: Original due date (defaults to days_delinquent ago)
            last_payment_date: Date of last payment received

        Returns:
            Delinquency instance with realistic data
        """
        # Calculate status from days_delinquent if not provided
        if status is None:
            if days_delinquent < 30:
                status = DelinquencyStatus.CURRENT.value
            elif days_delinquent < 60:
                status = DelinquencyStatus.LATE_30.value
            elif days_delinquent < 90:
                status = DelinquencyStatus.LATE_60.value
            elif days_delinquent < 120:
                status = DelinquencyStatus.LATE_90.value
            elif days_delinquent < 180:
                status = DelinquencyStatus.COLLECTIONS.value
            else:
                status = DelinquencyStatus.LEGAL.value
        elif hasattr(status, 'value'):
            # Handle enum values
            status = status.value

        # Calculate due date if not provided
        if due_date is None:
            due_date = date.today() - timedelta(days=days_delinquent)

        return Delinquency(
            tenant_id=tenant_id,
            member_id=member_id,
            days_delinquent=days_delinquent,
            total_amount_due=total_amount_due,
            status=status,
            due_date=due_date,
            last_payment_date=last_payment_date,
        )

    @staticmethod
    def create_batch(
        *,
        tenant_id: UUID,
        member_ids: list[UUID],
        days_delinquent_range: tuple[int, int] = (30, 90),
        total_amount_range: tuple[Decimal, Decimal] = (Decimal("100.00"), Decimal("1000.00")),
    ) -> list[Delinquency]:
        """
        Create multiple delinquency records with varying delinquency levels.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            member_ids: List of member IDs to create delinquencies for
            days_delinquent_range: Range of days delinquent (min, max)
            total_amount_range: Range of total amounts due (min, max)

        Returns:
            List of Delinquency instances
        """
        from faker import Faker
        fake = Faker()

        delinquencies = []
        min_days, max_days = days_delinquent_range
        min_amount, max_amount = total_amount_range

        for member_id in member_ids:
            days = fake.random_int(min=min_days, max=max_days)
            amount = Decimal(str(fake.random_int(
                min=int(min_amount),
                max=int(max_amount)
            ))).quantize(Decimal("0.01"))

            delinquency = DelinquencyGenerator.create(
                tenant_id=tenant_id,
                member_id=member_id,
                days_delinquent=days,
                total_amount_due=amount,
            )
            delinquencies.append(delinquency)

        return delinquencies
