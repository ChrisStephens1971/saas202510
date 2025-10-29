"""
Property-based tests for board packet generation invariants.

Uses Hypothesis to verify that board packet operations maintain critical invariants:
- PDF size always > 0 when status is READY or SENT
- Page count always > 0 when status is READY or SENT
- Generation time always > 0 when status is READY or SENT
- Sent date >= generated date
- Meeting date is date type (not datetime)
- Generated date is datetime type (not date)
- Sent date is datetime type (not date)
- Section page_end >= page_start
- Section order >= 0
- Email addresses are valid format
- Template sections are valid types
- Status progression order
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from hypothesis import assume, given
from hypothesis import strategies as st
import pytest

from qa_testing.generators import (
    BoardPacketGenerator,
    BoardPacketTemplateGenerator,
    PacketSectionGenerator,
    PropertyGenerator,
)
from qa_testing.models import (
    BoardPacketStatus,
    SectionType,
)


# Custom strategies for board packet tests
@st.composite
def pdf_size_strategy(draw):
    """Generate realistic PDF size (1-20 MB)."""
    return draw(st.integers(min_value=1_000_000, max_value=20_000_000))


@st.composite
def page_count_strategy(draw):
    """Generate realistic page count (10-100 pages)."""
    return draw(st.integers(min_value=10, max_value=100))


@st.composite
def generation_time_strategy(draw):
    """Generate realistic generation time (10-300 seconds)."""
    return draw(st.integers(min_value=10, max_value=300))


@st.composite
def days_ahead_strategy(draw):
    """Generate realistic meeting date (7-60 days ahead)."""
    return draw(st.integers(min_value=7, max_value=60))


@st.composite
def section_order_strategy(draw):
    """Generate valid section order (0-20)."""
    return draw(st.integers(min_value=0, max_value=20))


@st.composite
def page_start_strategy(draw):
    """Generate valid page start (1-100)."""
    return draw(st.integers(min_value=1, max_value=100))


@st.composite
def page_span_strategy(draw):
    """Generate valid page span (1-50 pages)."""
    return draw(st.integers(min_value=1, max_value=50))


@st.composite
def section_type_strategy(draw):
    """Generate random section type."""
    return draw(st.sampled_from(list(SectionType)))


@st.composite
def board_size_strategy(draw):
    """Generate realistic board size (3-7 members)."""
    return draw(st.integers(min_value=3, max_value=7))


class TestBoardPacketPDFInvariants:
    """Property-based tests for board packet PDF invariants."""

    @given(
        pdf_size=pdf_size_strategy(),
    )
    def test_pdf_size_always_positive(self, pdf_size):
        """
        INVARIANT: PDF size is always > 0 when packet is READY.

        Generated PDFs must have positive file size.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
            page_count=50,
        )

        assert packet.pdf_size_bytes is not None
        assert packet.pdf_size_bytes > 0

    @given(
        page_count=page_count_strategy(),
    )
    def test_page_count_always_positive(self, page_count):
        """
        INVARIANT: Page count is always > 0 when packet is READY.

        Generated PDFs must have at least one page.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
            page_count=page_count,
        )

        assert packet.page_count is not None
        assert packet.page_count > 0

    @given(
        generation_time=generation_time_strategy(),
    )
    def test_generation_time_always_positive(self, generation_time):
        """
        INVARIANT: Generation time is always > 0 when packet is READY.

        PDF generation must take some time.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.generation_time_seconds is not None
        assert packet.generation_time_seconds > 0

    def test_ready_packet_has_pdf_url(self):
        """
        INVARIANT: READY packets always have PDF URL.

        A packet cannot be READY without a PDF.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.READY
        assert packet.has_pdf
        assert packet.pdf_url != ""

    def test_sent_packet_has_pdf_url(self):
        """
        INVARIANT: SENT packets always have PDF URL.

        A packet cannot be SENT without a PDF.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.SENT
        assert packet.has_pdf
        assert packet.pdf_url != ""


class TestBoardPacketDateInvariants:
    """Property-based tests for board packet date invariants."""

    @given(
        days_ahead=days_ahead_strategy(),
    )
    def test_meeting_date_in_future(self, days_ahead):
        """
        INVARIANT: Meeting dates are typically in the future.

        Board packets are generated before the meeting.
        """
        property_obj = PropertyGenerator.create()
        meeting_date = date.today() + timedelta(days=days_ahead)

        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
            meeting_date=meeting_date,
        )

        assert packet.meeting_date >= date.today()

    def test_sent_date_after_generated_date(self):
        """
        INVARIANT: Sent date is always >= generated date.

        Packets cannot be sent before they are generated.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.sent_date is not None
        assert packet.sent_date >= packet.generated_date

    def test_meeting_date_is_date_type(self):
        """
        INVARIANT: Meeting date is date type (not datetime).

        Meeting dates don't need time precision.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        assert isinstance(packet.meeting_date, date)
        assert not isinstance(packet.meeting_date, datetime)

    def test_generated_date_is_datetime_type(self):
        """
        INVARIANT: Generated date is datetime type (not date).

        Generation timestamps need time precision.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        assert isinstance(packet.generated_date, datetime)

    def test_sent_date_is_datetime_type(self):
        """
        INVARIANT: Sent date is datetime type (not date).

        Sent timestamps need time precision.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.sent_date is not None
        assert isinstance(packet.sent_date, datetime)


class TestBoardPacketStatusInvariants:
    """Property-based tests for board packet status invariants."""

    def test_generating_packet_has_no_pdf(self):
        """
        INVARIANT: GENERATING packets don't have PDF yet.

        PDFs are not available until generation completes.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_generating(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.GENERATING
        assert packet.pdf_url == ""
        assert packet.pdf_size_bytes is None
        assert packet.page_count is None

    def test_ready_packet_not_sent(self):
        """
        INVARIANT: READY packets are not sent yet.

        READY status means generated but not distributed.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_ready(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.READY
        assert packet.is_generated
        assert not packet.is_sent
        assert len(packet.sent_to) == 0
        assert packet.sent_date is None

    def test_sent_packet_has_recipients(self):
        """
        INVARIANT: SENT packets always have recipients.

        Cannot be SENT without email addresses.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.SENT
        assert len(packet.sent_to) > 0
        assert packet.recipient_count > 0

    def test_sent_packet_has_sent_date(self):
        """
        INVARIANT: SENT packets always have sent_date.

        Sent timestamp is required for SENT status.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.SENT
        assert packet.sent_date is not None

    def test_failed_packet_has_notes(self):
        """
        INVARIANT: FAILED packets should have notes explaining failure.

        Failures should be documented.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_failed(
            tenant_id=property_obj.tenant_id,
        )

        assert packet.status == BoardPacketStatus.FAILED
        assert packet.notes != ""


class TestBoardPacketRecipientInvariants:
    """Property-based tests for board packet recipient invariants."""

    @given(
        board_size=board_size_strategy(),
    )
    def test_recipient_count_matches_list_length(self, board_size):
        """
        INVARIANT: recipient_count property matches sent_to list length.

        Count should always reflect actual list size.
        """
        property_obj = PropertyGenerator.create()

        # Create realistic email addresses
        recipients = [f"board{i}@hoa.com" for i in range(board_size)]

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
            sent_to=recipients,
        )

        assert packet.recipient_count == len(packet.sent_to)
        assert packet.recipient_count == board_size

    def test_email_addresses_are_valid_format(self):
        """
        INVARIANT: All email addresses in sent_to have valid format.

        Emails must contain @ and . characters.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        for email in packet.sent_to:
            assert "@" in email
            assert "." in email


class TestBoardPacketTemplateInvariants:
    """Property-based tests for board packet template invariants."""

    def test_template_sections_are_valid_types(self):
        """
        INVARIANT: All template sections are valid SectionType values.

        Invalid section types should not be accepted.
        """
        property_obj = PropertyGenerator.create()

        template = BoardPacketTemplateGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        valid_types = {s.value for s in SectionType}

        for section in template.sections:
            assert section in valid_types

    def test_template_section_count_property(self):
        """
        INVARIANT: section_count property matches sections list length.

        Count should always reflect actual list size.
        """
        property_obj = PropertyGenerator.create()

        template = BoardPacketTemplateGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        assert template.section_count == len(template.sections)

    def test_default_template_has_is_default_true(self):
        """
        INVARIANT: Default templates have is_default=True.

        Default flag must be set correctly.
        """
        property_obj = PropertyGenerator.create()

        template = BoardPacketTemplateGenerator.create_default_template(
            tenant_id=property_obj.tenant_id,
        )

        assert template.is_default is True

    def test_template_name_not_empty(self):
        """
        INVARIANT: Template name is never empty.

        Templates must have names.
        """
        property_obj = PropertyGenerator.create()

        template = BoardPacketTemplateGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        assert template.name != ""
        assert template.name.strip() != ""


class TestPacketSectionPageInvariants:
    """Property-based tests for packet section page invariants."""

    @given(
        page_start=page_start_strategy(),
        page_span=page_span_strategy(),
    )
    def test_page_end_always_greater_or_equal_to_page_start(self, page_start, page_span):
        """
        INVARIANT: page_end >= page_start for all sections.

        Sections cannot end before they start.
        """
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        page_end = page_start + page_span - 1

        section = PacketSectionGenerator.create_with_pages(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.TRIAL_BALANCE,
            page_start=page_start,
            page_end=page_end,
        )

        assert section.page_end >= section.page_start

    @given(
        page_start=page_start_strategy(),
        page_span=page_span_strategy(),
    )
    def test_page_count_calculation_is_correct(self, page_start, page_span):
        """
        INVARIANT: page_count = page_end - page_start + 1.

        Page count calculation must be accurate.
        """
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        page_end = page_start + page_span - 1

        section = PacketSectionGenerator.create_with_pages(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.FINANCIAL_SUMMARY,
            page_start=page_start,
            page_end=page_end,
        )

        expected_count = page_end - page_start + 1
        assert section.page_count == expected_count

    def test_page_start_always_positive(self):
        """
        INVARIANT: page_start is always >= 1.

        Page numbers start at 1, not 0.
        """
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create_with_pages(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=SectionType.AGENDA,
            page_start=1,
            page_end=3,
        )

        assert section.page_start is not None
        assert section.page_start >= 1

    def test_cover_page_is_always_one_page(self):
        """
        INVARIANT: Cover page sections are always exactly 1 page.

        Cover pages should not span multiple pages.
        """
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create_cover_page(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
        )

        assert section.section_type == SectionType.COVER_PAGE
        assert section.page_count == 1


class TestPacketSectionOrderInvariants:
    """Property-based tests for packet section order invariants."""

    @given(
        order=section_order_strategy(),
    )
    def test_section_order_always_non_negative(self, order):
        """
        INVARIANT: Section order is always >= 0.

        Negative ordering doesn't make sense.
        """
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            order=order,
        )

        assert section.order >= 0

    def test_cover_page_always_first(self):
        """
        INVARIANT: Cover page sections should have order=0.

        Cover pages should always be first.
        """
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create_cover_page(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
        )

        assert section.order == 0


class TestPacketSectionContentInvariants:
    """Property-based tests for packet section content invariants."""

    def test_section_has_content_url_or_data(self):
        """
        INVARIANT: Sections should have either content_url or content_data.

        Sections must have content source.
        """
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
        )

        assert section.has_content

    def test_section_title_not_empty(self):
        """
        INVARIANT: Section title is never empty.

        All sections must have titles.
        """
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
        )

        assert section.title != ""
        assert section.title.strip() != ""


class TestBoardPacketSectionTypeInvariants:
    """Property-based tests for all section types."""

    @given(
        section_type=section_type_strategy(),
    )
    def test_all_section_types_valid(self, section_type):
        """
        INVARIANT: All SectionType enum values can be used.

        Every section type should be supported.
        """
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
        )

        section = PacketSectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            packet_id=packet.id,
            section_type=section_type,
        )

        assert section.section_type == section_type
        assert section.section_type in list(SectionType)


class TestBoardPacketEndToEndInvariants:
    """Property-based tests for complete board packet workflows."""

    def test_complete_workflow_maintains_invariants(self):
        """
        INVARIANT: Complete workflow (template -> packet -> sections) maintains all invariants.

        End-to-end process should be consistent.
        """
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
        sections = []
        for i, section_type_value in enumerate(template.sections[:5]):  # First 5 sections
            section_type = SectionType(section_type_value)
            section = PacketSectionGenerator.create(
                tenant_id=property_obj.tenant_id,
                packet_id=packet.id,
                section_type=section_type,
                order=i,
            )
            sections.append(section)

        # Verify invariants
        assert template.is_default
        assert packet.template_id == template.id
        assert packet.is_generated
        assert packet.has_pdf

        for i, section in enumerate(sections):
            assert section.packet_id == packet.id
            assert section.order == i
            assert section.has_content

    def test_sent_packet_maintains_all_invariants(self):
        """
        INVARIANT: Sent packets maintain all generation and distribution invariants.

        Sent status implies all previous invariants still hold.
        """
        property_obj = PropertyGenerator.create()

        packet = BoardPacketGenerator.create_sent(
            tenant_id=property_obj.tenant_id,
        )

        # Status invariants
        assert packet.status == BoardPacketStatus.SENT
        assert packet.is_generated
        assert packet.is_sent

        # PDF invariants
        assert packet.has_pdf
        assert packet.pdf_url != ""
        assert packet.pdf_size_bytes is not None
        assert packet.pdf_size_bytes > 0
        assert packet.page_count is not None
        assert packet.page_count > 0

        # Distribution invariants
        assert len(packet.sent_to) > 0
        assert packet.sent_date is not None
        assert packet.sent_date >= packet.generated_date

        # Date type invariants
        assert isinstance(packet.meeting_date, date)
        assert not isinstance(packet.meeting_date, datetime)
        assert isinstance(packet.generated_date, datetime)
        assert isinstance(packet.sent_date, datetime)
