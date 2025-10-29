"""Board packet data generator for realistic test data."""

from datetime import date, datetime, timedelta
from typing import Any, Optional
from uuid import UUID, uuid4

from faker import Faker

# Sentinel value to distinguish between "not provided" and "explicitly None"
_UNSET = object()

from qa_testing.models import (
    BoardPacket,
    BoardPacketStatus,
    BoardPacketTemplate,
    PacketSection,
    SectionType,
)

fake = Faker()


# Common board meeting types
MEETING_TYPES = [
    "Monthly Board Meeting",
    "Annual Board Meeting",
    "Special Board Meeting",
    "Budget Review Meeting",
    "Emergency Board Meeting",
    "Quarterly Board Meeting",
]


# Common section titles by type
SECTION_TITLES = {
    SectionType.COVER_PAGE: ["Board Meeting Packet Cover"],
    SectionType.AGENDA: ["Meeting Agenda", "Board Meeting Agenda"],
    SectionType.MINUTES: ["Previous Meeting Minutes", "Minutes from Last Meeting"],
    SectionType.FINANCIAL_SUMMARY: [
        "Financial Summary",
        "Financial Overview",
        "Financial Report",
    ],
    SectionType.TRIAL_BALANCE: ["Trial Balance", "Trial Balance Report"],
    SectionType.CASH_FLOW: [
        "Cash Flow Statement",
        "Statement of Cash Flows",
    ],
    SectionType.AR_AGING: [
        "Accounts Receivable Aging Report",
        "AR Aging Summary",
    ],
    SectionType.DELINQUENCY_REPORT: [
        "Delinquency Report",
        "Collections Status Report",
    ],
    SectionType.VIOLATION_SUMMARY: [
        "Violation Summary",
        "Open Violations Report",
    ],
    SectionType.RESERVE_SUMMARY: [
        "Reserve Study Summary",
        "Reserve Fund Analysis",
    ],
    SectionType.BUDGET_VARIANCE: [
        "Budget Variance Report",
        "Budget vs Actual Analysis",
    ],
    SectionType.CUSTOM_REPORT: ["Custom Report", "Special Analysis"],
    SectionType.ATTACHMENT: ["Attachment", "Supporting Document"],
}


class BoardPacketTemplateGenerator:
    """
    Generator for creating realistic BoardPacketTemplate test data.

    Usage:
        # Create a default template
        template = BoardPacketTemplateGenerator.create(
            tenant_id=tenant.id,
            name="Monthly Board Meeting"
        )

        # Create with specific sections
        template = BoardPacketTemplateGenerator.create_with_sections(
            tenant_id=tenant.id,
            sections=[SectionType.AGENDA, SectionType.FINANCIAL_SUMMARY]
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        sections: Optional[list[str]] = None,
        section_order: Optional[list[str]] = None,
        include_cover_page: bool = True,
        is_default: bool = False,
    ) -> BoardPacketTemplate:
        """
        Create a board packet template with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            name: Template name (generates if not provided)
            description: Template description (generates if not provided)
            sections: List of section types to include (generates if not provided)
            section_order: Order of sections (uses sections order if not provided)
            include_cover_page: Include auto-generated cover page
            is_default: Default template for this tenant

        Returns:
            BoardPacketTemplate instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Generate template name
        if name is None:
            name = fake.random.choice(MEETING_TYPES)

        # Generate description
        if description is None:
            description = f"Standard template for {name.lower()} with all required sections."

        # Generate sections (typical board packet sections)
        if sections is None:
            # Most templates include these core sections
            sections = [
                SectionType.AGENDA.value,
                SectionType.MINUTES.value,
                SectionType.FINANCIAL_SUMMARY.value,
                SectionType.TRIAL_BALANCE.value,
                SectionType.AR_AGING.value,
            ]

            # Randomly add optional sections (60% chance each)
            optional_sections = [
                SectionType.CASH_FLOW.value,
                SectionType.DELINQUENCY_REPORT.value,
                SectionType.VIOLATION_SUMMARY.value,
                SectionType.RESERVE_SUMMARY.value,
                SectionType.BUDGET_VARIANCE.value,
            ]

            for section in optional_sections:
                if fake.random.random() < 0.6:
                    sections.append(section)

        # Generate section order (default to sections order)
        if section_order is None:
            section_order = list(sections)

        return BoardPacketTemplate(
            tenant_id=tenant_id,
            name=name,
            description=description,
            sections=sections,
            section_order=section_order,
            include_cover_page=include_cover_page,
            is_default=is_default,
        )

    @staticmethod
    def create_default_template(
        *,
        tenant_id: Optional[UUID] = None,
    ) -> BoardPacketTemplate:
        """Create a default template."""
        return BoardPacketTemplateGenerator.create(
            tenant_id=tenant_id,
            name="Monthly Board Meeting",
            is_default=True,
        )

    @staticmethod
    def create_with_sections(
        *,
        tenant_id: Optional[UUID] = None,
        sections: list[SectionType],
        name: Optional[str] = None,
    ) -> BoardPacketTemplate:
        """Create a template with specific sections."""
        section_values = [s.value for s in sections]

        return BoardPacketTemplateGenerator.create(
            tenant_id=tenant_id,
            name=name,
            sections=section_values,
            section_order=section_values,
        )

    @staticmethod
    def create_minimal_template(
        *,
        tenant_id: Optional[UUID] = None,
    ) -> BoardPacketTemplate:
        """Create a minimal template with only essential sections."""
        sections = [
            SectionType.AGENDA.value,
            SectionType.MINUTES.value,
            SectionType.FINANCIAL_SUMMARY.value,
        ]

        return BoardPacketTemplateGenerator.create(
            tenant_id=tenant_id,
            name="Minimal Board Meeting",
            sections=sections,
            section_order=sections,
        )

    @staticmethod
    def create_comprehensive_template(
        *,
        tenant_id: Optional[UUID] = None,
    ) -> BoardPacketTemplate:
        """Create a comprehensive template with all section types."""
        sections = [s.value for s in SectionType if s != SectionType.COVER_PAGE]

        return BoardPacketTemplateGenerator.create(
            tenant_id=tenant_id,
            name="Comprehensive Board Meeting",
            sections=sections,
            section_order=sections,
        )


class BoardPacketGenerator:
    """
    Generator for creating realistic BoardPacket test data.

    Usage:
        # Create a new board packet
        packet = BoardPacketGenerator.create(
            tenant_id=tenant.id,
            title="November 2025 Board Meeting"
        )

        # Create with specific status
        packet = BoardPacketGenerator.create_ready(
            tenant_id=tenant.id,
            meeting_date=date(2025, 11, 15)
        )

        # Create and mark as sent
        packet = BoardPacketGenerator.create_sent(
            tenant_id=tenant.id,
            sent_to=["board@hoa.com"]
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        title: Optional[str] = None,
        meeting_date: Optional[date] = None,
        generated_date: Optional[datetime] = None,
        generated_by: Optional[str] = None,
        status: Optional[BoardPacketStatus] = None,
        template_id: Optional[UUID] = None,
        pdf_url: Optional[str] = None,
        pdf_size_bytes: Optional[int] = None,
        page_count: Optional[int] = None,
        generation_time_seconds: Optional[int] = None,
        sent_to: Optional[list[str]] = None,
        sent_date: Optional[datetime] = None,
        notes: str = "",
    ) -> BoardPacket:
        """
        Create a board packet with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            title: Packet title (generates if not provided)
            meeting_date: Date of board meeting (generates if not provided)
            generated_date: When packet was generated (generates if not provided)
            generated_by: User who generated the packet (generates if not provided)
            status: Current status (GENERATING if not provided)
            template_id: Template used (optional)
            pdf_url: URL to generated PDF (generates if status is READY or SENT)
            pdf_size_bytes: PDF file size (generates if status is READY or SENT)
            page_count: Number of pages (generates if status is READY or SENT)
            generation_time_seconds: Time taken to generate (generates if status is READY or SENT)
            sent_to: List of email addresses (generates if status is SENT)
            sent_date: When packet was sent (generates if status is SENT)
            notes: Notes about this packet

        Returns:
            BoardPacket instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Generate meeting date (typically 7-60 days in the future)
        if meeting_date is None:
            days_ahead = fake.random.randint(7, 60)
            meeting_date = date.today() + timedelta(days=days_ahead)

        # Generate title based on meeting date
        if title is None:
            month_year = meeting_date.strftime("%B %Y")
            title = f"{month_year} Board Meeting"

        # Generate generated date (typically 3-7 days before meeting)
        if generated_date is None:
            days_before = fake.random.randint(3, 7)
            generated_date = datetime.now() - timedelta(days=days_before)

        # Generate generated_by
        if generated_by is None:
            generated_by_options = [
                "Property Manager",
                "HOA Administrator",
                f"{fake.first_name()} {fake.last_name()}",
                "Board Secretary",
                "Management Company",
            ]
            generated_by = fake.random.choice(generated_by_options)

        # Default status
        if status is None:
            status = BoardPacketStatus.GENERATING

        # Generate PDF URL if status is READY or SENT
        if pdf_url is None and status in [BoardPacketStatus.READY, BoardPacketStatus.SENT]:
            storage_providers = [
                f"https://s3.amazonaws.com/hoa-board-packets/{uuid4()}.pdf",
                f"https://cdn.cloudflare.com/board-packets/{uuid4()}.pdf",
                f"https://storage.googleapis.com/hoa-packets/{uuid4()}.pdf",
            ]
            pdf_url = fake.random.choice(storage_providers)

        # Generate PDF size (typically 1-20 MB)
        if pdf_size_bytes is None and status in [BoardPacketStatus.READY, BoardPacketStatus.SENT]:
            pdf_size_bytes = fake.random.randint(1_000_000, 20_000_000)

        # Generate page count (typically 10-100 pages)
        if page_count is None and status in [BoardPacketStatus.READY, BoardPacketStatus.SENT]:
            page_count = fake.random.randint(10, 100)

        # Generate generation time (typically 10-300 seconds)
        if generation_time_seconds is None and status in [BoardPacketStatus.READY, BoardPacketStatus.SENT]:
            generation_time_seconds = fake.random.randint(10, 300)

        # Generate sent_to if status is SENT
        if sent_to is None and status == BoardPacketStatus.SENT:
            # Typical board has 3-7 members
            board_size = fake.random.randint(3, 7)
            sent_to = [fake.email() for _ in range(board_size)]
        elif sent_to is None:
            sent_to = []

        # Generate sent_date if status is SENT
        if sent_date is None and status == BoardPacketStatus.SENT:
            # Typically sent within hours of generation
            hours_after = fake.random.randint(1, 24)
            sent_date = generated_date + timedelta(hours=hours_after)

        return BoardPacket(
            tenant_id=tenant_id,
            title=title,
            meeting_date=meeting_date,
            generated_date=generated_date,
            generated_by=generated_by,
            status=status,
            template_id=template_id,
            pdf_url=pdf_url or "",
            pdf_size_bytes=pdf_size_bytes,
            page_count=page_count,
            generation_time_seconds=generation_time_seconds,
            sent_to=sent_to,
            sent_date=sent_date,
            notes=notes,
        )

    @staticmethod
    def create_generating(
        *,
        tenant_id: Optional[UUID] = None,
        meeting_date: Optional[date] = None,
    ) -> BoardPacket:
        """Create a board packet that is currently generating."""
        return BoardPacketGenerator.create(
            tenant_id=tenant_id,
            meeting_date=meeting_date,
            status=BoardPacketStatus.GENERATING,
        )

    @staticmethod
    def create_ready(
        *,
        tenant_id: Optional[UUID] = None,
        meeting_date: Optional[date] = None,
        page_count: Optional[int] = None,
    ) -> BoardPacket:
        """Create a board packet that is ready."""
        return BoardPacketGenerator.create(
            tenant_id=tenant_id,
            meeting_date=meeting_date,
            status=BoardPacketStatus.READY,
            page_count=page_count,
        )

    @staticmethod
    def create_sent(
        *,
        tenant_id: Optional[UUID] = None,
        meeting_date: Optional[date] = None,
        sent_to: Optional[list[str]] = None,
    ) -> BoardPacket:
        """Create a board packet that has been sent."""
        return BoardPacketGenerator.create(
            tenant_id=tenant_id,
            meeting_date=meeting_date,
            status=BoardPacketStatus.SENT,
            sent_to=sent_to,
        )

    @staticmethod
    def create_failed(
        *,
        tenant_id: Optional[UUID] = None,
        meeting_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> BoardPacket:
        """Create a board packet that failed to generate."""
        if notes is None:
            error_messages = [
                "PDF generation timeout",
                "Failed to fetch financial data",
                "Insufficient memory",
                "Template rendering error",
                "Data validation error",
            ]
            notes = f"Generation failed: {fake.random.choice(error_messages)}"

        return BoardPacketGenerator.create(
            tenant_id=tenant_id,
            meeting_date=meeting_date,
            status=BoardPacketStatus.FAILED,
            notes=notes,
        )

    @staticmethod
    def create_for_month(
        *,
        tenant_id: Optional[UUID] = None,
        year: int,
        month: int,
    ) -> BoardPacket:
        """Create a board packet for a specific month."""
        # Set meeting date to second Tuesday of the month (common board meeting day)
        meeting_date = date(year, month, 1)
        days_to_tuesday = (1 - meeting_date.weekday() + 7) % 7  # Get to Tuesday
        meeting_date += timedelta(days=days_to_tuesday + 7)  # Second Tuesday

        month_name = meeting_date.strftime("%B %Y")
        title = f"{month_name} Board Meeting"

        return BoardPacketGenerator.create(
            tenant_id=tenant_id,
            title=title,
            meeting_date=meeting_date,
        )


class PacketSectionGenerator:
    """
    Generator for creating realistic PacketSection test data.

    Usage:
        # Create a section
        section = PacketSectionGenerator.create(
            tenant_id=tenant.id,
            packet_id=packet.id,
            section_type=SectionType.FINANCIAL_SUMMARY
        )

        # Create with page numbers
        section = PacketSectionGenerator.create_with_pages(
            tenant_id=tenant.id,
            packet_id=packet.id,
            section_type=SectionType.TRIAL_BALANCE,
            page_start=10,
            page_end=15
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        packet_id: UUID,
        section_type: Optional[SectionType] = None,
        title: Optional[str] = None,
        order: Optional[int] = None,
        content_url: Optional[str] = None,
        content_data: Optional[dict[str, Any]] = None,
        page_start: Optional[int] = None,
        page_end: Optional[int] = None,
    ) -> PacketSection:
        """
        Create a packet section with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            packet_id: Associated board packet (required)
            section_type: Type of section (random if not provided)
            title: Section title (generates if not provided)
            order: Display order (generates if not provided)
            content_url: URL to section content (generates if not provided)
            content_data: Embedded content data (optional)
            page_start: Starting page number (optional)
            page_end: Ending page number (optional)

        Returns:
            PacketSection instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Select random section type if not provided
        if section_type is None:
            section_type = fake.random.choice(list(SectionType))

        # Generate title based on section type
        if title is None:
            title = fake.random.choice(SECTION_TITLES[section_type])

        # Generate order (0-12 for typical board packets)
        if order is None:
            order = fake.random.randint(0, 12)

        # Generate content URL
        if content_url is None and content_data is None:
            storage_providers = [
                f"https://s3.amazonaws.com/hoa-sections/{uuid4()}.pdf",
                f"https://cdn.cloudflare.com/sections/{uuid4()}.pdf",
                f"https://storage.googleapis.com/hoa-reports/{uuid4()}.pdf",
            ]
            content_url = fake.random.choice(storage_providers)

        # Generate page numbers if not provided
        if page_start is not None and page_end is None:
            # Generate reasonable page count for section type
            page_counts = {
                SectionType.COVER_PAGE: 1,
                SectionType.AGENDA: (1, 2),
                SectionType.MINUTES: (2, 5),
                SectionType.FINANCIAL_SUMMARY: (3, 8),
                SectionType.TRIAL_BALANCE: (5, 15),
                SectionType.CASH_FLOW: (2, 5),
                SectionType.AR_AGING: (3, 10),
                SectionType.DELINQUENCY_REPORT: (2, 8),
                SectionType.VIOLATION_SUMMARY: (2, 6),
                SectionType.RESERVE_SUMMARY: (5, 20),
                SectionType.BUDGET_VARIANCE: (3, 10),
                SectionType.CUSTOM_REPORT: (3, 15),
                SectionType.ATTACHMENT: (1, 10),
            }

            count_range = page_counts.get(section_type, (1, 5))
            if isinstance(count_range, tuple):
                page_count = fake.random.randint(*count_range)
            else:
                page_count = count_range

            page_end = page_start + page_count - 1

        return PacketSection(
            tenant_id=tenant_id,
            packet_id=packet_id,
            section_type=section_type,
            title=title,
            order=order,
            content_url=content_url or "",
            content_data=content_data,
            page_start=page_start,
            page_end=page_end,
        )

    @staticmethod
    def create_with_pages(
        *,
        tenant_id: Optional[UUID] = None,
        packet_id: UUID,
        section_type: SectionType,
        page_start: int,
        page_end: int,
    ) -> PacketSection:
        """Create a section with specific page numbers."""
        return PacketSectionGenerator.create(
            tenant_id=tenant_id,
            packet_id=packet_id,
            section_type=section_type,
            page_start=page_start,
            page_end=page_end,
        )

    @staticmethod
    def create_cover_page(
        *,
        tenant_id: Optional[UUID] = None,
        packet_id: UUID,
    ) -> PacketSection:
        """Create a cover page section."""
        return PacketSectionGenerator.create(
            tenant_id=tenant_id,
            packet_id=packet_id,
            section_type=SectionType.COVER_PAGE,
            order=0,
            page_start=1,
            page_end=1,
        )

    @staticmethod
    def create_agenda(
        *,
        tenant_id: Optional[UUID] = None,
        packet_id: UUID,
        order: int = 1,
    ) -> PacketSection:
        """Create an agenda section."""
        return PacketSectionGenerator.create(
            tenant_id=tenant_id,
            packet_id=packet_id,
            section_type=SectionType.AGENDA,
            order=order,
        )

    @staticmethod
    def create_financial_summary(
        *,
        tenant_id: Optional[UUID] = None,
        packet_id: UUID,
        order: Optional[int] = None,
    ) -> PacketSection:
        """Create a financial summary section."""
        return PacketSectionGenerator.create(
            tenant_id=tenant_id,
            packet_id=packet_id,
            section_type=SectionType.FINANCIAL_SUMMARY,
            order=order,
        )
