"""Member data generator for realistic HOA member test data."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from faker import Faker

from qa_testing.models import Member, MemberType, PaymentHistory

fake = Faker()


class MemberGenerator:
    """
    Generator for creating realistic Member test data.

    Usage:
        # Create a member with default settings
        member = MemberGenerator.create()

        # Create a member with specific payment history
        late_member = MemberGenerator.create(payment_history=PaymentHistory.FREQUENTLY_LATE)

        # Create multiple members
        members = MemberGenerator.create_batch(50)
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        unit_id: Optional[UUID] = None,
        property_id: Optional[UUID] = None,
        member_type: Optional[MemberType] = None,
        payment_history: Optional[PaymentHistory] = None,
        is_active: bool = True,
        move_in_date: Optional[date] = None,
    ) -> Member:
        """
        Create a single Member with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            unit_id: Associated unit ID (generates one if not provided)
            property_id: Associated property ID (generates one if not provided)
            member_type: Type of member (random if not provided)
            payment_history: Payment behavior pattern (random if not provided)
            is_active: Whether member is active
            move_in_date: Move-in date (random within last 5 years if not provided)

        Returns:
            Member instance with realistic data
        """
        # Generate IDs if not provided
        tenant_id = tenant_id or uuid4()
        unit_id = unit_id or uuid4()
        property_id = property_id or uuid4()

        # Randomize member type if not provided
        if member_type is None:
            # Distribution: 85% owners, 10% tenants, 5% board members
            rand = fake.random.random()
            if rand < 0.85:
                member_type = MemberType.OWNER
            elif rand < 0.95:
                member_type = MemberType.TENANT
            else:
                member_type = MemberType.BOARD_MEMBER

        # Randomize payment history if not provided
        if payment_history is None:
            # Distribution: 70% on time, 20% occasional late, 7% frequently late, 2% delinquent, 1% overpayer
            rand = fake.random.random()
            if rand < 0.70:
                payment_history = PaymentHistory.ON_TIME
            elif rand < 0.90:
                payment_history = PaymentHistory.OCCASIONAL_LATE
            elif rand < 0.97:
                payment_history = PaymentHistory.FREQUENTLY_LATE
            elif rand < 0.99:
                payment_history = PaymentHistory.DELINQUENT
            else:
                payment_history = PaymentHistory.OVERPAYER

        # Generate move-in date (random within last 5 years)
        if move_in_date is None:
            days_ago = fake.random_int(min=30, max=1825)  # 1 month to 5 years
            move_in_date = date.today() - timedelta(days=days_ago)

        # Generate financial data based on payment history
        current_balance, total_paid, total_owed = MemberGenerator._generate_financial_data(
            payment_history, move_in_date
        )

        return Member(
            tenant_id=tenant_id,
            unit_id=unit_id,
            property_id=property_id,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone=fake.phone_number()[:20],  # Truncate to max 20 chars
            member_type=member_type,
            is_active=is_active,
            current_balance=current_balance,
            total_paid=total_paid,
            total_owed=total_owed,
            payment_history=payment_history,
            move_in_date=move_in_date,
            move_out_date=None if is_active else fake.date_between(start_date=move_in_date, end_date=date.today()),
        )

    @staticmethod
    def _generate_financial_data(
        payment_history: PaymentHistory,
        move_in_date: date,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Generate realistic financial data based on payment history.

        Returns:
            Tuple of (current_balance, total_paid, total_owed)
        """
        # Calculate months since move-in
        months_since_move_in = max(1, (date.today() - move_in_date).days // 30)

        # Assume average HOA fee of $300/month
        avg_monthly_fee = Decimal("300.00")
        total_owed = avg_monthly_fee * months_since_move_in

        # Generate payment behavior
        if payment_history == PaymentHistory.ON_TIME:
            # Pays on time, slight overpayment possible
            total_paid = total_owed + Decimal(str(fake.random.uniform(0, 50)))
            current_balance = total_paid - total_owed

        elif payment_history == PaymentHistory.OCCASIONAL_LATE:
            # Occasionally late, sometimes pays with late fee
            late_fees = Decimal(str(fake.random.uniform(25, 100)))
            total_paid = total_owed + late_fees - Decimal(str(fake.random.uniform(0, 100)))
            current_balance = total_paid - (total_owed + late_fees)

        elif payment_history == PaymentHistory.FREQUENTLY_LATE:
            # Frequently late, owes 1-3 months
            months_behind = fake.random.randint(1, 3)
            late_fees = Decimal(str(fake.random.uniform(50, 300)))
            total_paid = total_owed - (avg_monthly_fee * months_behind)
            current_balance = total_paid - (total_owed + late_fees)

        elif payment_history == PaymentHistory.DELINQUENT:
            # Seriously delinquent, owes 3-12 months
            months_behind = fake.random.randint(3, 12)
            late_fees = Decimal(str(fake.random.uniform(200, 1000)))
            total_paid = total_owed - (avg_monthly_fee * months_behind)
            current_balance = total_paid - (total_owed + late_fees)

        elif payment_history == PaymentHistory.OVERPAYER:
            # Prepays, has positive balance
            overpayment = avg_monthly_fee * Decimal(str(fake.random.uniform(1, 6)))
            total_paid = total_owed + overpayment
            current_balance = total_paid - total_owed

        else:
            # Default: break even
            total_paid = total_owed
            current_balance = Decimal("0.00")

        # Round to 2 decimal places
        return (
            current_balance.quantize(Decimal("0.01")),
            total_paid.quantize(Decimal("0.01")),
            total_owed.quantize(Decimal("0.01")),
        )

    @staticmethod
    def create_with_balance(
        *,
        tenant_id: UUID,
        balance: Decimal,
        property_id: Optional[UUID] = None,
        unit_id: Optional[UUID] = None,
        **kwargs
    ) -> Member:
        """
        Create a Member with a specific balance.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            balance: Specific balance for the member (can be negative for debt)
            property_id: Associated property ID (generates one if not provided)
            unit_id: Associated unit ID (generates one if not provided)
            **kwargs: Additional arguments passed to create()

        Returns:
            Member instance with specified balance
        """
        # Create member with default settings
        member = MemberGenerator.create(
            tenant_id=tenant_id,
            unit_id=unit_id,
            property_id=property_id,
            **kwargs
        )

        # Override the current_balance with the specified balance
        member.current_balance = balance.quantize(Decimal("0.01"))

        # If balance is negative (debt), set payment history accordingly
        if balance < Decimal("0.00"):
            member.payment_history = PaymentHistory.DELINQUENT
            # Adjust total_owed to reflect the debt
            member.total_owed = member.total_paid - balance
        elif balance > Decimal("0.00"):
            # Positive balance means they overpaid
            member.payment_history = PaymentHistory.OVERPAYER
            member.total_paid = member.total_owed + balance

        return member

    @staticmethod
    def create_batch(
        count: int,
        *,
        tenant_id: Optional[UUID] = None,
        property_id: Optional[UUID] = None,
        **kwargs
    ) -> list[Member]:
        """
        Create a batch of Members with realistic distribution.

        Args:
            count: Number of members to create
            tenant_id: Tenant ID for all members (generates one if not provided)
            property_id: Property ID for all members (generates one if not provided)
            **kwargs: Additional arguments passed to create()

        Returns:
            List of Member instances
        """
        tenant_id = tenant_id or uuid4()
        property_id = property_id or uuid4()

        return [
            MemberGenerator.create(
                tenant_id=tenant_id,
                property_id=property_id,
                **kwargs
            )
            for _ in range(count)
        ]
