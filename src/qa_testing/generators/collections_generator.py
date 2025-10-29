"""Collections and delinquency data generator for realistic test data."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from faker import Faker

from qa_testing.models import (
    ActionStatus,
    ActionType,
    CollectionAction,
    CollectionNotice,
    CollectionStage,
    DelinquencyStatus,
    DeliveryMethod,
    FeeType,
    LateFeeRule,
    NoticeType,
)

fake = Faker()


class LateFeeRuleGenerator:
    """
    Generator for creating realistic LateFeeRule test data.

    Usage:
        # Create a flat fee rule
        rule = LateFeeRuleGenerator.create_flat(
            tenant_id=tenant.id,
            flat_amount=Decimal("25.00")
        )

        # Create a percentage fee rule
        rule = LateFeeRuleGenerator.create_percentage(
            tenant_id=tenant.id,
            percentage_rate=Decimal("10.00")
        )

        # Create a combined fee rule (both flat and percentage)
        rule = LateFeeRuleGenerator.create_both(
            tenant_id=tenant.id,
            flat_amount=Decimal("25.00"),
            percentage_rate=Decimal("5.00")
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        name: Optional[str] = None,
        grace_period_days: Optional[int] = None,
        fee_type: Optional[FeeType] = None,
        flat_amount: Optional[Decimal] = None,
        percentage_rate: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        is_recurring: bool = False,
        is_active: bool = True,
    ) -> LateFeeRule:
        """
        Create a late fee rule with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            name: Rule name (generates if not provided)
            grace_period_days: Grace period (5-15 days if not provided)
            fee_type: Type of fee (random if not provided)
            flat_amount: Flat fee amount ($25-$200 if not provided)
            percentage_rate: Percentage rate (5-15% if not provided)
            max_amount: Maximum fee cap (optional)
            is_recurring: Whether fee applies monthly
            is_active: Whether rule is active

        Returns:
            LateFeeRule instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Generate grace period (typical: 5-15 days)
        if grace_period_days is None:
            grace_period_days = fake.random.randint(5, 15)

        # Select random fee type if not provided
        if fee_type is None:
            fee_type = fake.random.choice(list(FeeType))

        # Generate fee amounts based on type
        if flat_amount is None:
            if fee_type in [FeeType.FLAT, FeeType.BOTH]:
                flat_amount = Decimal(str(fake.random.randint(25, 200))).quantize(Decimal("0.01"))
            else:
                flat_amount = Decimal("0.00")

        if percentage_rate is None:
            if fee_type in [FeeType.PERCENTAGE, FeeType.BOTH]:
                percentage_rate = Decimal(str(fake.random.uniform(5, 15))).quantize(Decimal("0.01"))
            else:
                percentage_rate = Decimal("0.00")

        # Generate max amount cap (50% chance)
        if max_amount is None and fake.random.random() < 0.5:
            max_amount = Decimal(str(fake.random.randint(100, 500))).quantize(Decimal("0.01"))

        # Generate name
        if name is None:
            if fee_type == FeeType.FLAT:
                name = f"Flat Late Fee - ${flat_amount}"
            elif fee_type == FeeType.PERCENTAGE:
                name = f"Percentage Late Fee - {percentage_rate}%"
            else:
                name = f"Combined Late Fee - ${flat_amount} + {percentage_rate}%"

        return LateFeeRule(
            tenant_id=tenant_id,
            name=name,
            grace_period_days=grace_period_days,
            fee_type=fee_type,
            flat_amount=flat_amount,
            percentage_rate=percentage_rate,
            max_amount=max_amount,
            is_recurring=is_recurring,
            is_active=is_active,
        )

    @staticmethod
    def create_flat(
        *,
        tenant_id: Optional[UUID] = None,
        flat_amount: Optional[Decimal] = None,
        grace_period_days: Optional[int] = None,
        max_amount: Optional[Decimal] = None,
    ) -> LateFeeRule:
        """Create a flat fee rule."""
        if flat_amount is None:
            flat_amount = Decimal("25.00")

        return LateFeeRuleGenerator.create(
            tenant_id=tenant_id,
            fee_type=FeeType.FLAT,
            flat_amount=flat_amount,
            percentage_rate=Decimal("0.00"),
            grace_period_days=grace_period_days,
            max_amount=max_amount,
        )

    @staticmethod
    def create_percentage(
        *,
        tenant_id: Optional[UUID] = None,
        percentage_rate: Optional[Decimal] = None,
        grace_period_days: Optional[int] = None,
        max_amount: Optional[Decimal] = None,
    ) -> LateFeeRule:
        """Create a percentage fee rule."""
        if percentage_rate is None:
            percentage_rate = Decimal("10.00")

        return LateFeeRuleGenerator.create(
            tenant_id=tenant_id,
            fee_type=FeeType.PERCENTAGE,
            flat_amount=Decimal("0.00"),
            percentage_rate=percentage_rate,
            grace_period_days=grace_period_days,
            max_amount=max_amount,
        )

    @staticmethod
    def create_both(
        *,
        tenant_id: Optional[UUID] = None,
        flat_amount: Optional[Decimal] = None,
        percentage_rate: Optional[Decimal] = None,
        grace_period_days: Optional[int] = None,
        max_amount: Optional[Decimal] = None,
    ) -> LateFeeRule:
        """Create a combined fee rule (both flat and percentage)."""
        if flat_amount is None:
            flat_amount = Decimal("25.00")
        if percentage_rate is None:
            percentage_rate = Decimal("5.00")

        return LateFeeRuleGenerator.create(
            tenant_id=tenant_id,
            fee_type=FeeType.BOTH,
            flat_amount=flat_amount,
            percentage_rate=percentage_rate,
            grace_period_days=grace_period_days,
            max_amount=max_amount,
        )


class DelinquencyStatusGenerator:
    """
    Generator for creating realistic DelinquencyStatus test data.

    Usage:
        # Create current (no delinquency)
        status = DelinquencyStatusGenerator.create_current(
            tenant_id=tenant.id,
            member_id=member.id
        )

        # Create delinquent account at specific stage
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=tenant.id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_31_60,
            days_delinquent=45
        )

        # Create with specific aging buckets
        status = DelinquencyStatusGenerator.create(
            tenant_id=tenant.id,
            member_id=member.id,
            balance_0_30=Decimal("300.00"),
            balance_31_60=Decimal("300.00")
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        member_id: UUID,
        collection_stage: Optional[CollectionStage] = None,
        days_delinquent: Optional[int] = None,
        balance_0_30: Optional[Decimal] = None,
        balance_31_60: Optional[Decimal] = None,
        balance_61_90: Optional[Decimal] = None,
        balance_90_plus: Optional[Decimal] = None,
        current_balance: Optional[Decimal] = None,
        last_payment_date: Optional[date] = None,
        last_notice_date: Optional[date] = None,
        is_payment_plan: bool = False,
        notes: str = "",
    ) -> DelinquencyStatus:
        """
        Create a delinquency status with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            member_id: Member ID (required)
            collection_stage: Collection stage (generates based on days_delinquent)
            days_delinquent: Days past due (generates if not provided)
            balance_0_30: Balance 0-30 days past due
            balance_31_60: Balance 31-60 days past due
            balance_61_90: Balance 61-90 days past due
            balance_90_plus: Balance 90+ days past due
            current_balance: Total balance (sum of buckets if not provided)
            last_payment_date: Last payment date
            last_notice_date: Last notice date
            is_payment_plan: Whether on payment plan
            notes: Notes about delinquency

        Returns:
            DelinquencyStatus instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Generate days delinquent
        if days_delinquent is None:
            days_delinquent = fake.random.randint(0, 120)

        # Determine collection stage based on days delinquent
        if collection_stage is None:
            if days_delinquent == 0:
                collection_stage = CollectionStage.CURRENT
            elif days_delinquent <= 30:
                collection_stage = CollectionStage.DAYS_0_30
            elif days_delinquent <= 60:
                collection_stage = CollectionStage.DAYS_31_60
            elif days_delinquent <= 90:
                collection_stage = CollectionStage.DAYS_61_90
            else:
                collection_stage = CollectionStage.DAYS_90_PLUS

        # Generate aging buckets based on days delinquent
        if balance_0_30 is None and balance_31_60 is None and balance_61_90 is None and balance_90_plus is None:
            monthly_fee = Decimal("300.00")

            if days_delinquent <= 30:
                balance_0_30 = monthly_fee * (days_delinquent // 30 + 1)
                balance_31_60 = Decimal("0.00")
                balance_61_90 = Decimal("0.00")
                balance_90_plus = Decimal("0.00")
            elif days_delinquent <= 60:
                balance_0_30 = Decimal("0.00")
                balance_31_60 = monthly_fee * 2
                balance_61_90 = Decimal("0.00")
                balance_90_plus = Decimal("0.00")
            elif days_delinquent <= 90:
                balance_0_30 = Decimal("0.00")
                balance_31_60 = Decimal("0.00")
                balance_61_90 = monthly_fee * 3
                balance_90_plus = Decimal("0.00")
            else:
                # Distribute across buckets
                months_behind = days_delinquent // 30
                balance_0_30 = monthly_fee
                balance_31_60 = monthly_fee
                balance_61_90 = monthly_fee
                balance_90_plus = monthly_fee * max(1, months_behind - 3)
        else:
            # Use provided values or defaults
            balance_0_30 = balance_0_30 or Decimal("0.00")
            balance_31_60 = balance_31_60 or Decimal("0.00")
            balance_61_90 = balance_61_90 or Decimal("0.00")
            balance_90_plus = balance_90_plus or Decimal("0.00")

        # Calculate current balance as sum of buckets
        if current_balance is None:
            current_balance = balance_0_30 + balance_31_60 + balance_61_90 + balance_90_plus

        # Quantize all amounts
        balance_0_30 = balance_0_30.quantize(Decimal("0.01"))
        balance_31_60 = balance_31_60.quantize(Decimal("0.01"))
        balance_61_90 = balance_61_90.quantize(Decimal("0.01"))
        balance_90_plus = balance_90_plus.quantize(Decimal("0.01"))
        current_balance = current_balance.quantize(Decimal("0.01"))

        # Generate dates
        if last_payment_date is None and days_delinquent > 0:
            last_payment_date = date.today() - timedelta(days=days_delinquent + 30)

        if last_notice_date is None and days_delinquent > 15:
            last_notice_date = date.today() - timedelta(days=7)

        return DelinquencyStatus(
            tenant_id=tenant_id,
            member_id=member_id,
            collection_stage=collection_stage,
            days_delinquent=days_delinquent,
            balance_0_30=balance_0_30,
            balance_31_60=balance_31_60,
            balance_61_90=balance_61_90,
            balance_90_plus=balance_90_plus,
            current_balance=current_balance,
            last_payment_date=last_payment_date,
            last_notice_date=last_notice_date,
            is_payment_plan=is_payment_plan,
            notes=notes,
        )

    @staticmethod
    def create_current(
        *,
        tenant_id: Optional[UUID] = None,
        member_id: UUID,
    ) -> DelinquencyStatus:
        """Create a current (non-delinquent) status."""
        return DelinquencyStatusGenerator.create(
            tenant_id=tenant_id,
            member_id=member_id,
            collection_stage=CollectionStage.CURRENT,
            days_delinquent=0,
            balance_0_30=Decimal("0.00"),
            balance_31_60=Decimal("0.00"),
            balance_61_90=Decimal("0.00"),
            balance_90_plus=Decimal("0.00"),
            current_balance=Decimal("0.00"),
        )

    @staticmethod
    def create_delinquent(
        *,
        tenant_id: Optional[UUID] = None,
        member_id: UUID,
        collection_stage: CollectionStage,
        days_delinquent: int,
    ) -> DelinquencyStatus:
        """Create a delinquent status at specific stage."""
        return DelinquencyStatusGenerator.create(
            tenant_id=tenant_id,
            member_id=member_id,
            collection_stage=collection_stage,
            days_delinquent=days_delinquent,
        )


class CollectionNoticeGenerator:
    """
    Generator for creating realistic CollectionNotice test data.

    Usage:
        # Create first notice
        notice = CollectionNoticeGenerator.create_first_notice(
            tenant_id=tenant.id,
            delinquency_status_id=status.id
        )

        # Create final notice with certified mail
        notice = CollectionNoticeGenerator.create_final_notice(
            tenant_id=tenant.id,
            delinquency_status_id=status.id,
            delivery_method=DeliveryMethod.CERTIFIED_MAIL
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        delinquency_status_id: UUID,
        notice_type: Optional[NoticeType] = None,
        delivery_method: Optional[DeliveryMethod] = None,
        sent_date: Optional[date] = None,
        balance_at_notice: Optional[Decimal] = None,
        tracking_number: str = "",
        delivered_date: Optional[date] = None,
        returned_undeliverable: bool = False,
        notes: str = "",
    ) -> CollectionNotice:
        """
        Create a collection notice with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            delinquency_status_id: Associated delinquency status (required)
            notice_type: Type of notice (random if not provided)
            delivery_method: Delivery method (random if not provided)
            sent_date: Date sent (today if not provided)
            balance_at_notice: Balance at notice (generates if not provided)
            tracking_number: Tracking number (generates for certified mail)
            delivered_date: Date delivered (calculates if not provided)
            returned_undeliverable: Whether returned
            notes: Notes about notice

        Returns:
            CollectionNotice instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Select random notice type if not provided
        if notice_type is None:
            notice_type = fake.random.choice(list(NoticeType))

        # Select delivery method (prefer certified mail for serious notices)
        if delivery_method is None:
            if notice_type in [NoticeType.FINAL_NOTICE, NoticeType.PRE_LIEN, NoticeType.ATTORNEY_REFERRAL]:
                delivery_method = DeliveryMethod.CERTIFIED_MAIL
            else:
                delivery_method = fake.random.choice([DeliveryMethod.EMAIL, DeliveryMethod.REGULAR_MAIL])

        # Generate sent date
        if sent_date is None:
            sent_date = date.today()

        # Generate balance
        if balance_at_notice is None:
            balance_at_notice = Decimal(str(fake.random.randint(300, 5000))).quantize(Decimal("0.01"))

        # Generate tracking number for certified mail
        if not tracking_number and delivery_method == DeliveryMethod.CERTIFIED_MAIL:
            tracking_number = fake.bothify(text="??########US", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ")

        # Generate delivered date (3-7 days after sent for certified mail)
        if delivered_date is None and delivery_method in [DeliveryMethod.CERTIFIED_MAIL, DeliveryMethod.REGULAR_MAIL]:
            if not returned_undeliverable:
                days_to_deliver = fake.random.randint(3, 7)
                delivered_date = sent_date + timedelta(days=days_to_deliver)

        return CollectionNotice(
            tenant_id=tenant_id,
            delinquency_status_id=delinquency_status_id,
            notice_type=notice_type,
            delivery_method=delivery_method,
            sent_date=sent_date,
            balance_at_notice=balance_at_notice,
            tracking_number=tracking_number,
            delivered_date=delivered_date,
            returned_undeliverable=returned_undeliverable,
            notes=notes,
        )

    @staticmethod
    def create_first_notice(
        *,
        tenant_id: Optional[UUID] = None,
        delinquency_status_id: UUID,
        delivery_method: Optional[DeliveryMethod] = None,
    ) -> CollectionNotice:
        """Create a first notice."""
        return CollectionNoticeGenerator.create(
            tenant_id=tenant_id,
            delinquency_status_id=delinquency_status_id,
            notice_type=NoticeType.FIRST_NOTICE,
            delivery_method=delivery_method or DeliveryMethod.EMAIL,
        )

    @staticmethod
    def create_final_notice(
        *,
        tenant_id: Optional[UUID] = None,
        delinquency_status_id: UUID,
        delivery_method: Optional[DeliveryMethod] = None,
    ) -> CollectionNotice:
        """Create a final notice."""
        return CollectionNoticeGenerator.create(
            tenant_id=tenant_id,
            delinquency_status_id=delinquency_status_id,
            notice_type=NoticeType.FINAL_NOTICE,
            delivery_method=delivery_method or DeliveryMethod.CERTIFIED_MAIL,
        )


class CollectionActionGenerator:
    """
    Generator for creating realistic CollectionAction test data.

    Usage:
        # Create attorney referral
        action = CollectionActionGenerator.create_attorney_referral(
            tenant_id=tenant.id,
            delinquency_status_id=status.id
        )

        # Create lien filing
        action = CollectionActionGenerator.create_lien(
            tenant_id=tenant.id,
            delinquency_status_id=status.id,
            status=ActionStatus.COMPLETED
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        delinquency_status_id: UUID,
        action_type: Optional[ActionType] = None,
        status: Optional[ActionStatus] = None,
        requested_date: Optional[date] = None,
        approved_date: Optional[date] = None,
        approved_by: Optional[UUID] = None,
        completed_date: Optional[date] = None,
        balance_at_action: Optional[Decimal] = None,
        attorney_name: str = "",
        case_number: str = "",
        notes: str = "",
    ) -> CollectionAction:
        """
        Create a collection action with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            delinquency_status_id: Associated delinquency status (required)
            action_type: Type of action (random if not provided)
            status: Action status (PENDING_APPROVAL if not provided)
            requested_date: Date requested (generates if not provided)
            approved_date: Date approved (generates if status is approved)
            approved_by: Board member who approved (generates if approved)
            completed_date: Date completed (generates if status is completed)
            balance_at_action: Balance at action (generates if not provided)
            attorney_name: Attorney name (for attorney referrals)
            case_number: Case number (for liens/foreclosures)
            notes: Notes about action

        Returns:
            CollectionAction instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Select random action type if not provided
        if action_type is None:
            action_type = fake.random.choice(list(ActionType))

        # Default status
        if status is None:
            status = ActionStatus.PENDING_APPROVAL

        # Generate requested date (within last 30 days)
        if requested_date is None:
            days_ago = fake.random.randint(1, 30)
            requested_date = date.today() - timedelta(days=days_ago)

        # Generate approved date if status is approved or later
        if approved_date is None and status in [ActionStatus.APPROVED, ActionStatus.IN_PROGRESS, ActionStatus.COMPLETED]:
            days_after_requested = fake.random.randint(1, 14)
            approved_date = requested_date + timedelta(days=days_after_requested)
            approved_by = approved_by or uuid4()

        # Generate completed date if status is completed
        if completed_date is None and status == ActionStatus.COMPLETED:
            days_after_approved = fake.random.randint(7, 60)
            completed_date = (approved_date or requested_date) + timedelta(days=days_after_approved)

        # Generate balance
        if balance_at_action is None:
            balance_at_action = Decimal(str(fake.random.randint(1000, 10000))).quantize(Decimal("0.01"))

        # Generate attorney name for attorney referrals
        if not attorney_name and action_type == ActionType.ATTORNEY_REFERRAL:
            attorney_name = fake.name() + ", Esq."

        # Generate case number for liens and foreclosures
        if not case_number and action_type in [ActionType.LIEN_FILED, ActionType.FORECLOSURE]:
            case_number = fake.bothify(text="????-####", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ")

        return CollectionAction(
            tenant_id=tenant_id,
            delinquency_status_id=delinquency_status_id,
            action_type=action_type,
            status=status,
            requested_date=requested_date,
            approved_date=approved_date,
            approved_by=approved_by,
            completed_date=completed_date,
            balance_at_action=balance_at_action,
            attorney_name=attorney_name,
            case_number=case_number,
            notes=notes,
        )

    @staticmethod
    def create_attorney_referral(
        *,
        tenant_id: Optional[UUID] = None,
        delinquency_status_id: UUID,
        status: Optional[ActionStatus] = None,
    ) -> CollectionAction:
        """Create an attorney referral action."""
        return CollectionActionGenerator.create(
            tenant_id=tenant_id,
            delinquency_status_id=delinquency_status_id,
            action_type=ActionType.ATTORNEY_REFERRAL,
            status=status,
        )

    @staticmethod
    def create_lien(
        *,
        tenant_id: Optional[UUID] = None,
        delinquency_status_id: UUID,
        status: Optional[ActionStatus] = None,
    ) -> CollectionAction:
        """Create a lien filing action."""
        return CollectionActionGenerator.create(
            tenant_id=tenant_id,
            delinquency_status_id=delinquency_status_id,
            action_type=ActionType.LIEN_FILED,
            status=status,
        )
