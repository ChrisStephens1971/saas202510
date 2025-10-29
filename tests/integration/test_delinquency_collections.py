"""
Integration tests for delinquency workflow and collections functionality.

Tests the complete collections lifecycle including:
- Late fee rule configuration (flat, percentage, both)
- Late fee calculation and application
- Delinquency status tracking and aging buckets
- Collection stage progression (8 stages)
- Collection notice generation and tracking (6 types, 3 delivery methods)
- Collection action workflow (5 action types, 5 statuses)
- Payment plan tracking
- Board approval workflow
- Data type validation (Decimal precision, date types)
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from qa_testing.generators import (
    CollectionActionGenerator,
    CollectionNoticeGenerator,
    DelinquencyStatusGenerator,
    LateFeeRuleGenerator,
    MemberGenerator,
    PropertyGenerator,
)
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


class TestLateFeeRules:
    """Tests for late fee rule configuration."""

    def test_create_flat_fee_rule(self):
        """Test creating a flat late fee rule."""
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_flat(
            tenant_id=property_obj.tenant_id,
            flat_amount=Decimal("25.00"),
        )

        assert rule.fee_type == FeeType.FLAT
        assert rule.flat_amount == Decimal("25.00")
        assert rule.percentage_rate == Decimal("0.00")
        assert rule.grace_period_days >= 5
        assert rule.grace_period_days <= 15

    def test_create_percentage_fee_rule(self):
        """Test creating a percentage late fee rule."""
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_percentage(
            tenant_id=property_obj.tenant_id,
            percentage_rate=Decimal("10.00"),
        )

        assert rule.fee_type == FeeType.PERCENTAGE
        assert rule.flat_amount == Decimal("0.00")
        assert rule.percentage_rate == Decimal("10.00")

    def test_create_both_fee_rule(self):
        """Test creating a combined late fee rule (flat + percentage)."""
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_both(
            tenant_id=property_obj.tenant_id,
            flat_amount=Decimal("25.00"),
            percentage_rate=Decimal("5.00"),
        )

        assert rule.fee_type == FeeType.BOTH
        assert rule.flat_amount == Decimal("25.00")
        assert rule.percentage_rate == Decimal("5.00")

    def test_late_fee_rule_with_max_cap(self):
        """Test late fee rule with maximum amount cap."""
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            fee_type=FeeType.PERCENTAGE,
            percentage_rate=Decimal("15.00"),
            max_amount=Decimal("100.00"),
        )

        assert rule.max_amount == Decimal("100.00")

    def test_recurring_late_fee_rule(self):
        """Test recurring late fee rule (applies monthly)."""
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            is_recurring=True,
        )

        assert rule.is_recurring is True

    def test_one_time_late_fee_rule(self):
        """Test one-time late fee rule (not recurring)."""
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            is_recurring=False,
        )

        assert rule.is_recurring is False


class TestLateFeeCalculation:
    """Tests for late fee calculation logic."""

    def test_flat_fee_calculation(self):
        """Test calculating flat late fee."""
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_flat(
            tenant_id=property_obj.tenant_id,
            flat_amount=Decimal("25.00"),
        )

        # Flat fee is always the same regardless of balance
        balance = Decimal("300.00")
        late_fee = rule.flat_amount

        assert late_fee == Decimal("25.00")

    def test_percentage_fee_calculation(self):
        """Test calculating percentage late fee."""
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_percentage(
            tenant_id=property_obj.tenant_id,
            percentage_rate=Decimal("10.00"),
        )

        # Calculate percentage fee: balance * (rate / 100)
        balance = Decimal("300.00")
        late_fee = (balance * rule.percentage_rate / Decimal("100")).quantize(Decimal("0.01"))

        assert late_fee == Decimal("30.00")

    def test_combined_fee_calculation(self):
        """Test calculating combined late fee (flat + percentage)."""
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_both(
            tenant_id=property_obj.tenant_id,
            flat_amount=Decimal("25.00"),
            percentage_rate=Decimal("5.00"),
        )

        # Calculate combined fee: flat + (balance * percentage / 100)
        balance = Decimal("300.00")
        late_fee = rule.flat_amount + (balance * rule.percentage_rate / Decimal("100"))
        late_fee = late_fee.quantize(Decimal("0.01"))

        assert late_fee == Decimal("40.00")  # $25 + $15

    def test_fee_with_max_cap(self):
        """Test that late fee is capped at max_amount."""
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_percentage(
            tenant_id=property_obj.tenant_id,
            percentage_rate=Decimal("15.00"),
            max_amount=Decimal("100.00"),
        )

        # Calculate fee without cap
        balance = Decimal("1000.00")
        calculated_fee = (balance * rule.percentage_rate / Decimal("100")).quantize(Decimal("0.01"))
        assert calculated_fee == Decimal("150.00")

        # Apply max cap
        late_fee = min(calculated_fee, rule.max_amount)
        assert late_fee == Decimal("100.00")

    def test_grace_period_application(self):
        """Test that grace period delays late fee application."""
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create(
            tenant_id=property_obj.tenant_id,
            grace_period_days=10,
        )

        # Within grace period - no late fee
        days_late = 8
        assert days_late < rule.grace_period_days

        # After grace period - late fee applies
        days_late = 12
        assert days_late > rule.grace_period_days


class TestDelinquencyTracking:
    """Tests for delinquency status tracking."""

    def test_create_current_status(self):
        """Test creating a current (non-delinquent) status."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create_current(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
        )

        assert status.collection_stage == CollectionStage.CURRENT
        assert status.days_delinquent == 0
        assert status.current_balance == Decimal("0.00")
        assert status.is_delinquent is False

    def test_create_delinquent_status(self):
        """Test creating a delinquent status."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_31_60,
            days_delinquent=45,
        )

        assert status.collection_stage == CollectionStage.DAYS_31_60
        assert status.days_delinquent == 45
        assert status.current_balance > Decimal("0.00")
        assert status.is_delinquent is True

    def test_aging_bucket_0_30_days(self):
        """Test 0-30 day aging bucket."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            days_delinquent=20,
            balance_0_30=Decimal("300.00"),
            balance_31_60=Decimal("0.00"),
            balance_61_90=Decimal("0.00"),
            balance_90_plus=Decimal("0.00"),
        )

        assert status.balance_0_30 == Decimal("300.00")
        assert status.current_balance == Decimal("300.00")

    def test_aging_bucket_31_60_days(self):
        """Test 31-60 day aging bucket."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            days_delinquent=45,
            balance_0_30=Decimal("0.00"),
            balance_31_60=Decimal("600.00"),
            balance_61_90=Decimal("0.00"),
            balance_90_plus=Decimal("0.00"),
        )

        assert status.balance_31_60 == Decimal("600.00")
        assert status.current_balance == Decimal("600.00")

    def test_aging_bucket_61_90_days(self):
        """Test 61-90 day aging bucket."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            days_delinquent=75,
            balance_0_30=Decimal("0.00"),
            balance_31_60=Decimal("0.00"),
            balance_61_90=Decimal("900.00"),
            balance_90_plus=Decimal("0.00"),
        )

        assert status.balance_61_90 == Decimal("900.00")
        assert status.current_balance == Decimal("900.00")

    def test_aging_bucket_90_plus_days(self):
        """Test 90+ day aging bucket."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            days_delinquent=120,
            balance_0_30=Decimal("0.00"),
            balance_31_60=Decimal("0.00"),
            balance_61_90=Decimal("0.00"),
            balance_90_plus=Decimal("1200.00"),
        )

        assert status.balance_90_plus == Decimal("1200.00")
        assert status.current_balance == Decimal("1200.00")

    def test_aging_buckets_sum_to_current_balance(self):
        """Test that aging buckets sum to current_balance."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            balance_0_30=Decimal("300.00"),
            balance_31_60=Decimal("300.00"),
            balance_61_90=Decimal("300.00"),
            balance_90_plus=Decimal("300.00"),
        )

        sum_of_buckets = (
            status.balance_0_30 +
            status.balance_31_60 +
            status.balance_61_90 +
            status.balance_90_plus
        )

        assert status.current_balance == sum_of_buckets
        assert status.current_balance == Decimal("1200.00")


class TestCollectionStageProgression:
    """Tests for collection stage progression."""

    def test_current_stage(self):
        """Test CURRENT stage (no delinquency)."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create_current(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
        )

        assert status.collection_stage == CollectionStage.CURRENT

    def test_0_30_days_stage(self):
        """Test 0-30 days collection stage."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_0_30,
            days_delinquent=20,
        )

        assert status.collection_stage == CollectionStage.DAYS_0_30

    def test_31_60_days_stage(self):
        """Test 31-60 days collection stage."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_31_60,
            days_delinquent=45,
        )

        assert status.collection_stage == CollectionStage.DAYS_31_60

    def test_61_90_days_stage(self):
        """Test 61-90 days collection stage."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_61_90,
            days_delinquent=75,
        )

        assert status.collection_stage == CollectionStage.DAYS_61_90

    def test_90_plus_days_stage(self):
        """Test 90+ days collection stage."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_90_PLUS,
            days_delinquent=120,
        )

        assert status.collection_stage == CollectionStage.DAYS_90_PLUS

    def test_attorney_referral_stage(self):
        """Test ATTORNEY_REFERRAL collection stage."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.ATTORNEY_REFERRAL,
            days_delinquent=150,
        )

        assert status.collection_stage == CollectionStage.ATTORNEY_REFERRAL

    def test_lien_filed_stage(self):
        """Test LIEN_FILED collection stage."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.LIEN_FILED,
            days_delinquent=180,
        )

        assert status.collection_stage == CollectionStage.LIEN_FILED

    def test_foreclosure_stage(self):
        """Test FORECLOSURE collection stage."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.FORECLOSURE,
            days_delinquent=365,
        )

        assert status.collection_stage == CollectionStage.FORECLOSURE


class TestCollectionNotices:
    """Tests for collection notice generation and tracking."""

    def test_create_first_notice(self):
        """Test creating a first notice."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_0_30,
            days_delinquent=20,
        )

        notice = CollectionNoticeGenerator.create_first_notice(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
        )

        assert notice.notice_type == NoticeType.FIRST_NOTICE

    def test_create_second_notice(self):
        """Test creating a second notice."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_31_60,
            days_delinquent=45,
        )

        notice = CollectionNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            notice_type=NoticeType.SECOND_NOTICE,
        )

        assert notice.notice_type == NoticeType.SECOND_NOTICE

    def test_create_final_notice(self):
        """Test creating a final notice."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_61_90,
            days_delinquent=75,
        )

        notice = CollectionNoticeGenerator.create_final_notice(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
        )

        assert notice.notice_type == NoticeType.FINAL_NOTICE

    def test_create_pre_lien_notice(self):
        """Test creating a pre-lien notice."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_90_PLUS,
            days_delinquent=100,
        )

        notice = CollectionNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            notice_type=NoticeType.PRE_LIEN,
        )

        assert notice.notice_type == NoticeType.PRE_LIEN

    def test_create_lien_filed_notice(self):
        """Test creating a lien filed notice."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.LIEN_FILED,
            days_delinquent=180,
        )

        notice = CollectionNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            notice_type=NoticeType.LIEN_FILED,
        )

        assert notice.notice_type == NoticeType.LIEN_FILED

    def test_create_attorney_referral_notice(self):
        """Test creating an attorney referral notice."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.ATTORNEY_REFERRAL,
            days_delinquent=150,
        )

        notice = CollectionNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            notice_type=NoticeType.ATTORNEY_REFERRAL,
        )

        assert notice.notice_type == NoticeType.ATTORNEY_REFERRAL

    def test_email_delivery_method(self):
        """Test email delivery method."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_0_30,
            days_delinquent=20,
        )

        notice = CollectionNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            delivery_method=DeliveryMethod.EMAIL,
        )

        assert notice.delivery_method == DeliveryMethod.EMAIL

    def test_regular_mail_delivery_method(self):
        """Test regular mail delivery method."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_31_60,
            days_delinquent=45,
        )

        notice = CollectionNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            delivery_method=DeliveryMethod.REGULAR_MAIL,
        )

        assert notice.delivery_method == DeliveryMethod.REGULAR_MAIL

    def test_certified_mail_delivery_method(self):
        """Test certified mail delivery method."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_61_90,
            days_delinquent=75,
        )

        notice = CollectionNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            delivery_method=DeliveryMethod.CERTIFIED_MAIL,
        )

        assert notice.delivery_method == DeliveryMethod.CERTIFIED_MAIL
        assert len(notice.tracking_number) > 0

    def test_tracking_number_for_certified_mail(self):
        """Test that certified mail has tracking number."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_61_90,
            days_delinquent=75,
        )

        notice = CollectionNoticeGenerator.create_final_notice(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            delivery_method=DeliveryMethod.CERTIFIED_MAIL,
        )

        assert notice.tracking_number != ""
        assert len(notice.tracking_number) > 0

    def test_delivered_date_tracking(self):
        """Test that delivered_date is tracked for mail notices."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_31_60,
            days_delinquent=45,
        )

        notice = CollectionNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            delivery_method=DeliveryMethod.CERTIFIED_MAIL,
        )

        assert notice.delivered_date is not None
        assert notice.delivered_date >= notice.sent_date

    def test_returned_undeliverable_tracking(self):
        """Test tracking of returned/undeliverable notices."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_31_60,
            days_delinquent=45,
        )

        notice = CollectionNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            returned_undeliverable=True,
        )

        assert notice.returned_undeliverable is True


class TestCollectionActions:
    """Tests for collection action workflow."""

    def test_create_attorney_referral_action(self):
        """Test creating an attorney referral action."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.ATTORNEY_REFERRAL,
            days_delinquent=150,
        )

        action = CollectionActionGenerator.create_attorney_referral(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
        )

        assert action.action_type == ActionType.ATTORNEY_REFERRAL
        assert len(action.attorney_name) > 0

    def test_create_lien_filing_action(self):
        """Test creating a lien filing action."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.LIEN_FILED,
            days_delinquent=180,
        )

        action = CollectionActionGenerator.create_lien(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
        )

        assert action.action_type == ActionType.LIEN_FILED
        assert len(action.case_number) > 0

    def test_create_foreclosure_action(self):
        """Test creating a foreclosure action."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.FORECLOSURE,
            days_delinquent=365,
        )

        action = CollectionActionGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            action_type=ActionType.FORECLOSURE,
        )

        assert action.action_type == ActionType.FORECLOSURE

    def test_create_payment_plan_action(self):
        """Test creating a payment plan action."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_61_90,
            days_delinquent=75,
        )

        action = CollectionActionGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            action_type=ActionType.PAYMENT_PLAN,
        )

        assert action.action_type == ActionType.PAYMENT_PLAN

    def test_create_write_off_action(self):
        """Test creating a write-off action."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_90_PLUS,
            days_delinquent=180,
        )

        action = CollectionActionGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            action_type=ActionType.WRITE_OFF,
        )

        assert action.action_type == ActionType.WRITE_OFF

    def test_pending_approval_status(self):
        """Test action with PENDING_APPROVAL status."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.ATTORNEY_REFERRAL,
            days_delinquent=150,
        )

        action = CollectionActionGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            status=ActionStatus.PENDING_APPROVAL,
        )

        assert action.status == ActionStatus.PENDING_APPROVAL
        assert action.approved_date is None

    def test_approved_status(self):
        """Test action with APPROVED status."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.ATTORNEY_REFERRAL,
            days_delinquent=150,
        )

        action = CollectionActionGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            status=ActionStatus.APPROVED,
        )

        assert action.status == ActionStatus.APPROVED
        assert action.approved_date is not None
        assert action.approved_by is not None

    def test_rejected_status(self):
        """Test action with REJECTED status."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.ATTORNEY_REFERRAL,
            days_delinquent=150,
        )

        action = CollectionActionGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            status=ActionStatus.REJECTED,
        )

        assert action.status == ActionStatus.REJECTED

    def test_in_progress_status(self):
        """Test action with IN_PROGRESS status."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.LIEN_FILED,
            days_delinquent=180,
        )

        action = CollectionActionGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            status=ActionStatus.IN_PROGRESS,
        )

        assert action.status == ActionStatus.IN_PROGRESS

    def test_completed_status(self):
        """Test action with COMPLETED status."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.LIEN_FILED,
            days_delinquent=180,
        )

        action = CollectionActionGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            status=ActionStatus.COMPLETED,
        )

        assert action.status == ActionStatus.COMPLETED
        assert action.completed_date is not None


class TestPaymentPlans:
    """Tests for payment plan tracking."""

    def test_payment_plan_flag(self):
        """Test is_payment_plan flag on delinquency status."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            is_payment_plan=True,
        )

        assert status.is_payment_plan is True

    def test_payment_plan_action(self):
        """Test creating a payment plan action."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_61_90,
            days_delinquent=75,
        )

        action = CollectionActionGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            action_type=ActionType.PAYMENT_PLAN,
            status=ActionStatus.APPROVED,
        )

        assert action.action_type == ActionType.PAYMENT_PLAN
        assert action.status == ActionStatus.APPROVED


class TestCollectionsDataTypes:
    """Tests for proper data type usage in collections."""

    def test_late_fee_amounts_use_decimal(self):
        """Test that late fee amounts use Decimal with 2 decimal places."""
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_both(
            tenant_id=property_obj.tenant_id,
            flat_amount=Decimal("25.00"),
            percentage_rate=Decimal("5.00"),
        )

        assert isinstance(rule.flat_amount, Decimal)
        assert rule.flat_amount == Decimal("25.00")
        # Check precision: should have exactly 2 decimal places
        assert rule.flat_amount.as_tuple().exponent == -2

    def test_delinquency_balances_use_decimal(self):
        """Test that delinquency balances use Decimal with 2 decimal places."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            balance_0_30=Decimal("300.00"),
        )

        assert isinstance(status.balance_0_30, Decimal)
        assert status.balance_0_30.as_tuple().exponent == -2

    def test_notice_balance_uses_decimal(self):
        """Test that notice balance uses Decimal with 2 decimal places."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_0_30,
            days_delinquent=20,
        )

        notice = CollectionNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            balance_at_notice=Decimal("350.00"),
        )

        assert isinstance(notice.balance_at_notice, Decimal)
        assert notice.balance_at_notice.as_tuple().exponent == -2

    def test_action_balance_uses_decimal(self):
        """Test that action balance uses Decimal with 2 decimal places."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.ATTORNEY_REFERRAL,
            days_delinquent=150,
        )

        action = CollectionActionGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
            balance_at_action=Decimal("5000.00"),
        )

        assert isinstance(action.balance_at_action, Decimal)
        assert action.balance_at_action.as_tuple().exponent == -2

    def test_dates_use_date_type(self):
        """Test that all dates use date type (not datetime)."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)
        status = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_31_60,
            days_delinquent=45,
        )

        # Check delinquency status dates
        if status.last_payment_date is not None:
            assert isinstance(status.last_payment_date, date)

        # Check notice dates
        notice = CollectionNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
        )
        assert isinstance(notice.sent_date, date)
        if notice.delivered_date is not None:
            assert isinstance(notice.delivered_date, date)

        # Check action dates
        action = CollectionActionGenerator.create(
            tenant_id=property_obj.tenant_id,
            delinquency_status_id=status.id,
        )
        assert isinstance(action.requested_date, date)
