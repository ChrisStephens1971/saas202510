"""
Generators for Phase 4 Features (Sprint 20-22)

Includes generators for:
- Auditor Exports
- Resale Disclosure Packages
- Supporting evidence and documents
"""

import random
import string
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from faker import Faker

from ..models import (
    ARCRequest,
    AuditorExport,
    AuditorExportStatus,
    DisclosureState,
    JournalEntry,
    ResaleDisclosure,
    ResaleDisclosureStatus,
    Violation,
    WorkOrder,
)
from ..models.member import Member
from ..models.property import Property
from ..models.transaction import Transaction

fake = Faker()


class AuditorExportGenerator:
    """Generator for auditor export test data"""

    @staticmethod
    def create_export(
        property: Property,
        start_date: date,
        end_date: date,
        transactions: Optional[List[Transaction]] = None,
        journal_entries: Optional[List[JournalEntry]] = None,
        export_type: str = "general_ledger",
        requested_by: Optional[str] = None,
    ) -> AuditorExport:
        """Create an auditor export"""
        export = AuditorExport(
            property_id=property.id,
            start_date=start_date,
            end_date=end_date,
            export_type=export_type,
            requested_by=requested_by or f"auditor@{fake.domain_name()}",
            status=AuditorExportStatus.COMPLETED,
            file_url=f"https://s3.amazonaws.com/exports/export_{uuid4().hex[:8]}.csv",
            file_size_bytes=random.randint(100000, 5000000),
            row_count=len(transactions or []) + len(journal_entries or []),
        )

        # Generate mock CSV content
        export.csv_content = AuditorExportGenerator.generate_csv(export)
        export.file_hash = fake.sha256()

        return export

    @staticmethod
    def generate_csv(export: AuditorExport) -> str:
        """Generate CSV content for export"""
        csv_lines = [
            "date,journal_entry_id,account,description,debit,credit,running_balance,evidence_url"
        ]

        running_balance = Decimal("0.00")
        for i in range(10):  # Mock data
            date_str = (export.start_date + timedelta(days=i)).isoformat()
            entry_id = f"JE-{uuid4().hex[:8]}"
            account = f"{random.randint(1000, 9999)}-{fake.word().title()}"
            description = fake.sentence()
            debit = Decimal(str(random.randint(0, 10000)))
            credit = Decimal(str(random.randint(0, 10000)))
            running_balance += debit - credit
            evidence_url = "" if random.random() > 0.3 else fake.url()

            csv_lines.append(
                f"{date_str},{entry_id},{account},{description},{debit},{credit},{running_balance},{evidence_url}"
            )

        return "\n".join(csv_lines)

    @staticmethod
    def create_export_with_evidence(
        property: Property,
        start_date: date,
        end_date: date,
        violations: Optional[List[Violation]] = None,
        work_orders: Optional[List[WorkOrder]] = None,
        arc_requests: Optional[List[ARCRequest]] = None,
    ) -> AuditorExport:
        """Create export with evidence links"""
        export = AuditorExportGenerator.create_export(
            property=property,
            start_date=start_date,
            end_date=end_date,
        )

        export.has_evidence_links = True
        export.evidence_count = (
            len(violations or []) + len(work_orders or []) + len(arc_requests or [])
        )

        # Add evidence URLs to CSV
        csv_lines = export.csv_content.split("\n")

        # Add violations
        for violation in violations or []:
            for url in violation.evidence_urls:
                csv_lines.append(f"{date.today()},,,Violation Evidence,0,0,0,{url}")

        # Add work orders
        for work_order in work_orders or []:
            if work_order.invoice_url:
                csv_lines.append(
                    f"{date.today()},,,Work Order Invoice,0,0,0,{work_order.invoice_url}"
                )

        # Add ARC requests
        for arc_request in arc_requests or []:
            if arc_request.plans_url:
                csv_lines.append(
                    f"{date.today()},,,ARC Plans,0,0,0,{arc_request.plans_url}"
                )

        export.csv_content = "\n".join(csv_lines)
        return export

    @staticmethod
    def create_export_with_transactions(
        property: Property, transactions: List[Dict[str, Any]]
    ) -> AuditorExport:
        """Create export with specific transactions"""
        if not transactions:
            return AuditorExportGenerator.create_export(
                property=property,
                start_date=date.today() - timedelta(days=30),
                end_date=date.today(),
            )

        start_date = min(tx["date"] for tx in transactions)
        end_date = max(tx["date"] for tx in transactions)

        export = AuditorExportGenerator.create_export(
            property=property,
            start_date=start_date,
            end_date=end_date,
        )

        # Generate CSV with actual transactions
        csv_lines = [
            "date,journal_entry_id,account,description,debit,credit,running_balance,evidence_url"
        ]

        for tx in transactions:
            csv_lines.append(
                f"{tx['date']},{uuid4().hex[:8]},{tx['account']},"
                f"Transaction,{tx['debit']},{tx['credit']},{tx['expected_balance']},"
            )

        export.csv_content = "\n".join(csv_lines)
        return export

    @staticmethod
    def create_from_api_request(api_request: Dict[str, Any]) -> AuditorExport:
        """Create export from API request"""
        return AuditorExport(
            property_id=api_request["property_id"],
            start_date=date.fromisoformat(api_request["start_date"]),
            end_date=date.fromisoformat(api_request["end_date"]),
            export_type=api_request.get("export_format", "csv"),
            requested_by=api_request["requested_by"],
            status=AuditorExportStatus.PENDING,
        )

    @staticmethod
    def create_mock_export(
        id: Optional[str] = None,
        status: Optional[AuditorExportStatus] = None,
        created_date: Optional[datetime] = None,
        file_size: Optional[int] = None,
        date_range: Optional[str] = None,
        requested_by: Optional[str] = None,
    ) -> AuditorExport:
        """Create mock export for UI testing"""
        export = AuditorExport(
            id=UUID(id) if id else uuid4(),
            property_id="test-property",
            start_date=date.today() - timedelta(days=90),
            end_date=date.today(),
            status=status or AuditorExportStatus.COMPLETED,
            requested_by=requested_by or f"test@{fake.domain_name()}",
            created_at=created_date or datetime.now(),
            file_size_bytes=file_size,
        )

        if date_range:
            # Store as a property for UI display
            export.__dict__["date_range"] = date_range

        return export


class ResaleDisclosureGenerator:
    """Generator for resale disclosure test data"""

    @staticmethod
    def create_disclosure(
        property: Property,
        seller: Member,
        buyer: Dict[str, str],
        unit_number: str,
        sale_date: Optional[date] = None,
        state: str = "DEFAULT",
        capture_financials: bool = False,
    ) -> ResaleDisclosure:
        """Create a resale disclosure"""
        disclosure = ResaleDisclosure(
            property_id=property.id,
            seller_id=seller.id,
            unit_number=unit_number,
            buyer_name=buyer.get("name", fake.name()),
            buyer_email=buyer.get("email", fake.email()),
            buyer_phone=buyer.get("phone", fake.phone_number()),
            state=DisclosureState(state),
            sale_date=sale_date or date.today() + timedelta(days=30),
            status=ResaleDisclosureStatus.DRAFT,
        )

        if capture_financials:
            disclosure.financial_snapshot = {
                "account_balance": getattr(seller, "account_balance", Decimal("0.00")),
                "monthly_assessment": Decimal("350.00"),
                "special_assessments": Decimal("0.00"),
                "reserve_balance": Decimal("250000.00"),
                "as_of_date": date.today(),
            }

        return disclosure

    @staticmethod
    def generate_pdf(disclosure: ResaleDisclosure) -> bytes:
        """Generate PDF bytes for disclosure"""
        # Mock PDF generation - return dummy bytes
        pdf_content = f"PDF for Unit {disclosure.unit_number}".encode()
        # Make it look like a real PDF
        pdf_bytes = b"%PDF-1.4\n" + pdf_content + b"\n%%EOF"
        return pdf_bytes * 1000  # Make it substantial size

    @staticmethod
    def create_comprehensive_disclosure(
        property: Property,
        seller: Member,
        buyer: Dict[str, str],
        unit_number: str,
        financial_snapshot: Optional[Dict[str, Any]] = None,
        state: str = "CA",
        include_all_financials: bool = False,
        include_all_documents: bool = False,
    ) -> ResaleDisclosure:
        """Create comprehensive disclosure with all data"""
        disclosure = ResaleDisclosureGenerator.create_disclosure(
            property=property,
            seller=seller,
            buyer=buyer,
            unit_number=unit_number,
            state=state,
            capture_financials=True,
        )

        if financial_snapshot:
            disclosure.financial_snapshot = financial_snapshot

        if include_all_financials:
            disclosure.financial_snapshot.update(
                {
                    "operating_fund_balance": Decimal("150000.00"),
                    "reserve_fund_balance": Decimal("500000.00"),
                    "delinquency_rate": Decimal("5.2"),
                    "budget_variance": Decimal("-2500.00"),
                }
            )

        if include_all_documents:
            disclosure.attached_document_count = 10
            disclosure.total_document_size = 15000000  # 15MB

        return disclosure

    @staticmethod
    def create_disclosure_with_documents(
        property: Property,
        seller: Member,
        buyer: Dict[str, str],
        unit_number: str,
        attached_documents: List[Dict[str, Any]],
    ) -> ResaleDisclosure:
        """Create disclosure with document attachments"""
        disclosure = ResaleDisclosureGenerator.create_disclosure(
            property=property,
            seller=seller,
            buyer=buyer,
            unit_number=unit_number,
        )

        disclosure.attached_document_count = len(attached_documents)
        disclosure.total_document_size = sum(doc["size"] for doc in attached_documents)

        return disclosure

    @staticmethod
    def create_from_api(api_request: Dict[str, Any]) -> ResaleDisclosure:
        """Create disclosure from API request"""
        return ResaleDisclosure(
            property_id=api_request["property_id"],
            seller_id=api_request["seller_id"],
            unit_number=api_request["unit_number"],
            buyer_name=api_request["buyer_name"],
            buyer_email=api_request["buyer_email"],
            buyer_phone=api_request.get("buyer_phone"),
            state=DisclosureState(api_request.get("state", "DEFAULT")),
            sale_date=date.fromisoformat(api_request["sale_date"]),
            status=ResaleDisclosureStatus.DRAFT,
        )

    @staticmethod
    def generate_revenue_report(
        property: Property, year: int, disclosures: List[ResaleDisclosure]
    ) -> Dict[str, Any]:
        """Generate revenue report for disclosures"""
        total_revenue = sum(d.fee_amount or Decimal("0") for d in disclosures)
        total_packages = len(disclosures)

        return {
            "total_packages": total_packages,
            "total_revenue": total_revenue,
            "average_fee": total_revenue / total_packages if total_packages else Decimal("0"),
            "monthly_average": total_revenue / 12,
            "annual_projection": total_revenue,  # Simplified projection
        }


class EvidenceGenerator:
    """Generator for evidence URLs and documents"""

    @staticmethod
    def generate_evidence_url(evidence_type: str) -> str:
        """Generate a mock evidence URL"""
        file_id = uuid4().hex[:12]
        extensions = {
            "photo": "jpg",
            "document": "pdf",
            "invoice": "pdf",
            "plans": "pdf",
            "video": "mp4",
        }
        ext = extensions.get(evidence_type, "pdf")
        return f"https://s3.amazonaws.com/evidence/{evidence_type}_{file_id}.{ext}"

    @staticmethod
    def generate_multiple_urls(evidence_type: str, count: int) -> List[str]:
        """Generate multiple evidence URLs"""
        return [
            EvidenceGenerator.generate_evidence_url(evidence_type) for _ in range(count)
        ]


class ViolationGenerator:
    """Generator for violations with evidence"""

    @staticmethod
    def create_violation(
        property: Property,
        member: Member,
        violation_type: str,
        evidence_urls: Optional[List[str]] = None,
    ) -> Violation:
        """Create a violation with evidence"""
        return Violation(
            property_id=property.id,
            member_id=member.id,
            violation_type=violation_type,
            description=f"{violation_type.title()} violation at unit {member.unit_number}",
            evidence_urls=evidence_urls or EvidenceGenerator.generate_multiple_urls("photo", 2),
            created_date=date.today(),
            status="open",
        )


class WorkOrderGenerator:
    """Generator for work orders"""

    @staticmethod
    def create_work_order(
        property: Property,
        category: str,
        vendor: str,
        amount: Decimal,
        invoice_url: Optional[str] = None,
    ) -> WorkOrder:
        """Create a work order"""
        return WorkOrder(
            property_id=property.id,
            category=category,
            vendor=vendor,
            amount=amount,
            invoice_url=invoice_url or EvidenceGenerator.generate_evidence_url("invoice"),
            created_date=date.today(),
            status="pending",
        )


class ARCRequestGenerator:
    """Generator for ARC requests"""

    @staticmethod
    def create_arc_request(
        property: Property,
        member: Member,
        request_type: str,
        plans_url: Optional[str] = None,
    ) -> ARCRequest:
        """Create an ARC request"""
        return ARCRequest(
            property_id=property.id,
            member_id=member.id,
            request_type=request_type,
            description=f"{request_type.title()} modification request",
            plans_url=plans_url or EvidenceGenerator.generate_evidence_url("plans"),
            created_date=date.today(),
            status="pending",
        )


class LedgerGenerator:
    """Generator for ledger and journal entries"""

    @staticmethod
    def create_journal_entry(
        property: Property,
        date: date,
        description: str,
        debits: List[Dict[str, Any]],
        credits: List[Dict[str, Any]],
    ) -> JournalEntry:
        """Create a balanced journal entry"""
        return JournalEntry(
            property_id=property.id,
            date=date,
            description=description,
            debits=debits,
            credits=credits,
            evidence_urls=[],
        )

    @staticmethod
    def create_random_journal_entry(
        property: Property, date: date
    ) -> JournalEntry:
        """Create a random balanced journal entry"""
        amount = Decimal(str(random.randint(100, 10000)))

        debit_account = f"{random.randint(1000, 9999)}-{fake.word().title()}"
        credit_account = f"{random.randint(1000, 9999)}-{fake.word().title()}"

        return JournalEntry(
            property_id=property.id,
            date=date,
            description=fake.sentence(),
            debits=[{"account": debit_account, "amount": amount}],
            credits=[{"account": credit_account, "amount": amount}],
        )


class FinancialSnapshotGenerator:
    """Generator for financial snapshots"""

    @staticmethod
    def create_snapshot(
        property: Property,
        as_of_date: date,
        include_reserves: bool = False,
        include_budget: bool = False,
    ) -> Dict[str, Any]:
        """Create a financial snapshot"""
        snapshot = {
            "as_of_date": as_of_date,
            "operating_balance": Decimal("125000.00"),
            "accounts_receivable": Decimal("15000.00"),
            "accounts_payable": Decimal("8500.00"),
            "monthly_assessment_income": Decimal("35000.00"),
            "ytd_income": Decimal("350000.00"),
            "ytd_expenses": Decimal("320000.00"),
        }

        if include_reserves:
            snapshot.update(
                {
                    "reserve_balance": Decimal("450000.00"),
                    "reserve_contribution_ytd": Decimal("60000.00"),
                    "reserve_expenses_ytd": Decimal("25000.00"),
                    "percent_funded": Decimal("72.5"),
                }
            )

        if include_budget:
            snapshot.update(
                {
                    "budget_ytd": Decimal("340000.00"),
                    "actual_ytd": Decimal("320000.00"),
                    "variance_ytd": Decimal("20000.00"),
                    "variance_percent": Decimal("5.88"),
                }
            )

        return snapshot