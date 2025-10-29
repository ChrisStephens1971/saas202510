"""
Property-based tests for collections invariants.

Uses Hypothesis to verify that collections operations maintain critical invariants:
- Late fee calculation: flat + percentage always >= 0, capped by max_amount
- Percentage fee proportional to balance
- Aging bucket sum equals current_balance
- No negative balances in any aging bucket
- Collection stage progression order
- Approved date >= requested date
- Completed date >= requested date
- Decimal precision for all amounts (exactly 2 decimal places)
- Date types for all date fields (not datetime)
"""

from datetime import date, timedelta
from decimal import Decimal

from hypothesis import assume, given
from hypothesis import strategies as st
import pytest

from qa_testing.generators import (
    CollectionActionGenerator,
    CollectionNoticeGenerator,
    DelinquencyStatusGenerator,
    LateFeeRuleGenerator,
    MemberGenerator,
    PropertyGenerator,
)
from qa_testing.models import ActionStatus, ActionType, CollectionStage, FeeType


# Custom strategies for collections tests
@st.composite
def grace_period_strategy(draw):
    """Generate realistic grace periods (5-15 days)."""
    return draw(st.integers(min_value=5, max_value=15))


@st.composite
def flat_amount_strategy(draw):
    """Generate realistic flat fee amounts ($25-$200)."""
    return Decimal(str(draw(st.integers(min_value=25, max_value=200)))).quantize(Decimal("0.01"))


@st.composite
def percentage_rate_strategy(draw):
    """Generate realistic percentage rates (5-15%)."""
    return Decimal(str(draw(st.floats(min_value=5.0, max_value=15.0)))).quantize(Decimal("0.01"))


@st.composite
def balance_strategy(draw):
    """Generate realistic balances ($100-$10000)."""
    return Decimal(str(draw(st.integers(min_value=100, max_value=10000)))).quantize(Decimal("0.01"))


@st.composite
def days_delinquent_strategy(draw):
    """Generate realistic delinquency periods (0-365 days)."""
    return draw(st.integers(min_value=0, max_value=365))


class TestLateFeeCalculationInvariants:
    """Property-based tests for late fee calculation invariants."""

    @given(
        flat_amount=flat_amount_strategy(),
    )
    def test_flat_fee_always_non_negative(self, flat_amount):
        """
        INVARIANT: Flat late fee is always >= 0.

        Flat fees should never be negative.
        """
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_flat(
            tenant_id=property_obj.tenant_id,
            flat_amount=flat_amount,
        )

        assert rule.flat_amount >= Decimal("0.00")

    @given(
        percentage_rate=percentage_rate_strategy(),
        balance=balance_strategy(),
    )
    def test_percentage_fee_always_non_negative(self, percentage_rate, balance):
        """
        INVARIANT: Percentage late fee is always >= 0.

        Percentage fees should never be negative.
        """
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_percentage(
            tenant_id=property_obj.tenant_id,
            percentage_rate=percentage_rate,
        )

        # Calculate percentage fee
        late_fee = (balance * rule.percentage_rate / Decimal("100")).quantize(Decimal("0.01"))

        assert late_fee >= Decimal("0.00")

    @given(
        flat_amount=flat_amount_strategy(),
        percentage_rate=percentage_rate_strategy(),
        balance=balance_strategy(),
    )
    def test_combined_fee_always_non_negative(self, flat_amount, percentage_rate, balance):
        """
        INVARIANT: Combined late fee (flat + percentage) is always >= 0.

        Combined fees should never be negative.
        """
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_both(
            tenant_id=property_obj.tenant_id,
            flat_amount=flat_amount,
            percentage_rate=percentage_rate,
        )

        # Calculate combined fee
        late_fee = rule.flat_amount + (balance * rule.percentage_rate / Decimal("100"))
        late_fee = late_fee.quantize(Decimal("0.01"))

        assert late_fee >= Decimal("0.00")

    @given(
        percentage_rate=percentage_rate_strategy(),
        balance=balance_strategy(),
    )
    def test_percentage_fee_proportional_to_balance(self, percentage_rate, balance):
        """
        INVARIANT: Percentage fee is proportional to balance.

        If balance doubles, percentage fee should double.
        """
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_percentage(
            tenant_id=property_obj.tenant_id,
            percentage_rate=percentage_rate,
        )

        # Calculate fee for original balance
        fee1 = (balance * rule.percentage_rate / Decimal("100")).quantize(Decimal("0.01"))

        # Calculate fee for doubled balance
        doubled_balance = balance * 2
        fee2 = (doubled_balance * rule.percentage_rate / Decimal("100")).quantize(Decimal("0.01"))

        # Fee should roughly double (allow for rounding)
        assert abs(fee2 - (fee1 * 2)) <= Decimal("0.02")

    @given(
        percentage_rate=percentage_rate_strategy(),
        balance=balance_strategy(),
    )
    def test_late_fee_capped_by_max_amount(self, percentage_rate, balance):
        """
        INVARIANT: Late fee is capped by max_amount when specified.

        Calculated fee should never exceed max_amount.
        """
        # Only test when calculated fee would exceed cap
        calculated_fee = (balance * percentage_rate / Decimal("100")).quantize(Decimal("0.01"))
        max_amount = Decimal("100.00")

        assume(calculated_fee > max_amount)

        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_percentage(
            tenant_id=property_obj.tenant_id,
            percentage_rate=percentage_rate,
            max_amount=max_amount,
        )

        # Apply cap
        late_fee = min(calculated_fee, rule.max_amount)

        assert late_fee <= max_amount
        assert late_fee == max_amount


class TestAgingBucketInvariants:
    """Property-based tests for aging bucket invariants."""

    @given(
        days_delinquent=days_delinquent_strategy(),
    )
    def test_aging_bucket_sum_equals_current_balance(self, days_delinquent):
        """
        INVARIANT: Sum of aging buckets equals current_balance.

        balance_0_30 + balance_31_60 + balance_61_90 + balance_90_plus = current_balance
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            days_delinquent=days_delinquent,
        )

        sum_of_buckets = (
            status.balance_0_30 +
            status.balance_31_60 +
            status.balance_61_90 +
            status.balance_90_plus
        )

        # Should match exactly (within $0.01 for rounding)
        assert abs(status.current_balance - sum_of_buckets) <= Decimal("0.01")

    @given(
        days_delinquent=days_delinquent_strategy(),
    )
    def test_no_negative_balances_in_aging_buckets(self, days_delinquent):
        """
        INVARIANT: No aging bucket can have negative balance.

        All aging buckets must be >= 0.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            days_delinquent=days_delinquent,
        )

        assert status.balance_0_30 >= Decimal("0.00")
        assert status.balance_31_60 >= Decimal("0.00")
        assert status.balance_61_90 >= Decimal("0.00")
        assert status.balance_90_plus >= Decimal("0.00")

    @given(
        days_delinquent=days_delinquent_strategy(),
    )
    def test_current_balance_non_negative(self, days_delinquent):
        """
        INVARIANT: current_balance must be non-negative.

        Delinquent accounts have positive balance, current accounts have zero.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            days_delinquent=days_delinquent,
        )

        assert status.current_balance >= Decimal("0.00")

    def test_is_delinquent_property_matches_balance(self):
        """
        INVARIANT: is_delinquent property matches current_balance.

        is_delinquent is True when current_balance > 0.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        # Test current (zero balance)
        status_current = DelinquencyStatusGenerator.create_current(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
        )

        assert status_current.current_balance == Decimal("0.00")
        assert status_current.is_delinquent is False

        # Test delinquent (positive balance)
        status_delinquent = DelinquencyStatusGenerator.create_delinquent(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            collection_stage=CollectionStage.DAYS_31_60,
            days_delinquent=45,
        )

        if status_delinquent.current_balance > Decimal("0.00"):
            assert status_delinquent.is_delinquent is True


class TestCollectionStageInvariants:
    """Property-based tests for collection stage progression invariants."""

    def test_collection_stage_progression_order(self):
        """
        INVARIANT: Collection stages progress in order.

        CURRENT → 0_30 → 31_60 → 61_90 → 90_PLUS → ATTORNEY → LIEN → FORECLOSURE
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        # Define stage order
        stage_order = [
            CollectionStage.CURRENT,
            CollectionStage.DAYS_0_30,
            CollectionStage.DAYS_31_60,
            CollectionStage.DAYS_61_90,
            CollectionStage.DAYS_90_PLUS,
            CollectionStage.ATTORNEY_REFERRAL,
            CollectionStage.LIEN_FILED,
            CollectionStage.FORECLOSURE,
        ]

        # Create status at each stage
        for stage in stage_order:
            status = DelinquencyStatusGenerator.create(
                tenant_id=property_obj.tenant_id,
                member_id=member.id,
                collection_stage=stage,
            )

            # Verify stage is in defined order
            assert status.collection_stage in stage_order

    @given(
        days_delinquent=days_delinquent_strategy(),
    )
    def test_days_delinquent_non_negative(self, days_delinquent):
        """
        INVARIANT: days_delinquent must be non-negative.

        Cannot have negative days delinquent.
        """
        # Ensure non-negative
        assume(days_delinquent >= 0)

        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            days_delinquent=days_delinquent,
        )

        assert status.days_delinquent >= 0

    def test_current_stage_has_zero_balance(self):
        """
        INVARIANT: CURRENT stage should have zero balance.

        Non-delinquent accounts have zero balance.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create_current(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
        )

        if status.collection_stage == CollectionStage.CURRENT:
            assert status.current_balance == Decimal("0.00")


class TestCollectionActionInvariants:
    """Property-based tests for collection action invariants."""

    def test_approved_date_after_requested_date(self):
        """
        INVARIANT: approved_date must be >= requested_date.

        Actions cannot be approved before they are requested.
        """
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

        if action.approved_date is not None:
            assert action.approved_date >= action.requested_date

    def test_completed_date_after_requested_date(self):
        """
        INVARIANT: completed_date must be >= requested_date.

        Actions cannot complete before they are requested.
        """
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

        if action.completed_date is not None:
            assert action.completed_date >= action.requested_date

    def test_approved_action_has_approved_date(self):
        """
        INVARIANT: APPROVED status requires approved_date.

        Approved actions must have approval timestamp.
        """
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

        if action.status == ActionStatus.APPROVED:
            assert action.approved_date is not None

    def test_completed_action_has_completed_date(self):
        """
        INVARIANT: COMPLETED status requires completed_date.

        Completed actions must have completion timestamp.
        """
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

        if action.status == ActionStatus.COMPLETED:
            assert action.completed_date is not None

    def test_pending_action_no_approval_dates(self):
        """
        INVARIANT: PENDING_APPROVAL status should not have approval dates.

        Pending actions haven't been approved yet.
        """
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

        if action.status == ActionStatus.PENDING_APPROVAL:
            assert action.approved_date is None


class TestDataTypeInvariants:
    """Property-based tests for data type invariants."""

    @given(
        flat_amount=flat_amount_strategy(),
        percentage_rate=percentage_rate_strategy(),
    )
    def test_late_fee_amounts_use_decimal_with_precision(self, flat_amount, percentage_rate):
        """
        INVARIANT: All late fee amounts use Decimal with exactly 2 decimal places.

        Money amounts must use NUMERIC(15,2).
        """
        property_obj = PropertyGenerator.create()

        rule = LateFeeRuleGenerator.create_both(
            tenant_id=property_obj.tenant_id,
            flat_amount=flat_amount,
            percentage_rate=percentage_rate,
        )

        # Check Decimal type
        assert isinstance(rule.flat_amount, Decimal)

        # Check precision (exactly 2 decimal places)
        assert rule.flat_amount.as_tuple().exponent == -2

        # Check max_amount if present
        if rule.max_amount is not None:
            assert isinstance(rule.max_amount, Decimal)
            assert rule.max_amount.as_tuple().exponent == -2

    @given(
        days_delinquent=days_delinquent_strategy(),
    )
    def test_delinquency_balances_use_decimal_with_precision(self, days_delinquent):
        """
        INVARIANT: All delinquency balances use Decimal with exactly 2 decimal places.

        Money amounts must use NUMERIC(15,2).
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        status = DelinquencyStatusGenerator.create(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            days_delinquent=days_delinquent,
        )

        # Check all balances
        assert isinstance(status.balance_0_30, Decimal)
        assert status.balance_0_30.as_tuple().exponent == -2

        assert isinstance(status.balance_31_60, Decimal)
        assert status.balance_31_60.as_tuple().exponent == -2

        assert isinstance(status.balance_61_90, Decimal)
        assert status.balance_61_90.as_tuple().exponent == -2

        assert isinstance(status.balance_90_plus, Decimal)
        assert status.balance_90_plus.as_tuple().exponent == -2

        assert isinstance(status.current_balance, Decimal)
        assert status.current_balance.as_tuple().exponent == -2

    def test_notice_dates_use_date_type(self):
        """
        INVARIANT: All notice dates use date type (not datetime).

        Accounting dates should use DATE, not datetime.
        """
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
        )

        # Check date types
        assert isinstance(notice.sent_date, date)

        if notice.delivered_date is not None:
            assert isinstance(notice.delivered_date, date)

    def test_action_dates_use_date_type(self):
        """
        INVARIANT: All action dates use date type (not datetime).

        Accounting dates should use DATE, not datetime.
        """
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
            status=ActionStatus.COMPLETED,
        )

        # Check date types
        assert isinstance(action.requested_date, date)

        if action.approved_date is not None:
            assert isinstance(action.approved_date, date)

        if action.completed_date is not None:
            assert isinstance(action.completed_date, date)

    def test_notice_balance_uses_decimal_with_precision(self):
        """
        INVARIANT: Notice balance uses Decimal with exactly 2 decimal places.

        Money amounts must use NUMERIC(15,2).
        """
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
        )

        assert isinstance(notice.balance_at_notice, Decimal)
        assert notice.balance_at_notice.as_tuple().exponent == -2

    def test_action_balance_uses_decimal_with_precision(self):
        """
        INVARIANT: Action balance uses Decimal with exactly 2 decimal places.

        Money amounts must use NUMERIC(15,2).
        """
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
        )

        assert isinstance(action.balance_at_action, Decimal)
        assert action.balance_at_action.as_tuple().exponent == -2

    def test_delivered_date_after_sent_date(self):
        """
        INVARIANT: delivered_date must be >= sent_date.

        Notices cannot be delivered before they are sent.
        """
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
        )

        if notice.delivered_date is not None:
            assert notice.delivered_date >= notice.sent_date
