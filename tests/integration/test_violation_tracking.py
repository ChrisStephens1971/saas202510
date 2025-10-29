"""
Integration tests for violation tracking functionality.

Tests the complete violation lifecycle including:
- Violation reporting and tracking (7 statuses, 4 severity levels)
- Photo evidence management
- Notice generation and tracking (5 types, 3 delivery methods)
- Hearing scheduling and outcomes (5 possible outcomes)
- Fine assessment and payment tracking
- Cure deadline management
- Status workflow progression
- Data type validation (Decimal precision, date types)
"""

from datetime import date, time, timedelta
from decimal import Decimal

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
    Violation,
    ViolationHearing,
    ViolationNotice,
    ViolationNoticeType,
    ViolationPhoto,
    ViolationSeverity,
    ViolationStatus,
)


class TestViolationCreation:
    """Tests for creating violations."""

    def test_create_basic_violation(self):
        """Test creating a basic violation."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        assert violation.tenant_id == property_obj.tenant_id
        assert violation.owner_id == member.id
        assert violation.status == ViolationStatus.REPORTED
        assert violation.fine_amount == Decimal("0.00")
        assert violation.fine_paid is False

    def test_create_violation_with_unit(self):
        """Test creating a violation associated with a unit."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            unit_id=member.unit_id,
        )

        assert violation.unit_id == member.unit_id

    def test_create_violation_with_severity_levels(self):
        """Test creating violations with different severity levels."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        for severity in ViolationSeverity:
            violation = ViolationGenerator.create(
                tenant_id=property_obj.tenant_id,
                owner_id=member.id,
                severity=severity,
            )

            assert violation.severity == severity

    def test_create_low_severity_violation(self):
        """Test creating a low severity violation."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            severity=ViolationSeverity.LOW,
        )

        assert violation.severity == ViolationSeverity.LOW

    def test_create_critical_severity_violation(self):
        """Test creating a critical severity violation."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            severity=ViolationSeverity.CRITICAL,
        )

        assert violation.severity == ViolationSeverity.CRITICAL

    def test_violation_has_cure_deadline(self):
        """Test that violations are created with cure deadlines."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        # Open violations should have cure deadlines
        if violation.status not in [ViolationStatus.CURED, ViolationStatus.CLOSED]:
            assert violation.cure_deadline is not None
            assert violation.cure_deadline > violation.reported_date


class TestViolationTypes:
    """Tests for different violation types."""

    def test_create_unpainted_fence_violation(self):
        """Test creating an unpainted fence violation."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_by_type(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            violation_type="Unpainted Fence",
        )

        assert violation.violation_type == "Unpainted Fence"
        assert violation.severity == ViolationSeverity.MEDIUM

    def test_create_overgrown_lawn_violation(self):
        """Test creating an overgrown lawn violation."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_by_type(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            violation_type="Overgrown Lawn",
        )

        assert violation.violation_type == "Overgrown Lawn"

    def test_create_health_safety_hazard_violation(self):
        """Test creating a health/safety hazard violation."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_by_type(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            violation_type="Health/Safety Hazard",
        )

        assert violation.violation_type == "Health/Safety Hazard"
        assert violation.severity == ViolationSeverity.CRITICAL


class TestViolationStatusWorkflow:
    """Tests for violation status workflow progression."""

    def test_create_reported_violation(self):
        """Test creating a newly reported violation."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_reported(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        assert violation.status == ViolationStatus.REPORTED
        assert violation.is_open is True

    def test_create_notice_sent_violation(self):
        """Test creating a violation with notice sent."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_notice_sent(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        assert violation.status == ViolationStatus.NOTICE_SENT

    def test_create_pending_cure_violation(self):
        """Test creating a violation pending cure."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_pending_cure(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        assert violation.status == ViolationStatus.PENDING_CURE

    def test_create_cured_violation(self):
        """Test creating a cured violation."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_cured(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        assert violation.status == ViolationStatus.CURED
        assert violation.cured_date is not None
        assert violation.is_open is False

    def test_create_fined_violation(self):
        """Test creating a violation with fine assessed."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_fined(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        assert violation.status == ViolationStatus.FINED
        assert violation.fine_amount > Decimal("0.00")

    def test_violation_is_open_property(self):
        """Test violation is_open property for different statuses."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        # Open statuses
        for status in [ViolationStatus.REPORTED, ViolationStatus.NOTICE_SENT,
                      ViolationStatus.PENDING_CURE, ViolationStatus.HEARING_SCHEDULED,
                      ViolationStatus.FINED]:
            violation = ViolationGenerator.create(
                tenant_id=property_obj.tenant_id,
                owner_id=member.id,
                status=status,
            )
            assert violation.is_open is True

        # Closed statuses
        for status in [ViolationStatus.CURED, ViolationStatus.CLOSED]:
            violation = ViolationGenerator.create(
                tenant_id=property_obj.tenant_id,
                owner_id=member.id,
                status=status,
                cured_date=date.today() if status == ViolationStatus.CURED else None,
            )
            assert violation.is_open is False


class TestViolationFines:
    """Tests for violation fine assessment and tracking."""

    def test_fine_amount_based_on_severity(self):
        """Test that fine amounts vary by severity."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        low_violation = ViolationGenerator.create_fined(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            severity=ViolationSeverity.LOW,
        )

        critical_violation = ViolationGenerator.create_fined(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            severity=ViolationSeverity.CRITICAL,
        )

        # Critical violations should generally have higher fines
        # (Note: This is probabilistic, not guaranteed)
        assert low_violation.fine_amount >= Decimal("25.00")
        assert critical_violation.fine_amount >= Decimal("1000.00")

    def test_fine_amount_precision(self):
        """Test that fine amounts have exactly 2 decimal places."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_fined(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            fine_amount=Decimal("150.99"),
        )

        # Check precision
        assert violation.fine_amount == Decimal("150.99")
        assert str(violation.fine_amount) == "150.99"

    def test_fine_amount_non_negative(self):
        """Test that fine amounts cannot be negative."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        with pytest.raises(ValueError, match="fine_amount must be non-negative"):
            ViolationGenerator.create(
                tenant_id=property_obj.tenant_id,
                owner_id=member.id,
                fine_amount=Decimal("-100.00"),
            )

    def test_fine_paid_status(self):
        """Test tracking whether fine has been paid."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        # Unpaid fine
        violation_unpaid = ViolationGenerator.create_fined(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            fine_paid=False,
        )
        assert violation_unpaid.fine_paid is False

        # Paid fine
        violation_paid = ViolationGenerator.create_fined(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            fine_paid=True,
        )
        assert violation_paid.fine_paid is True


class TestViolationCureDeadlines:
    """Tests for violation cure deadline management."""

    def test_cure_deadline_after_reported_date(self):
        """Test that cure deadline is after reported date."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            reported_date=date.today() - timedelta(days=10),
        )

        if violation.cure_deadline:
            assert violation.cure_deadline > violation.reported_date

    def test_invalid_cure_deadline_raises_error(self):
        """Test that cure deadline before reported date raises error."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        with pytest.raises(ValueError, match="cure_deadline must be after reported_date"):
            ViolationGenerator.create(
                tenant_id=property_obj.tenant_id,
                owner_id=member.id,
                reported_date=date.today(),
                cure_deadline=date.today() - timedelta(days=1),
            )

    def test_overdue_violation(self):
        """Test creating and identifying overdue violations."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_overdue(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        assert violation.cure_deadline is not None
        assert violation.cure_deadline < date.today()
        assert violation.is_overdue is True

    def test_violation_not_overdue_if_no_deadline(self):
        """Test that violations without deadline are not overdue."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
            cure_deadline=None,
        )

        assert violation.is_overdue is False

    def test_violation_not_overdue_if_closed(self):
        """Test that closed violations are not overdue."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_cured(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        # Even if cure_deadline is in the past, closed violations are not overdue
        assert violation.is_overdue is False


class TestViolationPhotos:
    """Tests for violation photo evidence."""

    def test_create_violation_photo(self):
        """Test creating a violation photo."""
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

        assert photo.tenant_id == property_obj.tenant_id
        assert photo.violation_id == violation.id
        assert photo.photo_url != ""
        assert photo.uploaded_by != ""

    def test_photo_url_not_empty(self):
        """Test that photo URL cannot be empty."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        with pytest.raises(ValueError, match="photo_url cannot be empty"):
            ViolationPhotoGenerator.create(
                tenant_id=property_obj.tenant_id,
                violation_id=violation.id,
                photo_url="",
            )

    def test_photo_with_caption(self):
        """Test creating a photo with caption."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        photo = ViolationPhotoGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            caption="Front view of fence violation",
        )

        assert photo.caption == "Front view of fence violation"

    def test_photo_taken_date_is_date_type(self):
        """Test that photo taken_date is date type, not datetime."""
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

        assert isinstance(photo.taken_date, date)
        assert not hasattr(photo.taken_date, "hour")

    def test_multiple_photos_per_violation(self):
        """Test that violations can have multiple photos."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        photos = [
            ViolationPhotoGenerator.create(
                tenant_id=property_obj.tenant_id,
                violation_id=violation.id,
                caption=f"Photo {i+1}",
            )
            for i in range(3)
        ]

        assert len(photos) == 3
        assert all(photo.violation_id == violation.id for photo in photos)


class TestViolationNotices:
    """Tests for violation notice generation and tracking."""

    def test_create_first_notice(self):
        """Test creating a first notice."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        notice = ViolationNoticeGenerator.create_first_notice(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
        )

        assert notice.notice_type == ViolationNoticeType.FIRST_NOTICE
        assert notice.delivery_method == NoticeDeliveryMethod.EMAIL

    def test_create_second_notice(self):
        """Test creating a second notice."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        notice = ViolationNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            notice_type=ViolationNoticeType.SECOND_NOTICE,
        )

        assert notice.notice_type == ViolationNoticeType.SECOND_NOTICE

    def test_create_final_notice(self):
        """Test creating a final notice."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        notice = ViolationNoticeGenerator.create_final_notice(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
        )

        assert notice.notice_type == ViolationNoticeType.FINAL_NOTICE
        assert notice.delivery_method == NoticeDeliveryMethod.CERTIFIED_MAIL

    def test_create_hearing_notice(self):
        """Test creating a hearing notice."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        notice = ViolationNoticeGenerator.create_hearing_notice(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
        )

        assert notice.notice_type == ViolationNoticeType.HEARING_NOTICE
        assert notice.delivery_method == NoticeDeliveryMethod.CERTIFIED_MAIL

    def test_notice_delivery_methods(self):
        """Test different notice delivery methods."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        for delivery_method in NoticeDeliveryMethod:
            notice = ViolationNoticeGenerator.create(
                tenant_id=property_obj.tenant_id,
                violation_id=violation.id,
                delivery_method=delivery_method,
            )

            assert notice.delivery_method == delivery_method

    def test_certified_mail_has_tracking_number(self):
        """Test that certified mail notices have tracking numbers."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        notice = ViolationNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            delivery_method=NoticeDeliveryMethod.CERTIFIED_MAIL,
        )

        assert notice.tracking_number != ""

    def test_notice_delivered_after_sent(self):
        """Test that delivered date is after sent date."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        notice = ViolationNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            delivery_method=NoticeDeliveryMethod.CERTIFIED_MAIL,
        )

        if notice.delivered_date:
            assert notice.delivered_date >= notice.sent_date

    def test_invalid_delivered_date_raises_error(self):
        """Test that delivered date before sent date raises error."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        with pytest.raises(ValueError, match="delivered_date must be after sent_date"):
            ViolationNoticeGenerator.create(
                tenant_id=property_obj.tenant_id,
                violation_id=violation.id,
                sent_date=date.today(),
                delivered_date=date.today() - timedelta(days=1),
            )


class TestViolationHearings:
    """Tests for violation hearing scheduling and outcomes."""

    def test_create_pending_hearing(self):
        """Test creating a pending hearing."""
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
        assert hearing.scheduled_date >= date.today()

    def test_create_upheld_hearing(self):
        """Test creating a hearing where violation was upheld."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        hearing = ViolationHearingGenerator.create_upheld(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            fine_assessed=Decimal("500.00"),
        )

        assert hearing.outcome == HearingOutcome.UPHELD
        assert hearing.fine_assessed == Decimal("500.00")
        assert hearing.is_completed is True
        assert hearing.was_violation_upheld is True

    def test_create_overturned_hearing(self):
        """Test creating a hearing where violation was overturned."""
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
        assert hearing.was_violation_upheld is False

    def test_create_modified_hearing(self):
        """Test creating a hearing where outcome was modified."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        hearing = ViolationHearingGenerator.create_modified(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            fine_assessed=Decimal("250.00"),
        )

        assert hearing.outcome == HearingOutcome.MODIFIED
        assert hearing.fine_assessed > Decimal("0.00")
        assert hearing.was_violation_upheld is True

    def test_hearing_scheduled_time_is_time_type(self):
        """Test that hearing scheduled_time is time type, not datetime."""
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

    def test_hearing_fine_assessed_precision(self):
        """Test that hearing fine_assessed has exactly 2 decimal places."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        hearing = ViolationHearingGenerator.create_upheld(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
            fine_assessed=Decimal("123.45"),
        )

        assert hearing.fine_assessed == Decimal("123.45")
        assert str(hearing.fine_assessed) == "123.45"

    def test_hearing_fine_assessed_non_negative(self):
        """Test that hearing fine_assessed cannot be negative."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        with pytest.raises(ValueError, match="fine_assessed must be non-negative"):
            ViolationHearingGenerator.create(
                tenant_id=property_obj.tenant_id,
                violation_id=violation.id,
                fine_assessed=Decimal("-100.00"),
            )


class TestViolationDataTypes:
    """Tests for data type validation."""

    def test_violation_dates_are_date_type(self):
        """Test that violation dates are date type, not datetime."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        assert isinstance(violation.reported_date, date)
        assert not hasattr(violation.reported_date, "hour")

        if violation.cure_deadline:
            assert isinstance(violation.cure_deadline, date)
            assert not hasattr(violation.cure_deadline, "hour")

        if violation.cured_date:
            assert isinstance(violation.cured_date, date)
            assert not hasattr(violation.cured_date, "hour")

    def test_violation_fine_amount_is_decimal(self):
        """Test that violation fine_amount is Decimal type."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        violation = ViolationGenerator.create_fined(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        assert isinstance(violation.fine_amount, Decimal)
        assert not isinstance(violation.fine_amount, float)

    def test_notice_dates_are_date_type(self):
        """Test that notice dates are date type, not datetime."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)
        violation = ViolationGenerator.create(
            tenant_id=property_obj.tenant_id,
            owner_id=member.id,
        )

        notice = ViolationNoticeGenerator.create(
            tenant_id=property_obj.tenant_id,
            violation_id=violation.id,
        )

        assert isinstance(notice.sent_date, date)
        assert not hasattr(notice.sent_date, "hour")

        if notice.delivered_date:
            assert isinstance(notice.delivered_date, date)
            assert not hasattr(notice.delivered_date, "hour")

    def test_hearing_dates_are_date_type(self):
        """Test that hearing dates are date type, not datetime."""
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

        assert isinstance(hearing.scheduled_date, date)
        assert not hasattr(hearing.scheduled_date, "hour")
