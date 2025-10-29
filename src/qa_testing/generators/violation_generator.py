"""Violation tracking data generator for realistic test data."""

from datetime import date, time, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from faker import Faker

# Sentinel value to distinguish between "not provided" and "explicitly None"
_UNSET = object()

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

fake = Faker()


# Common HOA violation types by severity
VIOLATION_TYPES = {
    ViolationSeverity.LOW: [
        "Trash Can Visible From Street",
        "Holiday Decorations Left Up Too Long",
        "Mailbox Needs Paint",
        "Minor Landscaping Issue",
        "Hose Left Out Overnight",
    ],
    ViolationSeverity.MEDIUM: [
        "Unpainted Fence",
        "Overgrown Lawn",
        "Dead Plants in Front Yard",
        "Unauthorized Paint Color",
        "Exterior Repairs Needed",
        "Unauthorized Storage Shed",
        "Weeds in Driveway",
    ],
    ViolationSeverity.HIGH: [
        "Major Structural Damage",
        "Unauthorized Addition",
        "Commercial Vehicle Parked Overnight",
        "Roof Repair Overdue",
        "Broken Windows",
        "Large Fence Violation",
    ],
    ViolationSeverity.CRITICAL: [
        "Health/Safety Hazard",
        "Illegal Activity",
        "Severe Property Damage",
        "Fire Hazard",
        "Code Violation",
    ],
}


class ViolationGenerator:
    """
    Generator for creating realistic Violation test data.

    Usage:
        # Create a new violation
        violation = ViolationGenerator.create(
            tenant_id=tenant.id,
            owner_id=owner.id,
            severity=ViolationSeverity.MEDIUM
        )

        # Create with specific violation type
        violation = ViolationGenerator.create_by_type(
            tenant_id=tenant.id,
            owner_id=owner.id,
            violation_type="Unpainted Fence"
        )

        # Create at specific status
        violation = ViolationGenerator.create_fined(
            tenant_id=tenant.id,
            owner_id=owner.id
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        owner_id: UUID,
        unit_id: Optional[UUID] = None,
        violation_type: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        severity: Optional[ViolationSeverity] = None,
        status: Optional[ViolationStatus] = None,
        reported_date: Optional[date] = None,
        reported_by: Optional[str] = None,
        cure_deadline = _UNSET,
        cured_date: Optional[date] = None,
        fine_amount: Optional[Decimal] = None,
        fine_paid: bool = False,
        notes: str = "",
    ) -> Violation:
        """
        Create a violation with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            owner_id: Owner ID (required)
            unit_id: Unit ID (optional)
            violation_type: Type of violation (generates based on severity)
            description: Detailed description (generates if not provided)
            location: Specific location (generates if not provided)
            severity: Severity level (random if not provided)
            status: Current status (REPORTED if not provided)
            reported_date: Date reported (generates if not provided)
            reported_by: Who reported (generates if not provided)
            cure_deadline: Cure deadline (generates if not provided)
            cured_date: Date cured (generates if status is CURED)
            fine_amount: Fine amount (generates if status is FINED)
            fine_paid: Whether fine is paid
            notes: Internal notes

        Returns:
            Violation instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Select random severity if not provided
        if severity is None:
            severity = fake.random.choice(list(ViolationSeverity))

        # Select violation type based on severity
        if violation_type is None:
            violation_type = fake.random.choice(VIOLATION_TYPES[severity])

        # Generate description
        if description is None:
            description = f"{violation_type} observed at property. {fake.sentence()}"

        # Generate location
        if location is None:
            locations = ["Front Yard", "Back Yard", "Side Yard", "Driveway", "Exterior", "Fence Line"]
            location = fake.random.choice(locations)

        # Default status
        if status is None:
            status = ViolationStatus.REPORTED

        # Generate reported date (within last 90 days)
        if reported_date is None:
            days_ago = fake.random.randint(1, 90)
            reported_date = date.today() - timedelta(days=days_ago)

        # Generate reporter
        if reported_by is None:
            reporters = [
                "HOA Board Member",
                "Property Manager",
                "Neighbor Complaint",
                "Routine Inspection",
                f"{fake.first_name()} {fake.last_name()}",
            ]
            reported_by = fake.random.choice(reporters)

        # Generate cure deadline (typically 14-30 days from report)
        # Use _UNSET to distinguish "not provided" from "explicitly None"
        if cure_deadline is _UNSET:
            # Not provided - generate if status is appropriate
            if status not in [ViolationStatus.CURED, ViolationStatus.CLOSED]:
                days_to_cure = fake.random.randint(14, 30)
                cure_deadline = reported_date + timedelta(days=days_to_cure)
            else:
                cure_deadline = None
        # else: use the value provided by caller (including None)

        # Generate cured date if status is CURED
        if cured_date is None and status == ViolationStatus.CURED:
            if cure_deadline:
                # Cured within deadline (80% of the time)
                if fake.random.random() < 0.8:
                    days_to_cure = fake.random.randint(7, (cure_deadline - reported_date).days)
                else:
                    days_to_cure = fake.random.randint((cure_deadline - reported_date).days, 60)
            else:
                days_to_cure = fake.random.randint(7, 30)
            cured_date = reported_date + timedelta(days=days_to_cure)

        # Generate fine amount if status is FINED
        if fine_amount is None and status == ViolationStatus.FINED:
            # Fine amounts based on severity
            fine_ranges = {
                ViolationSeverity.LOW: (25, 100),
                ViolationSeverity.MEDIUM: (100, 500),
                ViolationSeverity.HIGH: (500, 2000),
                ViolationSeverity.CRITICAL: (1000, 5000),
            }
            min_fine, max_fine = fine_ranges[severity]
            fine_amount = Decimal(str(fake.random.randint(min_fine, max_fine))).quantize(Decimal("0.01"))
        elif fine_amount is None:
            fine_amount = Decimal("0.00")

        return Violation(
            tenant_id=tenant_id,
            owner_id=owner_id,
            unit_id=unit_id,
            violation_type=violation_type,
            description=description,
            location=location,
            severity=severity,
            status=status,
            reported_date=reported_date,
            reported_by=reported_by,
            cure_deadline=cure_deadline,
            cured_date=cured_date,
            fine_amount=fine_amount,
            fine_paid=fine_paid,
            notes=notes,
        )

    @staticmethod
    def create_by_type(
        *,
        tenant_id: Optional[UUID] = None,
        owner_id: UUID,
        violation_type: str,
    ) -> Violation:
        """Create a violation with specific type."""
        # Determine severity from violation type
        severity = ViolationSeverity.MEDIUM
        for sev, types in VIOLATION_TYPES.items():
            if violation_type in types:
                severity = sev
                break

        return ViolationGenerator.create(
            tenant_id=tenant_id,
            owner_id=owner_id,
            violation_type=violation_type,
            severity=severity,
        )

    @staticmethod
    def create_reported(
        *,
        tenant_id: Optional[UUID] = None,
        owner_id: UUID,
        severity: Optional[ViolationSeverity] = None,
    ) -> Violation:
        """Create a newly reported violation."""
        return ViolationGenerator.create(
            tenant_id=tenant_id,
            owner_id=owner_id,
            severity=severity,
            status=ViolationStatus.REPORTED,
        )

    @staticmethod
    def create_notice_sent(
        *,
        tenant_id: Optional[UUID] = None,
        owner_id: UUID,
        severity: Optional[ViolationSeverity] = None,
    ) -> Violation:
        """Create a violation with notice sent."""
        return ViolationGenerator.create(
            tenant_id=tenant_id,
            owner_id=owner_id,
            severity=severity,
            status=ViolationStatus.NOTICE_SENT,
        )

    @staticmethod
    def create_pending_cure(
        *,
        tenant_id: Optional[UUID] = None,
        owner_id: UUID,
        severity: Optional[ViolationSeverity] = None,
    ) -> Violation:
        """Create a violation pending cure."""
        return ViolationGenerator.create(
            tenant_id=tenant_id,
            owner_id=owner_id,
            severity=severity,
            status=ViolationStatus.PENDING_CURE,
        )

    @staticmethod
    def create_cured(
        *,
        tenant_id: Optional[UUID] = None,
        owner_id: UUID,
        severity: Optional[ViolationSeverity] = None,
        reported_date: Optional[date] = None,
    ) -> Violation:
        """Create a cured violation."""
        return ViolationGenerator.create(
            tenant_id=tenant_id,
            owner_id=owner_id,
            severity=severity,
            status=ViolationStatus.CURED,
            reported_date=reported_date,
        )

    @staticmethod
    def create_fined(
        *,
        tenant_id: Optional[UUID] = None,
        owner_id: UUID,
        severity: Optional[ViolationSeverity] = None,
        fine_amount: Optional[Decimal] = None,
        fine_paid: bool = False,
    ) -> Violation:
        """Create a violation with fine assessed."""
        return ViolationGenerator.create(
            tenant_id=tenant_id,
            owner_id=owner_id,
            severity=severity,
            status=ViolationStatus.FINED,
            fine_amount=fine_amount,
            fine_paid=fine_paid,
        )

    @staticmethod
    def create_overdue(
        *,
        tenant_id: Optional[UUID] = None,
        owner_id: UUID,
        severity: Optional[ViolationSeverity] = None,
    ) -> Violation:
        """Create an overdue violation (past cure deadline)."""
        reported_date = date.today() - timedelta(days=60)
        cure_deadline = date.today() - timedelta(days=10)  # Past deadline

        return ViolationGenerator.create(
            tenant_id=tenant_id,
            owner_id=owner_id,
            severity=severity,
            status=ViolationStatus.PENDING_CURE,
            reported_date=reported_date,
            cure_deadline=cure_deadline,
        )


class ViolationPhotoGenerator:
    """
    Generator for creating realistic ViolationPhoto test data.

    Usage:
        # Create a photo
        photo = ViolationPhotoGenerator.create(
            tenant_id=tenant.id,
            violation_id=violation.id
        )

        # Create with specific URL
        photo = ViolationPhotoGenerator.create(
            tenant_id=tenant.id,
            violation_id=violation.id,
            photo_url="https://s3.amazonaws.com/hoa-photos/violation-123.jpg"
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        violation_id: UUID,
        photo_url: Optional[str] = None,
        caption: Optional[str] = None,
        taken_date: Optional[date] = None,
        uploaded_by: Optional[str] = None,
    ) -> ViolationPhoto:
        """
        Create a violation photo with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            violation_id: Associated violation (required)
            photo_url: URL to photo (generates if not provided)
            caption: Photo caption (generates if not provided)
            taken_date: Date photo was taken (generates if not provided)
            uploaded_by: Who uploaded photo (generates if not provided)

        Returns:
            ViolationPhoto instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Generate photo URL
        if photo_url is None:
            storage_providers = [
                f"https://s3.amazonaws.com/hoa-photos/{uuid4()}.jpg",
                f"https://cdn.cloudflare.com/hoa/{uuid4()}.jpg",
                f"https://storage.googleapis.com/hoa-violations/{uuid4()}.jpg",
            ]
            photo_url = fake.random.choice(storage_providers)

        # Generate caption
        if caption is None:
            captions = [
                "Front view of violation",
                "Close-up of issue",
                "Overview of property condition",
                "Detail showing non-compliance",
                "Photo taken during inspection",
                "",  # Some photos have no caption
            ]
            caption = fake.random.choice(captions)

        # Generate taken date (within last 30 days)
        if taken_date is None:
            days_ago = fake.random.randint(1, 30)
            taken_date = date.today() - timedelta(days=days_ago)

        # Generate uploader
        if uploaded_by is None:
            uploaders = [
                "Property Manager",
                "HOA Board Member",
                f"{fake.first_name()} {fake.last_name()}",
                "Inspection Team",
            ]
            uploaded_by = fake.random.choice(uploaders)

        return ViolationPhoto(
            tenant_id=tenant_id,
            violation_id=violation_id,
            photo_url=photo_url,
            caption=caption,
            taken_date=taken_date,
            uploaded_by=uploaded_by,
        )


class ViolationNoticeGenerator:
    """
    Generator for creating realistic ViolationNotice test data.

    Usage:
        # Create first notice
        notice = ViolationNoticeGenerator.create_first_notice(
            tenant_id=tenant.id,
            violation_id=violation.id
        )

        # Create final notice with certified mail
        notice = ViolationNoticeGenerator.create_final_notice(
            tenant_id=tenant.id,
            violation_id=violation.id,
            delivery_method=NoticeDeliveryMethod.CERTIFIED_MAIL
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        violation_id: UUID,
        notice_type: Optional[ViolationNoticeType] = None,
        sent_date: Optional[date] = None,
        delivery_method: Optional[NoticeDeliveryMethod] = None,
        tracking_number: str = "",
        delivered_date: Optional[date] = None,
        notes: str = "",
    ) -> ViolationNotice:
        """
        Create a violation notice with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            violation_id: Associated violation (required)
            notice_type: Type of notice (random if not provided)
            sent_date: Date sent (generates if not provided)
            delivery_method: Delivery method (random if not provided)
            tracking_number: Tracking number (generates for certified mail)
            delivered_date: Date delivered (generates if not provided)
            notes: Notes about notice

        Returns:
            ViolationNotice instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Select random notice type if not provided
        if notice_type is None:
            notice_type = fake.random.choice(list(ViolationNoticeType))

        # Generate sent date (within last 60 days)
        if sent_date is None:
            days_ago = fake.random.randint(1, 60)
            sent_date = date.today() - timedelta(days=days_ago)

        # Select delivery method (prefer certified mail for serious notices)
        if delivery_method is None:
            if notice_type in [ViolationNoticeType.FINAL_NOTICE, ViolationNoticeType.HEARING_NOTICE]:
                delivery_method = NoticeDeliveryMethod.CERTIFIED_MAIL
            else:
                delivery_method = fake.random.choice([
                    NoticeDeliveryMethod.EMAIL,
                    NoticeDeliveryMethod.REGULAR_MAIL
                ])

        # Generate tracking number for certified mail
        if not tracking_number and delivery_method == NoticeDeliveryMethod.CERTIFIED_MAIL:
            tracking_number = fake.bothify(text="??########US", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ")

        # Generate delivered date (3-7 days after sent for mail)
        if delivered_date is None and delivery_method in [
            NoticeDeliveryMethod.CERTIFIED_MAIL,
            NoticeDeliveryMethod.REGULAR_MAIL
        ]:
            days_to_deliver = fake.random.randint(3, 7)
            delivered_date = sent_date + timedelta(days=days_to_deliver)

        return ViolationNotice(
            tenant_id=tenant_id,
            violation_id=violation_id,
            notice_type=notice_type,
            sent_date=sent_date,
            delivery_method=delivery_method,
            tracking_number=tracking_number,
            delivered_date=delivered_date,
            notes=notes,
        )

    @staticmethod
    def create_first_notice(
        *,
        tenant_id: Optional[UUID] = None,
        violation_id: UUID,
        delivery_method: Optional[NoticeDeliveryMethod] = None,
    ) -> ViolationNotice:
        """Create a first notice."""
        return ViolationNoticeGenerator.create(
            tenant_id=tenant_id,
            violation_id=violation_id,
            notice_type=ViolationNoticeType.FIRST_NOTICE,
            delivery_method=delivery_method or NoticeDeliveryMethod.EMAIL,
        )

    @staticmethod
    def create_final_notice(
        *,
        tenant_id: Optional[UUID] = None,
        violation_id: UUID,
        delivery_method: Optional[NoticeDeliveryMethod] = None,
    ) -> ViolationNotice:
        """Create a final notice."""
        return ViolationNoticeGenerator.create(
            tenant_id=tenant_id,
            violation_id=violation_id,
            notice_type=ViolationNoticeType.FINAL_NOTICE,
            delivery_method=delivery_method or NoticeDeliveryMethod.CERTIFIED_MAIL,
        )

    @staticmethod
    def create_hearing_notice(
        *,
        tenant_id: Optional[UUID] = None,
        violation_id: UUID,
        delivery_method: Optional[NoticeDeliveryMethod] = None,
    ) -> ViolationNotice:
        """Create a hearing notice."""
        return ViolationNoticeGenerator.create(
            tenant_id=tenant_id,
            violation_id=violation_id,
            notice_type=ViolationNoticeType.HEARING_NOTICE,
            delivery_method=delivery_method or NoticeDeliveryMethod.CERTIFIED_MAIL,
        )


class ViolationHearingGenerator:
    """
    Generator for creating realistic ViolationHearing test data.

    Usage:
        # Create a pending hearing
        hearing = ViolationHearingGenerator.create(
            tenant_id=tenant.id,
            violation_id=violation.id
        )

        # Create a completed hearing with outcome
        hearing = ViolationHearingGenerator.create_upheld(
            tenant_id=tenant.id,
            violation_id=violation.id,
            fine_assessed=Decimal("500.00")
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        violation_id: UUID,
        scheduled_date: Optional[date] = None,
        scheduled_time: Optional[time] = None,
        location: Optional[str] = None,
        outcome: Optional[HearingOutcome] = None,
        outcome_notes: str = "",
        fine_assessed: Optional[Decimal] = None,
    ) -> ViolationHearing:
        """
        Create a violation hearing with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            violation_id: Associated violation (required)
            scheduled_date: Date hearing is scheduled (generates if not provided)
            scheduled_time: Time of hearing (generates if not provided)
            location: Hearing location (generates if not provided)
            outcome: Hearing outcome (PENDING if not provided)
            outcome_notes: Details of outcome
            fine_assessed: Fine amount assessed (generates if outcome is UPHELD)

        Returns:
            ViolationHearing instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Generate scheduled date (within next 60 days for pending, past 30 days for completed)
        if scheduled_date is None:
            if outcome == HearingOutcome.PENDING or outcome is None:
                days_ahead = fake.random.randint(7, 60)
                scheduled_date = date.today() + timedelta(days=days_ahead)
            else:
                days_ago = fake.random.randint(1, 30)
                scheduled_date = date.today() - timedelta(days=days_ago)

        # Generate scheduled time (typically business hours)
        if scheduled_time is None:
            hour = fake.random.randint(9, 17)
            minute = fake.random.choice([0, 15, 30, 45])
            scheduled_time = time(hour=hour, minute=minute)

        # Generate location
        if location is None:
            locations = [
                "HOA Community Center - Board Room",
                "Virtual Meeting - Zoom Link: https://zoom.us/j/...",
                "HOA Office - Conference Room",
                "Community Clubhouse",
                f"{fake.street_address()} - Meeting Room",
            ]
            location = fake.random.choice(locations)

        # Default outcome
        if outcome is None:
            outcome = HearingOutcome.PENDING

        # Generate fine assessed if outcome is UPHELD
        if fine_assessed is None and outcome in [HearingOutcome.UPHELD, HearingOutcome.MODIFIED]:
            fine_assessed = Decimal(str(fake.random.randint(100, 2000))).quantize(Decimal("0.01"))
        elif fine_assessed is None:
            fine_assessed = Decimal("0.00")

        return ViolationHearing(
            tenant_id=tenant_id,
            violation_id=violation_id,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            location=location,
            outcome=outcome,
            outcome_notes=outcome_notes,
            fine_assessed=fine_assessed,
        )

    @staticmethod
    def create_pending(
        *,
        tenant_id: Optional[UUID] = None,
        violation_id: UUID,
    ) -> ViolationHearing:
        """Create a pending hearing."""
        return ViolationHearingGenerator.create(
            tenant_id=tenant_id,
            violation_id=violation_id,
            outcome=HearingOutcome.PENDING,
        )

    @staticmethod
    def create_upheld(
        *,
        tenant_id: Optional[UUID] = None,
        violation_id: UUID,
        fine_assessed: Optional[Decimal] = None,
    ) -> ViolationHearing:
        """Create a hearing where violation was upheld."""
        return ViolationHearingGenerator.create(
            tenant_id=tenant_id,
            violation_id=violation_id,
            outcome=HearingOutcome.UPHELD,
            fine_assessed=fine_assessed,
            outcome_notes="Board voted to uphold violation and assess fine.",
        )

    @staticmethod
    def create_overturned(
        *,
        tenant_id: Optional[UUID] = None,
        violation_id: UUID,
    ) -> ViolationHearing:
        """Create a hearing where violation was overturned."""
        return ViolationHearingGenerator.create(
            tenant_id=tenant_id,
            violation_id=violation_id,
            outcome=HearingOutcome.OVERTURNED,
            fine_assessed=Decimal("0.00"),
            outcome_notes="Board voted to overturn violation. No fine assessed.",
        )

    @staticmethod
    def create_modified(
        *,
        tenant_id: Optional[UUID] = None,
        violation_id: UUID,
        fine_assessed: Optional[Decimal] = None,
    ) -> ViolationHearing:
        """Create a hearing where outcome was modified."""
        return ViolationHearingGenerator.create(
            tenant_id=tenant_id,
            violation_id=violation_id,
            outcome=HearingOutcome.MODIFIED,
            fine_assessed=fine_assessed,
            outcome_notes="Board modified violation terms and reduced fine amount.",
        )
