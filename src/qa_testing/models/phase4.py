"""
Phase 4 Models for Sprint 20-22 Features

Models for:
- Board Packet Generation (Sprint 20)
- Auditor Export (Sprint 21)
- Resale Disclosure Packages (Sprint 22)
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from .base import BaseTestModel


class AuditorExportStatus(str, Enum):
    """Status values for auditor exports"""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ResaleDisclosureStatus(str, Enum):
    """Status values for resale disclosure packages"""

    DRAFT = "draft"
    GENERATED = "generated"
    DELIVERED = "delivered"
    BILLED = "billed"
    CANCELLED = "cancelled"


class DisclosureState(str, Enum):
    """US states with specific disclosure requirements"""

    CA = "CA"  # California
    TX = "TX"  # Texas
    FL = "FL"  # Florida
    AZ = "AZ"  # Arizona
    NV = "NV"  # Nevada
    CO = "CO"  # Colorado
    DEFAULT = "DEFAULT"  # Default template


class AuditorExport(BaseTestModel):
    """Model for auditor export data"""

    id: UUID = Field(default_factory=uuid4)
    property_id: str
    start_date: date
    end_date: date
    status: AuditorExportStatus = AuditorExportStatus.PENDING
    export_type: str = "general_ledger"

    # File information
    file_url: Optional[str] = None
    file_hash: Optional[str] = None  # SHA-256
    file_size_bytes: Optional[int] = None
    row_count: Optional[int] = None

    # Evidence linking
    has_evidence_links: bool = False
    evidence_count: int = 0

    # Metadata
    requested_by: str
    created_at: datetime = Field(default_factory=datetime.now)
    generated_at: Optional[datetime] = None

    # Download tracking
    download_count: int = 0
    last_downloaded_at: Optional[datetime] = None
    last_downloaded_by: Optional[str] = None

    # CSV content (for testing)
    csv_content: Optional[str] = None

    @field_validator('end_date')
    def validate_date_range(cls, v, info):
        """Ensure end date is after start date"""
        if 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError("End date must be after start date")
        return v

    def generate(self) -> None:
        """Start generation process"""
        self.status = AuditorExportStatus.GENERATING

    def complete_generation(self) -> str:
        """Complete generation and return CSV content"""
        self.status = AuditorExportStatus.COMPLETED
        self.generated_at = datetime.now()
        return self.csv_content or ""

    def track_download(self, downloaded_by: str, ip_address: str) -> Dict[str, Any]:
        """Track a download of this export"""
        self.download_count += 1
        self.last_downloaded_at = datetime.now()
        self.last_downloaded_by = downloaded_by
        return {
            'downloaded_at': self.last_downloaded_at,
            'downloaded_by': downloaded_by,
            'ip_address': ip_address
        }

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Get audit trail of all actions on this export"""
        trail = [
            {
                'action': 'created',
                'user': self.requested_by,
                'timestamp': self.created_at
            }
        ]

        if self.generated_at:
            trail.append({
                'action': 'generated',
                'user': 'system',
                'timestamp': self.generated_at
            })

        # Add download entries (simplified - in real system would track all)
        if self.last_downloaded_at:
            trail.append({
                'action': 'downloaded',
                'user': self.last_downloaded_by,
                'timestamp': self.last_downloaded_at
            })

        return trail

    def save(self) -> None:
        """Save the export (mock for testing)"""
        if self.status == AuditorExportStatus.COMPLETED and hasattr(self, '_original_content'):
            if self.csv_content != self._original_content:
                raise ValueError("Cannot modify completed export")


class ResaleDisclosure(BaseTestModel):
    """Model for resale disclosure packages"""

    id: UUID = Field(default_factory=uuid4)
    property_id: str
    seller_id: str
    unit_number: str

    # Buyer information
    buyer_name: str
    buyer_email: str
    buyer_phone: Optional[str] = None

    # Disclosure details
    state: DisclosureState = DisclosureState.DEFAULT
    sale_date: date
    status: ResaleDisclosureStatus = ResaleDisclosureStatus.DRAFT

    # Financial snapshot
    financial_snapshot: Optional[Dict[str, Any]] = None

    # PDF information
    pdf_url: Optional[str] = None
    file_hash: Optional[str] = None  # SHA-256
    file_size_bytes: Optional[int] = None
    page_count: Optional[int] = None

    # Fee tracking
    fee_amount: Optional[Decimal] = None
    invoice_number: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    generated_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    billed_at: Optional[datetime] = None

    # Delivery tracking
    delivered_to: Optional[str] = None
    download_count: int = 0

    # Document attachments
    attached_document_count: int = 0
    total_document_size: int = 0

    def generate_pdf(self) -> Dict[str, Any]:
        """Generate PDF and update status"""
        self.status = ResaleDisclosureStatus.GENERATED
        self.generated_at = datetime.now()
        self.pdf_url = f"https://s3.amazonaws.com/disclosures/{self.id}.pdf"
        self.file_size_bytes = 150000  # Mock size
        return {
            'pdf_url': self.pdf_url,
            'file_size': self.file_size_bytes
        }

    def download(self, downloaded_by: str, ip_address: str) -> Dict[str, Any]:
        """Track download of disclosure"""
        self.download_count += 1
        return {
            'success': True,
            'downloaded_by': downloaded_by,
            'ip_address': ip_address
        }

    def deliver_to_buyer(self, cc_recipients: Optional[List[str]] = None,
                         subject: Optional[str] = None,
                         body: Optional[str] = None) -> Dict[str, Any]:
        """Deliver disclosure to buyer via email"""
        if self.status == ResaleDisclosureStatus.DRAFT:
            raise ValueError("Cannot deliver draft disclosure")

        self.status = ResaleDisclosureStatus.DELIVERED
        self.delivered_at = datetime.now()
        self.delivered_to = self.buyer_email

        return {
            'success': True,
            'email_sent': True,
            'delivered_at': self.delivered_at,
            'recipients': [self.buyer_email],
            'cc_recipients': cc_recipients or []
        }

    def create_invoice(self) -> Dict[str, Any]:
        """Create invoice for disclosure fee"""
        self.status = ResaleDisclosureStatus.BILLED
        self.billed_at = datetime.now()
        self.invoice_number = f"INV-{self.id.hex[:8].upper()}"

        # Calculate fee based on state
        if self.state == DisclosureState.CA:
            self.fee_amount = Decimal("395.00")
        elif self.state == DisclosureState.TX:
            self.fee_amount = Decimal("375.00")
        elif self.state == DisclosureState.FL:
            self.fee_amount = Decimal("250.00")
        else:
            self.fee_amount = Decimal("200.00")

        return {
            'invoice_number': self.invoice_number,
            'amount': self.fee_amount
        }

    def calculate_fee(self) -> Decimal:
        """Calculate fee for this disclosure"""
        if self.state == DisclosureState.CA:
            return Decimal("395.00")
        elif self.state == DisclosureState.TX:
            return Decimal("375.00")
        elif self.state == DisclosureState.FL:
            return Decimal("250.00")
        else:
            return Decimal("200.00")


class JournalEntry(BaseTestModel):
    """Model for journal entries used in auditor exports"""

    id: UUID = Field(default_factory=uuid4)
    property_id: str
    date: date
    description: str

    # Debit and credit entries
    debits: List[Dict[str, Any]]
    credits: List[Dict[str, Any]]

    # Evidence links
    evidence_urls: List[str] = []

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = "system"


class Violation(BaseTestModel):
    """Model for HOA violations with evidence"""

    id: UUID = Field(default_factory=uuid4)
    property_id: str
    member_id: str
    violation_type: str
    description: str
    evidence_urls: List[str] = []
    created_date: date = Field(default_factory=date.today)
    status: str = "open"


class WorkOrder(BaseTestModel):
    """Model for work orders with invoices"""

    id: UUID = Field(default_factory=uuid4)
    property_id: str
    category: str
    vendor: str
    amount: Decimal
    invoice_url: Optional[str] = None
    created_date: date = Field(default_factory=date.today)
    status: str = "pending"


class ARCRequest(BaseTestModel):
    """Model for Architectural Review Committee requests"""

    id: UUID = Field(default_factory=uuid4)
    property_id: str
    member_id: str
    request_type: str
    description: str
    plans_url: Optional[str] = None
    created_date: date = Field(default_factory=date.today)
    status: str = "pending"


class ARCApproval(BaseTestModel):
    """Model for ARC approvals (Phase 3)"""

    id: UUID = Field(default_factory=uuid4)
    property_id: str
    request_id: UUID
    approved: bool
    approved_by: str
    approval_date: date
    conditions: List[str] = []
    expiration_date: Optional[date] = None


class Invoice(BaseTestModel):
    """Model for invoices"""

    id: UUID = Field(default_factory=uuid4)
    invoice_number: str
    property_id: str
    amount: Decimal
    due_date: date
    paid: bool = False
    paid_date: Optional[date] = None


class EmailDelivery(BaseTestModel):
    """Model for email delivery tracking"""

    id: UUID = Field(default_factory=uuid4)
    recipient: str
    subject: str
    sent_at: datetime
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    opened: bool = False
    opened_at: Optional[datetime] = None