"""
Accounts Receivable (AR) and Collections workflow generators.

Generates test data for delinquency scenarios, late fees, aging buckets,
payment plans, and collections workflows.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from qa_testing.models import Transaction, TransactionType
from qa_testing.models.base import money_amount


class DelinquencyStatus(str, Enum):
    """Delinquency status based on days past due."""

    CURRENT = "current"  # 0-29 days
    LATE_30 = "late_30"  # 30-59 days
    LATE_60 = "late_60"  # 60-89 days
    LATE_90 = "late_90"  # 90+ days
    COLLECTIONS = "collections"  # Sent to collections
    LEGAL = "legal"  # Legal action initiated
    SUSPENDED = "suspended"  # Account suspended


class PaymentPlanStatus(str, Enum):
    """Payment plan status."""

    ACTIVE = "active"  # Plan is active
    COMPLETED = "completed"  # Plan completed successfully
    DEFAULTED = "defaulted"  # Missed payment(s)
    CANCELLED = "cancelled"  # Plan cancelled


@dataclass
class AgingBucket:
    """
    Aging bucket for AR aging report.

    Represents amount owed in each aging category.
    """

    current: Decimal  # 0-29 days
    days_30: Decimal  # 30-59 days
    days_60: Decimal  # 60-89 days
    days_90_plus: Decimal  # 90+ days
    total: Decimal

    @staticmethod
    def create(
        *,
        current: Decimal = Decimal("0.00"),
        days_30: Decimal = Decimal("0.00"),
        days_60: Decimal = Decimal("0.00"),
        days_90_plus: Decimal = Decimal("0.00"),
    ) -> "AgingBucket":
        """Create an aging bucket."""
        total = current + days_30 + days_60 + days_90_plus

        return AgingBucket(
            current=money_amount(current),
            days_30=money_amount(days_30),
            days_60=money_amount(days_60),
            days_90_plus=money_amount(days_90_plus),
            total=money_amount(total),
        )


@dataclass
class PaymentPlan:
    """
    Payment plan for delinquent accounts.

    Allows members to pay off balance in installments.
    """

    id: UUID
    member_id: UUID
    property_id: UUID
    tenant_id: UUID
    total_amount: Decimal
    down_payment: Decimal
    num_installments: int
    installment_amount: Decimal
    remaining_balance: Decimal
    status: PaymentPlanStatus
    start_date: date
    next_payment_date: date
    grace_period_days: int = 5

    @staticmethod
    def create(
        *,
        member_id: UUID,
        property_id: UUID,
        tenant_id: Optional[UUID] = None,
        total_amount: Decimal,
        down_payment: Decimal = Decimal("0.00"),
        num_installments: int = 6,
        start_date: Optional[date] = None,
        grace_period_days: int = 5,
    ) -> "PaymentPlan":
        """Create a payment plan."""
        start = start_date or date.today()

        # Calculate installment amount
        remaining = total_amount - down_payment
        installment = (remaining / Decimal(num_installments)).quantize(Decimal("0.01"))

        return PaymentPlan(
            id=uuid4(),
            member_id=member_id,
            property_id=property_id,
            tenant_id=tenant_id or property_id,
            total_amount=money_amount(total_amount),
            down_payment=money_amount(down_payment),
            num_installments=num_installments,
            installment_amount=installment,
            remaining_balance=money_amount(remaining),
            status=PaymentPlanStatus.ACTIVE,
            start_date=start,
            next_payment_date=start + timedelta(days=30),  # First payment in 30 days
            grace_period_days=grace_period_days,
        )


class ARCollectionsGenerator:
    """
    Generator for AR/Collections test data.

    Creates delinquency scenarios, late fees, payment plans, and aging reports.
    """

    @staticmethod
    def calculate_delinquency_status(days_past_due: int) -> DelinquencyStatus:
        """
        Calculate delinquency status from days past due.

        Args:
            days_past_due: Number of days past due

        Returns:
            Delinquency status
        """
        if days_past_due < 30:
            return DelinquencyStatus.CURRENT
        elif days_past_due < 60:
            return DelinquencyStatus.LATE_30
        elif days_past_due < 90:
            return DelinquencyStatus.LATE_60
        elif days_past_due < 120:
            return DelinquencyStatus.LATE_90
        elif days_past_due < 180:
            return DelinquencyStatus.COLLECTIONS
        else:
            return DelinquencyStatus.LEGAL

    @staticmethod
    def create_delinquent_scenario(
        *,
        property_id: UUID,
        member_id: UUID,
        days_past_due: int,
        original_balance: Decimal = Decimal("300.00"),
    ) -> dict:
        """
        Create a delinquent member scenario.

        Returns:
        - status: DelinquencyStatus
        - days_past_due: int
        - balance_owed: Decimal (with late fees)
        - late_fees: Decimal
        - transactions: list[Transaction]
        """
        from qa_testing.generators import TransactionGenerator

        status = ARCollectionsGenerator.calculate_delinquency_status(days_past_due)

        # Calculate late fees
        late_fees = ARCollectionsGenerator.calculate_late_fees(
            original_balance,
            days_past_due,
        )

        # Create original due transaction
        due_date = date.today() - timedelta(days=days_past_due)
        original_txn = TransactionGenerator.create(
            property_id=property_id,
            transaction_type=TransactionType.MEMBER_DUES,
            amount=original_balance,
            transaction_date=due_date,
        )

        transactions = [original_txn]

        # Add late fee transactions
        if late_fees > Decimal("0.00"):
            late_fee_txn = TransactionGenerator.create(
                property_id=property_id,
                transaction_type=TransactionType.LATE_FEE,
                amount=late_fees,
                transaction_date=date.today(),
            )
            transactions.append(late_fee_txn)

        return {
            "status": status,
            "days_past_due": days_past_due,
            "original_balance": original_balance,
            "late_fees": late_fees,
            "balance_owed": original_balance + late_fees,
            "due_date": due_date,
            "transactions": transactions,
        }

    @staticmethod
    def calculate_late_fees(
        balance: Decimal,
        days_past_due: int,
        grace_period: int = 10,
        flat_fee: Decimal = Decimal("25.00"),
        monthly_rate: Decimal = Decimal("0.05"),  # 5% per month
    ) -> Decimal:
        """
        Calculate late fees for delinquent balance.

        Args:
            balance: Original balance owed
            days_past_due: Number of days past due
            grace_period: Grace period before fees apply
            flat_fee: Flat late fee
            monthly_rate: Monthly penalty rate (as decimal)

        Returns:
            Total late fees
        """
        if days_past_due <= grace_period:
            return Decimal("0.00")

        # Flat fee for first late payment
        total_fees = flat_fee

        # Add monthly penalty (compounding)
        months_late = max(0, (days_past_due - grace_period) // 30)
        if months_late > 0:
            penalty = balance * monthly_rate * Decimal(months_late)
            total_fees += penalty

        return money_amount(total_fees)

    @staticmethod
    def create_aging_bucket(
        *,
        current: Decimal = Decimal("0.00"),
        days_30: Decimal = Decimal("0.00"),
        days_60: Decimal = Decimal("0.00"),
        days_90_plus: Decimal = Decimal("0.00"),
    ) -> AgingBucket:
        """Create an aging bucket for AR aging report."""
        return AgingBucket.create(
            current=current,
            days_30=days_30,
            days_60=days_60,
            days_90_plus=days_90_plus,
        )

    @staticmethod
    def create_payment_plan(
        *,
        member_id: UUID,
        property_id: UUID,
        total_amount: Decimal,
        down_payment: Decimal = Decimal("0.00"),
        num_installments: int = 6,
    ) -> PaymentPlan:
        """Create a payment plan for delinquent member."""
        return PaymentPlan.create(
            member_id=member_id,
            property_id=property_id,
            total_amount=total_amount,
            down_payment=down_payment,
            num_installments=num_installments,
        )

    @staticmethod
    def create_collections_workflow(
        *,
        property_id: UUID,
        member_id: UUID,
        balance_owed: Decimal = Decimal("900.00"),
    ) -> dict:
        """
        Create a complete collections workflow scenario.

        Returns:
        - member_id: UUID
        - balance_owed: Decimal
        - collection_letters: list[dict]
        - collection_calls: list[dict]
        - payment_plan: Optional[PaymentPlan]
        - legal_action: bool
        """
        # Escalating collection letters
        collection_letters = [
            {
                "type": "friendly_reminder",
                "sent_date": date.today() - timedelta(days=35),
                "days_past_due": 35,
            },
            {
                "type": "first_notice",
                "sent_date": date.today() - timedelta(days=50),
                "days_past_due": 50,
            },
            {
                "type": "final_notice",
                "sent_date": date.today() - timedelta(days=75),
                "days_past_due": 75,
            },
        ]

        # Collection calls
        collection_calls = [
            {
                "date": date.today() - timedelta(days=60),
                "result": "no_answer",
            },
            {
                "date": date.today() - timedelta(days=55),
                "result": "promised_payment",
            },
            {
                "date": date.today() - timedelta(days=45),
                "result": "requested_payment_plan",
            },
        ]

        # Offer payment plan
        payment_plan = ARCollectionsGenerator.create_payment_plan(
            member_id=member_id,
            property_id=property_id,
            total_amount=balance_owed,
            down_payment=Decimal("150.00"),  # 10% down
            num_installments=6,
        )

        # Legal action if balance > $1000 and 120+ days
        legal_action = balance_owed >= Decimal("1000.00")

        return {
            "member_id": member_id,
            "balance_owed": balance_owed,
            "collection_letters": collection_letters,
            "collection_calls": collection_calls,
            "payment_plan": payment_plan,
            "legal_action": legal_action,
        }

    @staticmethod
    def allocate_partial_payment(
        aging_bucket: AgingBucket,
        payment_amount: Decimal,
    ) -> AgingBucket:
        """
        Allocate partial payment to aging buckets (oldest first).

        Args:
            aging_bucket: Current aging bucket
            payment_amount: Payment amount to allocate

        Returns:
            Updated aging bucket after payment
        """
        remaining = payment_amount

        # Pay oldest first (90+, then 60, then 30, then current)
        new_90_plus = max(Decimal("0.00"), aging_bucket.days_90_plus - remaining)
        remaining -= (aging_bucket.days_90_plus - new_90_plus)

        new_60 = max(Decimal("0.00"), aging_bucket.days_60 - remaining)
        remaining -= (aging_bucket.days_60 - new_60)

        new_30 = max(Decimal("0.00"), aging_bucket.days_30 - remaining)
        remaining -= (aging_bucket.days_30 - new_30)

        new_current = max(Decimal("0.00"), aging_bucket.current - remaining)

        return AgingBucket.create(
            current=new_current,
            days_30=new_30,
            days_60=new_60,
            days_90_plus=new_90_plus,
        )
