"""Board packet generation models for testing HOA board meeting materials."""

from datetime import date, datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import Field, field_validator

from .base import AccountingDate, BaseTestModel


class BoardPacketStatus(str, Enum):
    """Board packet generation status."""

    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"
    SENT = "SENT"


class SectionType(str, Enum):
    """Types of sections that can be included in board packets."""

    COVER_PAGE = "COVER_PAGE"
    AGENDA = "AGENDA"
    MINUTES = "MINUTES"
    FINANCIAL_SUMMARY = "FINANCIAL_SUMMARY"
    TRIAL_BALANCE = "TRIAL_BALANCE"
    CASH_FLOW = "CASH_FLOW"
    AR_AGING = "AR_AGING"
    DELINQUENCY_REPORT = "DELINQUENCY_REPORT"
    VIOLATION_SUMMARY = "VIOLATION_SUMMARY"
    RESERVE_SUMMARY = "RESERVE_SUMMARY"
    BUDGET_VARIANCE = "BUDGET_VARIANCE"
    CUSTOM_REPORT = "CUSTOM_REPORT"
    ATTACHMENT = "ATTACHMENT"


class BoardPacketTemplate(BaseTestModel):
    """
    Reusable template for board packet generation.

    Defines which sections to include and their order for consistent
    board packet creation across meetings.
    """

    name: str = Field(
        description="Template name (e.g., 'Monthly Board Meeting', 'Annual Meeting')"
    )

    description: str = Field(
        default="",
        description="Template description"
    )

    sections: list[str] = Field(
        default_factory=list,
        description="List of section types to include (e.g., ['AGENDA', 'FINANCIAL_SUMMARY'])"
    )

    section_order: list[str] = Field(
        default_factory=list,
        description="Order of sections in packet"
    )

    include_cover_page: bool = Field(
        default=True,
        description="Include auto-generated cover page"
    )

    is_default: bool = Field(
        default=False,
        description="Default template for this tenant"
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v):
        """Ensure name is not empty."""
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v

    @field_validator("sections")
    @classmethod
    def validate_sections_valid(cls, v):
        """Ensure all section types are valid."""
        valid_types = {s.value for s in SectionType}
        for section in v:
            if section not in valid_types:
                raise ValueError(f"Invalid section type: {section}")
        return v

    @property
    def section_count(self) -> int:
        """Get the number of sections in this template."""
        return len(self.sections)


class BoardPacket(BaseTestModel):
    """
    Generated board packet with PDF and distribution tracking.

    Archives of generated packets for each board meeting including:
    - PDF generation and storage
    - Generation performance metrics
    - Email distribution tracking
    - Status workflow (4 stages)
    """

    title: str = Field(
        description="Packet title (e.g., 'November 2025 Board Meeting')"
    )

    meeting_date: AccountingDate = Field(
        description="Date of board meeting"
    )

    generated_date: datetime = Field(
        description="When packet was generated (timestamp with timezone)"
    )

    generated_by: str = Field(
        description="User who generated the packet"
    )

    status: BoardPacketStatus = Field(
        default=BoardPacketStatus.GENERATING,
        description="Current status of packet generation"
    )

    template_id: Optional[UUID] = Field(
        default=None,
        description="Template used to generate this packet"
    )

    pdf_url: str = Field(
        default="",
        description="URL to generated PDF (S3, CloudFlare, etc.)",
        max_length=500
    )

    pdf_size_bytes: Optional[int] = Field(
        default=None,
        description="PDF file size in bytes"
    )

    page_count: Optional[int] = Field(
        default=None,
        description="Number of pages in PDF"
    )

    generation_time_seconds: Optional[int] = Field(
        default=None,
        description="Time taken to generate PDF"
    )

    sent_to: list[str] = Field(
        default_factory=list,
        description="List of email addresses packet was sent to"
    )

    sent_date: Optional[datetime] = Field(
        default=None,
        description="When packet was emailed to board (timestamp with timezone)"
    )

    notes: str = Field(
        default="",
        description="Notes about this packet"
    )

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v):
        """Ensure title is not empty."""
        if not v or not v.strip():
            raise ValueError("title cannot be empty")
        return v

    @field_validator("generated_by")
    @classmethod
    def validate_generated_by_not_empty(cls, v):
        """Ensure generated_by is not empty."""
        if not v or not v.strip():
            raise ValueError("generated_by cannot be empty")
        return v

    @field_validator("pdf_size_bytes")
    @classmethod
    def validate_pdf_size_positive(cls, v):
        """Ensure pdf_size_bytes is positive."""
        if v is not None and v <= 0:
            raise ValueError("pdf_size_bytes must be positive")
        return v

    @field_validator("page_count")
    @classmethod
    def validate_page_count_positive(cls, v):
        """Ensure page_count is positive."""
        if v is not None and v <= 0:
            raise ValueError("page_count must be positive")
        return v

    @field_validator("generation_time_seconds")
    @classmethod
    def validate_generation_time_positive(cls, v):
        """Ensure generation_time_seconds is positive."""
        if v is not None and v <= 0:
            raise ValueError("generation_time_seconds must be positive")
        return v

    @field_validator("sent_to")
    @classmethod
    def validate_sent_to_emails(cls, v):
        """Ensure sent_to contains valid email format."""
        for email in v:
            if "@" not in email or "." not in email:
                raise ValueError(f"Invalid email format: {email}")
        return v

    @field_validator("sent_date")
    @classmethod
    def validate_sent_date_after_generated(cls, v, info):
        """Ensure sent_date is after generated_date."""
        if v is not None and "generated_date" in info.data:
            if v < info.data["generated_date"]:
                raise ValueError("sent_date must be after generated_date")
        return v

    @field_validator("generated_date")
    @classmethod
    def validate_generated_date_type(cls, v):
        """Ensure generated_date is datetime type (not date)."""
        if not isinstance(v, datetime):
            raise ValueError("generated_date must be datetime type, not date")
        return v

    @field_validator("sent_date")
    @classmethod
    def validate_sent_date_type(cls, v):
        """Ensure sent_date is datetime type (not date)."""
        if v is not None and not isinstance(v, datetime):
            raise ValueError("sent_date must be datetime type, not date")
        return v

    @property
    def is_generated(self) -> bool:
        """Check if packet generation is complete."""
        return self.status in [BoardPacketStatus.READY, BoardPacketStatus.SENT]

    @property
    def is_sent(self) -> bool:
        """Check if packet has been sent to board members."""
        return self.status == BoardPacketStatus.SENT

    @property
    def has_pdf(self) -> bool:
        """Check if packet has a PDF URL."""
        return bool(self.pdf_url and self.pdf_url.strip())

    @property
    def recipient_count(self) -> int:
        """Get the number of recipients."""
        return len(self.sent_to)


class PacketSection(BaseTestModel):
    """
    Individual section within a board packet.

    Tracks which reports/documents are included and page numbers.
    """

    packet_id: UUID = Field(
        description="Associated board packet"
    )

    section_type: SectionType = Field(
        description="Type of section"
    )

    title: str = Field(
        description="Section title/heading"
    )

    order: int = Field(
        default=0,
        description="Display order (lower numbers first)"
    )

    content_url: str = Field(
        default="",
        description="URL to section content (PDF, image, etc.)",
        max_length=500
    )

    content_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Embedded content data (for reports generated inline)"
    )

    page_start: Optional[int] = Field(
        default=None,
        description="Starting page number in final PDF"
    )

    page_end: Optional[int] = Field(
        default=None,
        description="Ending page number in final PDF"
    )

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v):
        """Ensure title is not empty."""
        if not v or not v.strip():
            raise ValueError("title cannot be empty")
        return v

    @field_validator("order")
    @classmethod
    def validate_order_non_negative(cls, v):
        """Ensure order is non-negative."""
        if v < 0:
            raise ValueError("order must be non-negative")
        return v

    @field_validator("page_start")
    @classmethod
    def validate_page_start_positive(cls, v):
        """Ensure page_start is positive."""
        if v is not None and v <= 0:
            raise ValueError("page_start must be positive")
        return v

    @field_validator("page_end")
    @classmethod
    def validate_page_end_positive(cls, v):
        """Ensure page_end is positive."""
        if v is not None and v <= 0:
            raise ValueError("page_end must be positive")
        return v

    @field_validator("page_end")
    @classmethod
    def validate_page_end_after_start(cls, v, info):
        """Ensure page_end is >= page_start."""
        if v is not None and "page_start" in info.data:
            page_start = info.data["page_start"]
            if page_start is not None and v < page_start:
                raise ValueError("page_end must be >= page_start")
        return v

    @property
    def page_count(self) -> Optional[int]:
        """Get the number of pages in this section."""
        if self.page_start is not None and self.page_end is not None:
            return self.page_end - self.page_start + 1
        return None

    @property
    def has_content(self) -> bool:
        """Check if section has content (URL or data)."""
        return bool(
            (self.content_url and self.content_url.strip()) or
            self.content_data
        )
