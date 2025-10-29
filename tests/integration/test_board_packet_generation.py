"""
Integration tests for board packet generation functionality.

Tests the complete board packet lifecycle including:
- Template creation and configuration (13 section types)
- Board packet generation and status tracking (4 statuses)
- Section management and ordering
- PDF generation and storage
- Email distribution to board members
- Generation performance metrics
- Data type validation (datetime for timestamps, date for meeting dates)
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from qa_testing.generators import (
    BoardPacketGenerator,
    BoardPacketTemplateGenerator,
    PacketSectionGenerator,
    PropertyGenerator,
)
from qa_testing.models import (
    BoardPacket,
    BoardPacketStatus,
    BoardPacketTemplate,
    PacketSection,
    SectionType,
)


class TestBoardPacketTemplateCreation:
    """Tests for creating board packet templates."""

    def test_create_basic_template(self):
        """Test creating a basic board packet template."""
        property_obj = PropertyGenerator.create()

        template = BoardPacketTemplateGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        assert template.tenant_id == property_obj.tenant_id
        assert template.name != ""
        assert template.include_cover_page is True
        assert template.is_default is False
        assert len(template.sections) > 0

    def test_create_default_template(self):
        """Test creating a default template."""
        property_obj = PropertyGenerator.create()

        template = BoardPacketTemplateGenerator.create_default_template(
            tenant_id=property_obj.tenant_id,
        )

        assert template.name == "Monthly Board Meeting"
        assert template.is_default is True

    def test_create_template_with_specific_sections(self):
        """Test creating a template with specific sections."""
        property_obj = PropertyGenerator.create()

        sections = [
            SectionType.AGENDA,
            SectionType.FINANCIAL_SUMMARY,
            SectionType.TRIAL_BALANCE,
        ]

        template = BoardPacketTemplateGenerator.create_with_sections(
            tenant_id=property_obj.tenant_id,
            sections=sections,
        )

        assert len(template.sections) == 3
        assert SectionType.AGENDA.value in template.sections
        assert SectionType.FINANCIAL_SUMMARY.value in template.sections
        assert SectionType.TRIAL_BALANCE.value in template.sections

    def test_create_minimal_template(self):
        """Test creating a minimal template."""
        property_obj = PropertyGenerator.create()

        template = BoardPacketTemplateGenerator.create_minimal_template(
            tenant_id=property_obj.tenant_id,
        )

        assert len(template.sections) == 3
        assert template.name == "Minimal Board Meeting"

    def test_create_comprehensive_template(self):
        """Test creating a comprehensive template with all sections."""
        property_obj = PropertyGenerator.create()

        template = BoardPacketTemplateGenerator.create_comprehensive_template(
            tenant_id=property_obj.tenant_id,
        )

        assert len(template.sections) >= 10
        assert template.name == "Comprehensive Board Meeting"

    def test_template_section_count_property(self):
        """Test that template section_count property works."""
        property_obj = PropertyGenerator.create()

        template = BoardPacketTemplateGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        assert template.section_count == len(template.sections)


class TestBoardPacketCreation:
    """Tests for creating board packets."""

    def test_create_basic_board_packet(self):
        """Test creating a basic board packet."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.tenant_id == property_obj.tenant_id
        assert packet.title != ""
        assert packet.status == BoardPacketStatus.GENERATING
        assert isinstance(packet.meeting_date, date)
        assert isinstance(packet.generated_date, datetime)
        assert packet.generated_by != ""

    def test_create_generating_packet(self):
        """Test creating a packet in generating status."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_generating(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.GENERATING
        assert packet.pdf_url == ""
        assert packet.pdf_size_bytes is None
        assert packet.page_count is None

    def test_create_ready_packet(self):
        """Test creating a packet in ready status."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.READY
        assert packet.pdf_url != ""
        assert packet.pdf_size_bytes is not None
        assert packet.pdf_size_bytes > 0
        assert packet.page_count is not None
        assert packet.page_count > 0
        assert packet.generation_time_seconds is not None

    def test_create_sent_packet(self):
        """Test creating a packet in sent status."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.SENT
        assert len(packet.sent_to) > 0
        assert packet.sent_date is not None
        assert isinstance(packet.sent_date, datetime)

    def test_create_failed_packet(self):
        """Test creating a packet in failed status."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_failed(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.FAILED
        assert "failed" in packet.notes.lower()

    def test_create_packet_with_template(self):
        """Test creating a packet with a template."""
        property_obj = PropertyGenerator.create()

        template = BoardPacketTemplateGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
            template_id=template.id,
        )

        assert packet.template_id == template.id

    def test_create_packet_with_specific_meeting_date(self):
        """Test creating a packet with specific meeting date."""
        property_obj = PropertyGenerator.create()
        meeting_date = date(2025, 11, 15)

        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
            meeting_date=meeting_date,
        )

        assert packet.meeting_date == meeting_date
        assert "November 2025" in packet.title

    def test_create_packet_for_month(self):
        """Test creating a packet for a specific month."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_for_month(
            tenant_id=property_obj.tenant_id,
            year=2025,
            month=12,
        )

        assert packet.meeting_date.year == 2025
        assert packet.meeting_date.month == 12
        assert "December 2025" in packet.title


class TestBoardPacketStatus:
    """Tests for board packet status transitions."""

    def test_packet_status_generating(self):
        """Test packet in generating status."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_generating(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.GENERATING
        assert packet.is_generated is False
        assert packet.is_sent is False
        assert packet.has_pdf is False

    def test_packet_status_ready(self):
        """Test packet in ready status."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.READY
        assert packet.is_generated is True
        assert packet.is_sent is False
        assert packet.has_pdf is True

    def test_packet_status_sent(self):
        """Test packet in sent status."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.SENT
        assert packet.is_generated is True
        assert packet.is_sent is True
        assert packet.has_pdf is True

    def test_packet_status_failed(self):
        """Test packet in failed status."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_failed(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.FAILED
        assert packet.is_generated is False


class TestBoardPacketPDFGeneration:
    """Tests for board packet PDF generation."""

    def test_packet_with_pdf_url(self):
        """Test packet with PDF URL."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.pdf_url != ""
        assert packet.has_pdf is True
        assert "http" in packet.pdf_url

    def test_packet_with_pdf_size(self):
        """Test packet with PDF size."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.pdf_size_bytes is not None
        assert packet.pdf_size_bytes > 0
        # Typical PDF is 1-20 MB
        assert packet.pdf_size_bytes >= 1_000_000
        assert packet.pdf_size_bytes <= 20_000_000

    def test_packet_with_page_count(self):
        """Test packet with page count."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.page_count is not None
        assert packet.page_count > 0
        # Typical board packet is 10-100 pages
        assert packet.page_count >= 10
        assert packet.page_count <= 100

    def test_packet_with_generation_time(self):
        """Test packet with generation time."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.generation_time_seconds is not None
        assert packet.generation_time_seconds > 0
        # Typical generation is 10-300 seconds
        assert packet.generation_time_seconds >= 10
        assert packet.generation_time_seconds <= 300


class TestBoardPacketDistribution:
    """Tests for board packet email distribution."""

    def test_packet_with_recipients(self):
        """Test packet with email recipients."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        assert len(packet.sent_to) > 0
        assert packet.recipient_count > 0
        assert packet.recipient_count == len(packet.sent_to)

    def test_packet_with_multiple_recipients(self):
        """Test packet sent to multiple board members."""
        property_obj = PropertyGenerator.create()

        recipients = [
            "president@hoa.com",
            "treasurer@hoa.com",
            "secretary@hoa.com",
            "member1@hoa.com",
            "member2@hoa.com",
        ]

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
            sent_to=recipients,
        )

        assert len(packet.sent_to) == 5
        assert packet.recipient_count == 5
        assert "president@hoa.com" in packet.sent_to

    def test_packet_with_sent_date(self):
        """Test packet with sent date."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.sent_date is not None
        assert isinstance(packet.sent_date, datetime)
        assert packet.sent_date >= packet.generated_date

    def test_packet_recipient_count_property(self):
        """Test that packet recipient_count property works."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.recipient_count == len(packet.sent_to)


class TestPacketSectionCreation:
    """Tests for creating packet sections."""

    def test_create_basic_section(self):
        """Test creating a basic packet section."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
        )

        assert section.tenant_id == property_obj.tenant_id
        assert section.packet_id == packet.id
        assert section.title != ""
        assert section.order >= 0

    def test_create_section_with_specific_type(self):
        """Test creating a section with specific type."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.FINANCIAL_SUMMARY,
        )

        assert section.section_type == SectionType.FINANCIAL_SUMMARY

    def test_create_section_with_pages(self):
        """Test creating a section with page numbers."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create_with_pages(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.TRIAL_BALANCE,
            page_start=10,
            page_end=15,
        )

        assert section.page_start == 10
        assert section.page_end == 15
        assert section.page_count == 6

    def test_create_cover_page_section(self):
        """Test creating a cover page section."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create_cover_page(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
        )

        assert section.section_type == SectionType.COVER_PAGE
        assert section.order == 0
        assert section.page_start == 1
        assert section.page_end == 1

    def test_create_agenda_section(self):
        """Test creating an agenda section."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create_agenda(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
        )

        assert section.section_type == SectionType.AGENDA
        assert section.order == 1

    def test_create_financial_summary_section(self):
        """Test creating a financial summary section."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create_financial_summary(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
        )

        assert section.section_type == SectionType.FINANCIAL_SUMMARY


class TestPacketSectionTypes:
    """Tests for different packet section types."""

    def test_all_section_types(self):
        """Test creating sections for all types."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        for section_type in SectionType:
            section = PacketSectionGenerator.create(
                tenant_id=property_obj.tenant_id,
                packet_id=packet.id,
                section_type=section_type,
            )

            assert section.section_type == section_type

    def test_section_type_agenda(self):
        """Test agenda section type."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.AGENDA,
        )

        assert section.section_type == SectionType.AGENDA

    def test_section_type_financial_summary(self):
        """Test financial summary section type."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.FINANCIAL_SUMMARY,
        )

        assert section.section_type == SectionType.FINANCIAL_SUMMARY

    def test_section_type_trial_balance(self):
        """Test trial balance section type."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.TRIAL_BALANCE,
        )

        assert section.section_type == SectionType.TRIAL_BALANCE

    def test_section_type_ar_aging(self):
        """Test AR aging section type."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.AR_AGING,
        )

        assert section.section_type == SectionType.AR_AGING

    def test_section_type_violation_summary(self):
        """Test violation summary section type."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.VIOLATION_SUMMARY,
        )

        assert section.section_type == SectionType.VIOLATION_SUMMARY


class TestPacketSectionOrdering:
    """Tests for packet section ordering."""

    def test_section_order_property(self):
        """Test section order property."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            order=5,
        )

        assert section.order == 5

    def test_multiple_sections_ordered(self):
        """Test creating multiple sections with ordering."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section1 = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.COVER_PAGE,
            order=0,
        )

        section2 = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.AGENDA,
            order=1,
        )

        section3 = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.FINANCIAL_SUMMARY,
            order=2,
        )

        assert section1.order < section2.order < section3.order


class TestPacketSectionContent:
    """Tests for packet section content."""

    def test_section_with_content_url(self):
        """Test section with content URL."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
        )

        # Generator should provide content_url or content_data
        assert section.has_content

    def test_section_with_embedded_data(self):
        """Test section with embedded content data."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        content_data = {
            "report_type": "financial_summary",
            "data": {"revenue": 50000, "expenses": 30000},
        }

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            content_url="",
            content_data=content_data,
        )

        assert section.content_data is not None
        assert section.has_content
        assert section.content_data["report_type"] == "financial_summary"


class TestPacketSectionPages:
    """Tests for packet section page numbering."""

    def test_section_page_count(self):
        """Test section page count calculation."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create_with_pages(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.TRIAL_BALANCE,
            page_start=10,
            page_end=15,
        )

        assert section.page_count == 6

    def test_section_single_page(self):
        """Test section with single page."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create_with_pages(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.COVER_PAGE,
            page_start=1,
            page_end=1,
        )

        assert section.page_count == 1

    def test_section_multiple_pages(self):
        """Test section with multiple pages."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create_with_pages(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.RESERVE_SUMMARY,
            page_start=20,
            page_end=39,
        )

        assert section.page_count == 20


class TestBoardPacketDataTypes:
    """Tests for board packet data type validation."""

    def test_meeting_date_is_date_type(self):
        """Test that meeting_date is date type (not datetime)."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        assert isinstance(packet.meeting_date, date)
        assert not isinstance(packet.meeting_date, datetime)

    def test_generated_date_is_datetime_type(self):
        """Test that generated_date is datetime type (not date)."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        assert isinstance(packet.generated_date, datetime)

    def test_sent_date_is_datetime_type(self):
        """Test that sent_date is datetime type (not date)."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.sent_date is not None
        assert isinstance(packet.sent_date, datetime)

    def test_pdf_size_is_integer(self):
        """Test that pdf_size_bytes is integer type."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.pdf_size_bytes is not None
        assert isinstance(packet.pdf_size_bytes, int)

    def test_page_count_is_integer(self):
        """Test that page_count is integer type."""
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.page_count is not None
        assert isinstance(packet.page_count, int)


class TestBoardPacketEndToEnd:
    """End-to-end tests for complete board packet workflow."""

    def test_create_complete_board_packet(self):
        """Test creating a complete board packet with template and sections."""
        property_obj = PropertyGenerator.create()

        # Create template
        template = BoardPacketTemplateGenerator.create_default_template(
            tenant_id=property_obj.tenant_id,
        )

        # Create packet
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
            template_id=template.id,
            status=BoardPacketStatus.READY,
        )

        # Create sections
        cover_page = PacketSectionGenerator.create_cover_page(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
        )

        agenda = PacketSectionGenerator.create_agenda(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
        )

        financials = PacketSectionGenerator.create_financial_summary(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
        )

        # Verify
        assert packet.template_id == template.id
        assert packet.is_generated
        assert cover_page.packet_id == packet.id
        assert agenda.packet_id == packet.id
        assert financials.packet_id == packet.id

    def test_generate_and_send_board_packet(self):
        """Test complete workflow: generate packet and send to board."""
        property_obj = PropertyGenerator.create()

        # Create template
        template = BoardPacketTemplateGenerator.create_comprehensive_template(
            tenant_id=property_obj.tenant_id,
        )

        # Generate packet
        meeting_date = date(2025, 12, 15)
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
            template_id=template.id,
            meeting_date=meeting_date,
            status=BoardPacketStatus.READY,
        )

        # Send packet
        sent_packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
            meeting_date=meeting_date,
        )

        # Verify
        assert packet.status == BoardPacketStatus.READY
        assert sent_packet.status == BoardPacketStatus.SENT
        assert len(sent_packet.sent_to) > 0
        assert sent_packet.sent_date is not None
