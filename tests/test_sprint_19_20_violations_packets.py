"""
Comprehensive tests for Sprint 19 (Violations) and Sprint 20 (Board Packets)

Sprint 19 Tests:
- Violation tracking workflow
- Photo evidence storage
- Notice generation
- Hearing management
- Fine assessment

Sprint 20 Tests:
- Board packet template management
- Packet generation workflow
- Section management
- PDF generation placeholder
"""

import pytest
from decimal import Decimal
from datetime import date, time, timedelta


# ===========================
# Sprint 19: Violation Tests
# ===========================

class TestViolations:
    """Test violation tracking and workflow"""

    @pytest.fixture
    def owner(self, db, tenant):
        """Create a test owner"""
        from accounting.models import Owner
        return Owner.objects.create(
            tenant=tenant,
            full_name="John Violator",
            property_address="123 Violation Lane",
            email="john@example.com"
        )

    def test_create_violation(self, db, tenant, owner):
        """Test creating a violation"""
        from accounting.models import Violation

        violation = Violation.objects.create(
            tenant=tenant,
            owner=owner,
            violation_type="Unpainted fence",
            severity='moderate',
            status='reported',
            reported_date=date.today(),
            fine_amount=Decimal('100.00'),
            description="Front fence needs painting per CC&Rs"
        )

        assert violation.severity == 'moderate'
        assert violation.status == 'reported'
        assert not violation.is_paid

    def test_violation_workflow_progression(self, db, tenant, owner):
        """Test violation progresses through workflow"""
        from accounting.models import Violation

        violation = Violation.objects.create(
            tenant=tenant,
            owner=owner,
            violation_type="Lawn maintenance",
            severity='minor',
            status='reported',
            reported_date=date.today(),
            fine_amount=Decimal('50.00')
        )

        # Send notice
        violation.status = 'notice_sent'
        violation.first_notice_date = date.today()
        violation.save()

        violation.refresh_from_db()
        assert violation.status == 'notice_sent'

        # Schedule hearing
        violation.status = 'hearing_scheduled'
        violation.save()

        violation.refresh_from_db()
        assert violation.status == 'hearing_scheduled'

        # Resolve
        violation.status = 'resolved'
        violation.compliance_date = date.today() + timedelta(days=14)
        violation.save()

        violation.refresh_from_db()
        assert violation.status == 'resolved'

    def test_severity_levels(self, db, tenant, owner):
        """Test all severity levels"""
        from accounting.models import Violation

        severities = ['minor', 'moderate', 'major', 'critical']

        for severity in severities:
            violation = Violation.objects.create(
                tenant=tenant,
                owner=owner,
                violation_type=f"{severity.capitalize()} violation",
                severity=severity,
                status='reported',
                reported_date=date.today(),
                fine_amount=Decimal('100.00')
            )
            assert violation.severity == severity


class TestViolationPhotos:
    """Test violation photo evidence"""

    @pytest.fixture
    def violation(self, db, tenant):
        """Create a test violation"""
        from accounting.models import Violation, Owner
        owner = Owner.objects.create(
            tenant=tenant,
            full_name="Test Owner",
            property_address="456 Test St"
        )
        return Violation.objects.create(
            tenant=tenant,
            owner=owner,
            violation_type="Test violation",
            severity='moderate',
            status='reported',
            reported_date=date.today(),
            fine_amount=Decimal('100.00')
        )

    def test_add_photo_evidence(self, db, tenant, violation):
        """Test adding photo evidence to violation"""
        from accounting.models import ViolationPhoto

        photo = ViolationPhoto.objects.create(
            tenant=tenant,
            violation=violation,
            photo_url="https://example.com/photos/violation1.jpg",
            caption="Front view of unpainted fence",
            taken_date=date.today()
        )

        assert photo.violation == violation
        assert "violation1.jpg" in photo.photo_url

    def test_multiple_photos(self, db, tenant, violation):
        """Test multiple photos per violation"""
        from accounting.models import ViolationPhoto

        for i in range(3):
            ViolationPhoto.objects.create(
                tenant=tenant,
                violation=violation,
                photo_url=f"https://example.com/photos/violation{i}.jpg",
                caption=f"Photo {i+1}",
                taken_date=date.today()
            )

        photos = ViolationPhoto.objects.filter(violation=violation)
        assert photos.count() == 3


class TestViolationNotices:
    """Test violation notice workflow"""

    @pytest.fixture
    def violation(self, db, tenant):
        """Create a test violation"""
        from accounting.models import Violation, Owner
        owner = Owner.objects.create(
            tenant=tenant,
            full_name="Test Owner",
            property_address="789 Test Ave"
        )
        return Violation.objects.create(
            tenant=tenant,
            owner=owner,
            violation_type="Test violation",
            severity='moderate',
            status='reported',
            reported_date=date.today(),
            fine_amount=Decimal('100.00')
        )

    def test_send_violation_notice(self, db, tenant, violation):
        """Test sending a violation notice"""
        from accounting.models import ViolationNotice

        notice = ViolationNotice.objects.create(
            tenant=tenant,
            violation=violation,
            notice_type='first',
            delivery_method='email',
            sent_date=date.today(),
            cure_deadline=date.today() + timedelta(days=14)
        )

        assert notice.notice_type == 'first'
        assert notice.cure_deadline > notice.sent_date

    def test_notice_tracking(self, db, tenant, violation):
        """Test tracking multiple notices"""
        from accounting.models import ViolationNotice

        # First notice
        ViolationNotice.objects.create(
            tenant=tenant,
            violation=violation,
            notice_type='first',
            delivery_method='email',
            sent_date=date.today(),
            cure_deadline=date.today() + timedelta(days=14)
        )

        # Second notice
        ViolationNotice.objects.create(
            tenant=tenant,
            violation=violation,
            notice_type='second',
            delivery_method='certified_mail',
            sent_date=date.today() + timedelta(days=14),
            cure_deadline=date.today() + timedelta(days=28),
            tracking_number="1234567890"
        )

        notices = ViolationNotice.objects.filter(violation=violation)
        assert notices.count() == 2


class TestViolationHearings:
    """Test violation hearing management"""

    @pytest.fixture
    def violation(self, db, tenant):
        """Create a test violation"""
        from accounting.models import Violation, Owner
        owner = Owner.objects.create(
            tenant=tenant,
            full_name="Test Owner",
            property_address="321 Hearing St"
        )
        return Violation.objects.create(
            tenant=tenant,
            owner=owner,
            violation_type="Serious violation",
            severity='major',
            status='hearing_scheduled',
            reported_date=date.today(),
            fine_amount=Decimal('500.00')
        )

    def test_schedule_hearing(self, db, tenant, violation):
        """Test scheduling a violation hearing"""
        from accounting.models import ViolationHearing

        hearing = ViolationHearing.objects.create(
            tenant=tenant,
            violation=violation,
            scheduled_date=date.today() + timedelta(days=30),
            scheduled_time=time(18, 0),  # 6:00 PM
            location="Community Center Room B",
            attendees=["Board President", "Owner", "Board Secretary"]
        )

        assert hearing.scheduled_date > date.today()
        assert len(hearing.attendees) == 3

    def test_hearing_outcome(self, db, tenant, violation):
        """Test recording hearing outcome"""
        from accounting.models import ViolationHearing

        hearing = ViolationHearing.objects.create(
            tenant=tenant,
            violation=violation,
            scheduled_date=date.today(),
            scheduled_time=time(18, 0),
            location="Community Center",
            outcome='upheld',
            fine_assessed=Decimal('500.00'),
            compliance_deadline=date.today() + timedelta(days=30),
            hearing_notes="Board voted 3-0 to uphold violation. Owner given 30 days to cure."
        )

        assert hearing.outcome == 'upheld'
        assert hearing.fine_assessed == Decimal('500.00')


# ===========================
# Sprint 20: Board Packet Tests
# ===========================

class TestBoardPacketTemplates:
    """Test board packet template management"""

    def test_create_template(self, db, tenant):
        """Test creating a board packet template"""
        from accounting.models import BoardPacketTemplate

        template = BoardPacketTemplate.objects.create(
            tenant=tenant,
            name="Standard Monthly Board Packet",
            description="Standard template for monthly board meetings",
            sections=['cover', 'agenda', 'minutes', 'financials', 'ar_aging'],
            section_order=['cover', 'agenda', 'minutes', 'financials', 'ar_aging'],
            include_cover_page=True,
            is_default=True
        )

        assert template.is_default
        assert len(template.sections) == 5

    def test_template_customization(self, db, tenant):
        """Test custom template with specific sections"""
        from accounting.models import BoardPacketTemplate

        template = BoardPacketTemplate.objects.create(
            tenant=tenant,
            name="Financial Review Packet",
            description="Template for financial review meetings",
            sections=['cover', 'trial_balance', 'cash_flow', 'budget_variance', 'reserve_study'],
            include_cover_page=True,
            header_text="Monthly Financial Review",
            footer_text="Confidential - Board Members Only"
        )

        assert "trial_balance" in template.sections
        assert template.header_text == "Monthly Financial Review"


class TestBoardPackets:
    """Test board packet generation and management"""

    @pytest.fixture
    def template(self, db, tenant):
        """Create a test template"""
        from accounting.models import BoardPacketTemplate
        return BoardPacketTemplate.objects.create(
            tenant=tenant,
            name="Test Template",
            sections=['cover', 'agenda', 'financials'],
            include_cover_page=True
        )

    def test_create_board_packet(self, db, tenant, template):
        """Test creating a board packet"""
        from accounting.models import BoardPacket

        packet = BoardPacket.objects.create(
            tenant=tenant,
            template=template,
            meeting_date=date.today() + timedelta(days=7),
            status='draft',
            generated_by="Board Secretary"
        )

        assert packet.status == 'draft'
        assert packet.meeting_date > date.today()

    def test_packet_status_workflow(self, db, tenant, template):
        """Test packet status progression"""
        from accounting.models import BoardPacket

        packet = BoardPacket.objects.create(
            tenant=tenant,
            template=template,
            meeting_date=date.today(),
            status='draft'
        )

        # Generate
        packet.status = 'generating'
        packet.save()
        assert packet.status == 'generating'

        # Ready
        packet.status = 'ready'
        packet.pdf_url = "https://example.com/packets/packet1.pdf"
        packet.page_count = 25
        packet.save()
        assert packet.status == 'ready'
        assert packet.pdf_url is not None

        # Sent
        packet.status = 'sent'
        packet.sent_to = ["board@example.com"]
        packet.sent_at = date.today()
        packet.save()
        assert packet.status == 'sent'


class TestPacketSections:
    """Test packet section management"""

    @pytest.fixture
    def packet(self, db, tenant):
        """Create a test packet"""
        from accounting.models import BoardPacket, BoardPacketTemplate
        template = BoardPacketTemplate.objects.create(
            tenant=tenant,
            name="Test",
            sections=['cover', 'agenda']
        )
        return BoardPacket.objects.create(
            tenant=tenant,
            template=template,
            meeting_date=date.today(),
            status='draft'
        )

    def test_add_section(self, db, tenant, packet):
        """Test adding a section to packet"""
        from accounting.models import PacketSection

        section = PacketSection.objects.create(
            tenant=tenant,
            packet=packet,
            section_type='agenda',
            title="Board Meeting Agenda",
            order=1
        )

        assert section.section_type == 'agenda'
        assert section.order == 1

    def test_section_ordering(self, db, tenant, packet):
        """Test sections maintain order"""
        from accounting.models import PacketSection

        sections_data = [
            ('cover', 'Cover Page', 0),
            ('agenda', 'Meeting Agenda', 1),
            ('minutes', 'Previous Minutes', 2),
            ('financials', 'Financial Summary', 3),
        ]

        for section_type, title, order in sections_data:
            PacketSection.objects.create(
                tenant=tenant,
                packet=packet,
                section_type=section_type,
                title=title,
                order=order
            )

        sections = PacketSection.objects.filter(packet=packet).order_by('order')
        assert sections.count() == 4
        assert sections[0].section_type == 'cover'
        assert sections[3].section_type == 'financials'


class TestBoardPacketIntegration:
    """Integration tests for board packet workflow"""

    def test_full_packet_generation_workflow(self, db, tenant):
        """Test complete workflow from template to sent packet"""
        from accounting.models import (
            BoardPacketTemplate, BoardPacket, PacketSection
        )

        # 1. Create template
        template = BoardPacketTemplate.objects.create(
            tenant=tenant,
            name="Monthly Board Packet",
            sections=['cover', 'agenda', 'minutes', 'trial_balance', 'ar_aging'],
            is_default=True
        )

        # 2. Create packet
        packet = BoardPacket.objects.create(
            tenant=tenant,
            template=template,
            meeting_date=date.today() + timedelta(days=7),
            status='draft',
            generated_by="Secretary"
        )

        # 3. Add sections
        for i, section_type in enumerate(template.sections):
            PacketSection.objects.create(
                tenant=tenant,
                packet=packet,
                section_type=section_type,
                title=f"{section_type.replace('_', ' ').title()}",
                order=i
            )

        # 4. Generate PDF (placeholder)
        packet.status = 'generating'
        packet.save()

        packet.status = 'ready'
        packet.pdf_url = "https://s3.example.com/packets/packet_123.pdf"
        packet.page_count = 35
        packet.save()

        # 5. Send to board
        packet.status = 'sent'
        packet.sent_to = ["president@hoa.com", "treasurer@hoa.com", "secretary@hoa.com"]
        packet.sent_at = date.today()
        packet.save()

        # Verify
        assert packet.status == 'sent'
        assert len(packet.sent_to) == 3
        assert PacketSection.objects.filter(packet=packet).count() == 5
