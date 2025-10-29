"""
Property-based tests for violation tracking invariants.

Uses Hypothesis to verify that violation operations maintain critical invariants:
- Fine amounts always >= 0
- Cure deadline >= reported date
- Cured date >= reported date
- Delivered date >= sent date
- Fine assessed at hearing >= 0
- Decimal precision for all amounts (exactly 2 decimal places)
- Date types for all date fields (not datetime)
- Time types for hearing times (not datetime)
- Status progression order
- Open/closed status consistency
"""

from datetime import date, time, timedelta
from decimal import Decimal

from hypothesis import assume, given
from hypothesis import strategies as st
import pytest

from qa_testing.generators import (
    MemberGenerator,
    PropertyGenerator,
    ViolationGenerator,
    ViolationHearingGenerator,
    ViolationNoticeGenerator,
    ViolationPhotoGenerator,
)
from qa_testing.models import (
    HearingOutcome,
    NoticeDeliveryMethod,
    ViolationNoticeType,
    ViolationSeverity,
    ViolationStatus,
)


# Custom strategies for violation tests
@st.composite
def fine_amount_strategy(draw):
    """Generate realistic fine amounts ($25-$5000)."""
    return Decimal(str(draw(st.integers(min_value=25, max_value=5000)))).quantize(Decimal("0.01"))


@st.composite
def severity_strategy(draw):
    """Generate random severity level."""
    return draw(st.sampled_from(list(ViolationSeverity)))


@st.composite
def status_strategy(draw):
    """Generate random violation status."""
    return draw(st.sampled_from(list(ViolationStatus)))


@st.composite
def days_ago_strategy(draw):
    """Generate realistic days ago (1-365 days)."""
    return draw(st.integers(min_value=1, max_value=365))


@st.composite
def days_to_cure_strategy(draw):
    """Generate realistic cure period (14-30 days)."""
    return draw(st.integers(min_value=14, max_value=30))


class TestViolationFineInvariants:
    """Property-based tests for violation fine invariants."""

    @given(
        fine_amount=fine_amount_strategy(),
    )
    def test_fine_amount_always_non_negative(self, fine_amount):
        """
        INVARIANT: Violation fine amount is always >= 0.

        Fines should never be negative.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            fine_amount=fine_amount,
        )

        assert violation.fine_amount >= Decimal("0.00")

    @given(
        fine_amount=fine_amount_strategy(),
    )
    def test_fine_amount_has_two_decimal_places(self, fine_amount):
        """
        INVARIANT: Fine amounts have exactly 2 decimal places.

        All monetary amounts must be precise to the cent.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            fine_amount=fine_amount,
        )

        # Check that quantization works correctly
        assert violation.fine_amount == fine_amount.quantize(Decimal("0.01"))

        # Check string representation has exactly 2 decimal places
        fine_str = str(violation.fine_amount)
        if "." in fine_str:
            decimal_part = fine_str.split(".")[1]
            assert len(decimal_part) == 2

    @given(
        severity=severity_strategy(),
    )
    def test_fined_violations_have_positive_fine(self, severity):
        """
        INVARIANT: Violations with FINED status have positive fine amounts.

        If status is FINED, fine_amount must be > 0.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_fined(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            severity=severity,
        )

        assert violation.status == ViolationStatus.FINED
        assert violation.fine_amount > Decimal("0.00")


class TestViolationDateInvariants:
    """Property-based tests for violation date invariants."""

    @given(
        days_ago=days_ago_strategy(),
        days_to_cure=days_to_cure_strategy(),
    )
    def test_cure_deadline_after_reported_date(self, days_ago, days_to_cure):
        """
        INVARIANT: Cure deadline is always after reported date.

        Violations cannot have cure deadlines before they were reported.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        reported_date = date.today() - timedelta(days=days_ago)
        cure_deadline = reported_date + timedelta(days=days_to_cure)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            reported_date=reported_date,
            cure_deadline=cure_deadline,
        )

        assert violation.cure_deadline > violation.reported_date

    @given(
        days_ago=days_ago_strategy(),
    )
    def test_cured_date_after_reported_date(self, days_ago):
        """
        INVARIANT: Cured date is always after reported date.

        Violations cannot be cured before they were reported.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        reported_date = date.today() - timedelta(days=days_ago)

        violation = ViolationGenerator.create_cured(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            reported_date=reported_date,
        )

        if violation.cured_date:
            assert violation.cured_date >= violation.reported_date

    @given(
        days_ago=days_ago_strategy(),
    )
    def test_violation_dates_are_date_type_not_datetime(self, days_ago):
        """
        INVARIANT: All violation date fields are date type, not datetime.

        Financial/accounting dates should never include time components.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        reported_date = date.today() - timedelta(days=days_ago)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            reported_date=reported_date,
        )

        # reported_date must be date type
        assert isinstance(violation.reported_date, date)
        assert not hasattr(violation.reported_date, "hour")

        # cure_deadline must be date type (if present)
        if violation.cure_deadline:
            assert isinstance(violation.cure_deadline, date)
            assert not hasattr(violation.cure_deadline, "hour")

        # cured_date must be date type (if present)
        if violation.cured_date:
            assert isinstance(violation.cured_date, date)
            assert not hasattr(violation.cured_date, "hour")


class TestViolationStatusInvariants:
    """Property-based tests for violation status invariants."""

    @given(
        severity=severity_strategy(),
    )
    def test_cured_violations_are_not_open(self, severity):
        """
        INVARIANT: Violations with CURED status are not open.

        Cured violations should be marked as closed.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_cured(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            severity=severity,
        )

        assert violation.status == ViolationStatus.CURED
        assert violation.is_open is False

    @given(
        severity=severity_strategy(),
    )
    def test_closed_violations_are_not_open(self, severity):
        """
        INVARIANT: Violations with CLOSED status are not open.

        Closed violations should be marked as not open.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            status=ViolationStatus.CLOSED,
            severity=severity,
        )

        assert violation.status == ViolationStatus.CLOSED
        assert violation.is_open is False

    @given(
        status=st.sampled_from([
            ViolationStatus.REPORTED,
            ViolationStatus.NOTICE_SENT,
            ViolationStatus.PENDING_CURE,
            ViolationStatus.HEARING_SCHEDULED,
            ViolationStatus.FINED,
        ]),
    )
    def test_non_closed_violations_are_open(self, status):
        """
        INVARIANT: Violations not in CURED or CLOSED status are open.

        All other statuses indicate an open violation.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            status=status,
        )

        assert violation.is_open is True

    @given(
        severity=severity_strategy(),
    )
    def test_cured_violations_have_cured_date(self, severity):
        """
        INVARIANT: Violations with CURED status have cured_date set.

        If status is CURED, cured_date should be present.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_cured(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            severity=severity,
        )

        assert violation.status == ViolationStatus.CURED
        assert violation.cured_date is not None


class TestViolationOverdueInvariants:
    """Property-based tests for violation overdue invariants."""

    @given(
        days_overdue=st.integers(min_value=1, max_value=30),
    )
    def test_overdue_violations_past_deadline(self, days_overdue):
        """
        INVARIANT: Overdue violations have cure deadline in the past.

        If is_overdue is True, cure_deadline must be < today.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        # Reported 60 days ago, cure deadline between reported date and today but in past
        reported_date = date.today() - timedelta(days=60)
        # Cure deadline is days_overdue days ago (but at least 30 days after reported)
        cure_deadline = date.today() - timedelta(days=days_overdue)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            status=ViolationStatus.PENDING_CURE,
            reported_date=reported_date,
            cure_deadline=cure_deadline,
        )

        if violation.is_overdue:
            assert violation.cure_deadline < date.today()

    @given(
        severity=severity_strategy(),
    )
    def test_violations_without_deadline_not_overdue(self, severity):
        """
        INVARIANT: Violations without cure deadline cannot be overdue.

        If cure_deadline is None, is_overdue must be False.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            severity=severity,
            cure_deadline=None,
        )

        assert violation.is_overdue is False

    @given(
        severity=severity_strategy(),
    )
    def test_closed_violations_not_overdue(self, severity):
        """
        INVARIANT: Closed violations cannot be overdue.

        Even if deadline is past, closed violations are not overdue.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            status=ViolationStatus.CLOSED,
            severity=severity,
        )

        assert violation.is_overdue is False


class TestViolationNoticeInvariants:
    """Property-based tests for violation notice invariants."""

    @given(
        notice_type=st.sampled_from(list(ViolationNoticeType)),
        days_ago=days_ago_strategy(),
    )
    def test_notice_delivered_after_sent(self, notice_type, days_ago):
        """
        INVARIANT: Notice delivered date is always after sent date.

        Notices cannot be delivered before they are sent.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        sent_date = date.today() - timedelta(days=days_ago)

        notice = ViolationNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            notice_type=notice_type,
            sent_date=sent_date,
        )

        if notice.delivered_date:
            assert notice.delivered_date >= notice.sent_date

    @given(
        notice_type=st.sampled_from(list(ViolationNoticeType)),
    )
    def test_notice_dates_are_date_type_not_datetime(self, notice_type):
        """
        INVARIANT: All notice date fields are date type, not datetime.

        Date fields should never include time components.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        notice = ViolationNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            notice_type=notice_type,
        )

        # sent_date must be date type
        assert isinstance(notice.sent_date, date)
        assert not hasattr(notice.sent_date, "hour")

        # delivered_date must be date type (if present)
        if notice.delivered_date:
            assert isinstance(notice.delivered_date, date)
            assert not hasattr(notice.delivered_date, "hour")

    @given(
        notice_type=st.sampled_from([
            ViolationNoticeType.FINAL_NOTICE,
            ViolationNoticeType.HEARING_NOTICE,
        ]),
    )
    def test_serious_notices_use_certified_mail(self, notice_type):
        """
        INVARIANT: Final and hearing notices prefer certified mail.

        Serious notices should use certified delivery when possible.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        if notice_type == ViolationNoticeType.FINAL_NOTICE:
            notice = ViolationNoticeGenerator.create_final_notice(
                tenant_id=property_obj.tenant_id,
                violation_id=violation.id,
            )
        else:
            notice = ViolationNoticeGenerator.create_hearing_notice(
                tenant_id=property_obj.tenant_id,
                violation_id=violation.id,
            )

        assert notice.delivery_method == NoticeDeliveryMethod.CERTIFIED_MAIL


class TestViolationHearingInvariants:
    """Property-based tests for violation hearing invariants."""

    @given(
        fine_assessed=fine_amount_strategy(),
    )
    def test_hearing_fine_assessed_always_non_negative(self, fine_assessed):
        """
        INVARIANT: Hearing fine assessed is always >= 0.

        Fines assessed at hearings should never be negative.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        hearing = ViolationHearingGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            fine_assessed=fine_assessed,
        )

        assert hearing.fine_assessed >= Decimal("0.00")

    @given(
        fine_assessed=fine_amount_strategy(),
    )
    def test_hearing_fine_has_two_decimal_places(self, fine_assessed):
        """
        INVARIANT: Hearing fines have exactly 2 decimal places.

        All monetary amounts must be precise to the cent.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        hearing = ViolationHearingGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            fine_assessed=fine_assessed,
        )

        # Check that quantization works correctly
        assert hearing.fine_assessed == fine_assessed.quantize(Decimal("0.01"))

        # Check string representation has exactly 2 decimal places
        fine_str = str(hearing.fine_assessed)
        if "." in fine_str:
            decimal_part = fine_str.split(".")[1]
            assert len(decimal_part) == 2

    def test_hearing_scheduled_time_is_time_type(self):
        """
        INVARIANT: Hearing scheduled_time is time type, not datetime.

        Time fields should be pure time, not datetime.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        hearing = ViolationHearingGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
        )

        assert isinstance(hearing.scheduled_time, time)
        assert not hasattr(hearing.scheduled_time, "year")

    @given(
        outcome=st.sampled_from([
            HearingOutcome.UPHELD,
            HearingOutcome.MODIFIED,
        ]),
    )
    def test_upheld_hearings_have_positive_fine(self, outcome):
        """
        INVARIANT: Hearings where violation is upheld have positive fines.

        If outcome is UPHELD or MODIFIED, fine_assessed should be > 0.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        hearing = ViolationHearingGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            outcome=outcome,
        )

        assert hearing.was_violation_upheld is True
        # Generator should create positive fine for upheld violations
        assert hearing.fine_assessed > Decimal("0.00")

    def test_overturned_hearings_have_zero_fine(self):
        """
        INVARIANT: Overturned violations have zero fine assessed.

        If outcome is OVERTURNED, fine_assessed should be 0.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        hearing = ViolationHearingGenerator.create_overturned(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
        )

        assert hearing.outcome == HearingOutcome.OVERTURNED
        assert hearing.fine_assessed == Decimal("0.00")

    def test_pending_hearings_are_not_completed(self):
        """
        INVARIANT: Pending hearings are not marked as completed.

        If outcome is PENDING, is_completed should be False.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        hearing = ViolationHearingGenerator.create_pending(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
        )

        assert hearing.outcome == HearingOutcome.PENDING
        assert hearing.is_completed is False

    @given(
        outcome=st.sampled_from([
            HearingOutcome.UPHELD,
            HearingOutcome.OVERTURNED,
            HearingOutcome.MODIFIED,
        ]),
    )
    def test_non_pending_hearings_are_completed(self, outcome):
        """
        INVARIANT: Non-pending hearings are marked as completed.

        If outcome is not PENDING, is_completed should be True.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        hearing = ViolationHearingGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            outcome=outcome,
        )

        assert hearing.is_completed is True


class TestViolationPhotoInvariants:
    """Property-based tests for violation photo invariants."""

    @given(
        days_ago=days_ago_strategy(),
    )
    def test_photo_taken_date_is_date_type(self, days_ago):
        """
        INVARIANT: Photo taken_date is date type, not datetime.

        Date fields should never include time components.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        taken_date = date.today() - timedelta(days=days_ago)

        photo = ViolationPhotoGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            taken_date=taken_date,
        )

        assert isinstance(photo.taken_date, date)
        assert not hasattr(photo.taken_date, "hour")

    def test_photo_url_not_empty(self):
        """
        INVARIANT: Photo URL cannot be empty.

        All photos must have a valid URL/path.
        """
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        photo = ViolationPhotoGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
        )

        assert photo.photo_url != ""
        assert len(photo.photo_url) > 0
