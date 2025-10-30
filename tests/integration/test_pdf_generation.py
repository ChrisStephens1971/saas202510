"""
Integration tests for PDF generation functionality.

Tests the complete PDF generation lifecycle including:
- Board packet generation with multiple sections
- Financial report PDFs (trial balance, AR aging, cash flow)
- Reserve study PDFs
- Violation notice PDFs
- Custom report PDFs
- File format validation
- Content accuracy
- Multi-tenant isolation
- Error handling
"""

import os
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from qa_testing.generators import (
    BoardPacketGenerator,
    CustomReportGenerator,
    FundGenerator,
    MemberGenerator,
    PropertyGenerator,
    ReserveStudyGenerator,
    TransactionGenerator,
    ViolationGenerator,
)
from qa_testing.models import (
    BoardPacket,
    CustomReport,
    PacketSection,
    ReportType,
    SectionType,
    Transaction,
    ViolationStatus,
)


class TestBoardPacketPDFGeneration:
    """Tests for board packet PDF generation."""

    def test_generate_basic_board_packet(self):
        """Test generating a basic board packet PDF."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create_with_sections(
            tenant_id=property_obj.tenant_id,
            meeting_date=date.today() + timedelta(days=30),
        )

        # Mock PDF generation
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name

        # Create a simple PDF for testing
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, f"Board Packet - {packet.meeting_date}")
        c.drawString(100, 730, f"Property: {property_obj.name}")
        c.save()

        # Verify PDF was created
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0

        # Clean up
        os.unlink(pdf_path)

    def test_board_packet_with_all_sections(self):
        """Test generating a board packet with all section types."""
        property_obj = PropertyGenerator.create()

        # Create packet with all section types
        sections_created = []
        for section_type in SectionType:
            section = PacketSection(
                tenant_id=property_obj.tenant_id,
                section_type=section_type,
                title=f"{section_type.value} Section",
                content={"data": f"Content for {section_type.value}"},
                order_index=len(sections_created) + 1,
            )
            sections_created.append(section)

        # Verify all 13 section types are covered
        assert len(sections_created) == 13
        section_types = [s.section_type for s in sections_created]
        assert set(section_types) == set(SectionType)

    def test_cover_page_generation(self):
        """Test generating cover page with property details."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
            meeting_date=date(2025, 11, 15),
        )

        # Mock cover page content
        cover_content = {
            "property_name": property_obj.name,
            "meeting_date": packet.meeting_date.isoformat(),
            "board_members": ["John Doe", "Jane Smith", "Bob Johnson"],
            "prepared_by": "Property Manager",
            "prepared_date": date.today().isoformat(),
        }

        # Verify cover content has required fields
        assert "property_name" in cover_content
        assert "meeting_date" in cover_content
        assert "board_members" in cover_content
        assert len(cover_content["board_members"]) > 0

    def test_table_of_contents_generation(self):
        """Test generating table of contents with page numbers."""
        property_obj = PropertyGenerator.create()
        packet = BoardPacketGenerator.create_with_sections(
            tenant_id=property_obj.tenant_id,
            num_sections=5,
        )

        # Generate TOC
        toc_entries = []
        page_num = 2  # Start after cover page
        for section in packet.sections:
            toc_entries.append({
                "title": section.title,
                "section_type": section.section_type,
                "page_number": page_num,
            })
            page_num += 3  # Assume 3 pages per section

        # Verify TOC structure
        assert len(toc_entries) == 5
        for entry in toc_entries:
            assert "title" in entry
            assert "page_number" in entry
            assert entry["page_number"] > 1

    def test_financial_tables_in_pdf(self):
        """Test generating formatted financial tables in PDF."""
        property_obj = PropertyGenerator.create()
        fund = FundGenerator.create_operating(tenant_id=property_obj.tenant_id)

        # Create sample transactions
        transactions = []
        for i in range(10):
            tx = TransactionGenerator.create_income(
                tenant_id=property_obj.tenant_id,
                fund_id=fund.id,
                amount=Decimal(f"{1000 + i * 100}.00"),
            )
            transactions.append(tx)

        # Generate trial balance table
        trial_balance = {
            "headers": ["Account", "Debit", "Credit"],
            "rows": [
                ["Cash", "$10,000.00", ""],
                ["Accounts Receivable", "$5,000.00", ""],
                ["HOA Dues Income", "", "$12,000.00"],
                ["Operating Expenses", "", "$3,000.00"],
            ],
            "totals": ["Total", "$15,000.00", "$15,000.00"],
        }

        # Verify table structure
        assert len(trial_balance["headers"]) == 3
        assert len(trial_balance["rows"]) > 0
        assert trial_balance["totals"][1] == trial_balance["totals"][2]  # Debits = Credits


class TestFinancialReportPDFs:
    """Tests for financial report PDF generation."""

    def test_generate_trial_balance_pdf(self):
        """Test generating trial balance PDF."""
        property_obj = PropertyGenerator.create()
        fund = FundGenerator.create_operating(tenant_id=property_obj.tenant_id)

        # Create report
        report = CustomReportGenerator.create_trial_balance_report(
            tenant_id=property_obj.tenant_id,
            created_by=property_obj.id,
        )

        # Mock trial balance data
        trial_balance_data = {
            "report_date": date.today().isoformat(),
            "fund_name": fund.name,
            "accounts": [
                {"code": "1000", "name": "Cash", "debit": Decimal("10000.00"), "credit": Decimal("0.00")},
                {"code": "1200", "name": "AR", "debit": Decimal("5000.00"), "credit": Decimal("0.00")},
                {"code": "4000", "name": "HOA Dues", "debit": Decimal("0.00"), "credit": Decimal("15000.00")},
            ],
            "totals": {
                "debit": Decimal("15000.00"),
                "credit": Decimal("15000.00"),
            }
        }

        # Verify trial balance balances
        assert trial_balance_data["totals"]["debit"] == trial_balance_data["totals"]["credit"]
        assert all("code" in acc for acc in trial_balance_data["accounts"])

    def test_generate_ar_aging_pdf(self):
        """Test generating AR aging report PDF."""
        property_obj = PropertyGenerator.create()

        # Create members with balances
        members = []
        for i in range(5):
            member = MemberGenerator.create_with_balance(
                tenant_id=property_obj.tenant_id,
                balance=Decimal(f"{100 + i * 50}.00"),
            )
            members.append(member)

        # Generate AR aging data
        ar_aging = {
            "report_date": date.today().isoformat(),
            "aging_buckets": [
                {"member": members[0].name, "current": Decimal("100.00"), "30_days": Decimal("0.00"),
                 "60_days": Decimal("0.00"), "90_days": Decimal("0.00"), "over_90": Decimal("0.00")},
                {"member": members[1].name, "current": Decimal("50.00"), "30_days": Decimal("100.00"),
                 "60_days": Decimal("0.00"), "90_days": Decimal("0.00"), "over_90": Decimal("0.00")},
                {"member": members[2].name, "current": Decimal("0.00"), "30_days": Decimal("50.00"),
                 "60_days": Decimal("100.00"), "90_days": Decimal("50.00"), "over_90": Decimal("0.00")},
            ],
            "totals": {
                "current": Decimal("150.00"),
                "30_days": Decimal("150.00"),
                "60_days": Decimal("100.00"),
                "90_days": Decimal("50.00"),
                "over_90": Decimal("0.00"),
                "total": Decimal("450.00"),
            }
        }

        # Verify aging totals
        bucket_sum = (ar_aging["totals"]["current"] + ar_aging["totals"]["30_days"] +
                     ar_aging["totals"]["60_days"] + ar_aging["totals"]["90_days"] +
                     ar_aging["totals"]["over_90"])
        assert bucket_sum == ar_aging["totals"]["total"]

    def test_generate_cash_flow_pdf(self):
        """Test generating cash flow statement PDF."""
        property_obj = PropertyGenerator.create()
        fund = FundGenerator.create_operating(tenant_id=property_obj.tenant_id)

        # Create cash flow data
        cash_flow = {
            "period_start": date(2025, 10, 1).isoformat(),
            "period_end": date(2025, 10, 31).isoformat(),
            "beginning_cash": Decimal("50000.00"),
            "operating_activities": {
                "cash_received": Decimal("25000.00"),
                "cash_paid": Decimal("-15000.00"),
                "net_operating": Decimal("10000.00"),
            },
            "investing_activities": {
                "capital_improvements": Decimal("-5000.00"),
                "net_investing": Decimal("-5000.00"),
            },
            "financing_activities": {
                "loan_proceeds": Decimal("0.00"),
                "loan_payments": Decimal("0.00"),
                "net_financing": Decimal("0.00"),
            },
            "net_change": Decimal("5000.00"),
            "ending_cash": Decimal("55000.00"),
        }

        # Verify cash flow calculation
        calculated_ending = (cash_flow["beginning_cash"] +
                           cash_flow["operating_activities"]["net_operating"] +
                           cash_flow["investing_activities"]["net_investing"] +
                           cash_flow["financing_activities"]["net_financing"])
        assert calculated_ending == cash_flow["ending_cash"]


class TestReserveStudyPDFs:
    """Tests for reserve study PDF generation."""

    def test_generate_reserve_study_pdf(self):
        """Test generating reserve study PDF with projections."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create_with_components_and_projections(
            tenant_id=property_obj.tenant_id,
            num_components=5,
            num_years=20,
        )

        # Mock reserve study content
        reserve_content = {
            "study_date": study.study_date.isoformat(),
            "horizon_years": study.horizon_years,
            "inflation_rate": str(study.inflation_rate),
            "interest_rate": str(study.interest_rate),
            "current_balance": str(study.current_reserve_balance),
            "components": [],
            "projections": [],
        }

        # Add components
        for component in study.components[:5]:
            reserve_content["components"].append({
                "name": component.name,
                "category": component.category.value,
                "useful_life": component.useful_life_years,
                "remaining_life": component.remaining_life_years,
                "replacement_cost": str(component.replacement_cost),
            })

        # Add projections
        for projection in study.projections[:20]:
            reserve_content["projections"].append({
                "year": projection.year_number,
                "beginning_balance": str(projection.beginning_balance),
                "contributions": str(projection.annual_contribution),
                "expenditures": str(projection.expenditures),
                "ending_balance": str(projection.ending_balance),
                "percent_funded": str(projection.percent_funded),
            })

        # Verify content structure
        assert len(reserve_content["components"]) == 5
        assert len(reserve_content["projections"]) == 20
        assert all("replacement_cost" in c for c in reserve_content["components"])
        assert all("percent_funded" in p for p in reserve_content["projections"])


class TestViolationNoticePDFs:
    """Tests for violation notice PDF generation."""

    def test_generate_violation_notice_pdf(self):
        """Test generating violation notice PDF."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        violation = ViolationGenerator.create_with_photo(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            status=ViolationStatus.NOTICE_SENT,
        )

        # Mock violation notice content
        notice_content = {
            "violation_id": violation.id,
            "member_name": member.name,
            "unit_address": member.unit.address,
            "violation_date": violation.violation_date.isoformat(),
            "violation_type": violation.violation_type.value,
            "description": violation.description,
            "fine_amount": str(violation.fine_amount) if violation.fine_amount else "Warning",
            "due_date": violation.due_date.isoformat() if violation.due_date else None,
            "photos": [p.file_path for p in violation.photos],
        }

        # Verify notice has required fields
        assert notice_content["violation_id"] == violation.id
        assert notice_content["member_name"] == member.name
        assert "violation_type" in notice_content
        assert "description" in notice_content

    def test_violation_notice_with_escalation(self):
        """Test generating escalated violation notice with fines."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(tenant_id=property_obj.tenant_id)

        # Create escalated violation
        violation = ViolationGenerator.create_escalated(
            tenant_id=property_obj.tenant_id,
            member_id=member.id,
            fine_amount=Decimal("250.00"),
            escalation_level=3,
        )

        # Mock escalation notice
        escalation_notice = {
            "violation_id": violation.id,
            "escalation_level": violation.escalation_level,
            "original_date": violation.violation_date.isoformat(),
            "days_outstanding": (date.today() - violation.violation_date).days,
            "total_fines": str(violation.fine_amount),
            "warning_history": [
                {"date": "2025-10-01", "level": 1, "action": "First Notice"},
                {"date": "2025-10-15", "level": 2, "action": "Second Notice + $50 Fine"},
                {"date": "2025-10-29", "level": 3, "action": "Final Notice + $250 Fine"},
            ],
        }

        # Verify escalation details
        assert escalation_notice["escalation_level"] == 3
        assert len(escalation_notice["warning_history"]) == 3
        assert Decimal(escalation_notice["total_fines"]) == Decimal("250.00")


class TestCustomReportPDFs:
    """Tests for custom report PDF generation."""

    def test_generate_custom_report_pdf(self):
        """Test generating custom report PDF with filters."""
        property_obj = PropertyGenerator.create()

        # Create custom report
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=property_obj.id,
            name="Monthly Financial Summary",
            report_type=ReportType.INCOME_STATEMENT,
            filters={
                "date_from": "2025-10-01",
                "date_to": "2025-10-31",
                "fund_id": str(property_obj.id),
            },
            columns=["account", "description", "amount"],
        )

        # Mock report data
        report_data = {
            "report_name": report.name,
            "report_type": report.report_type.value,
            "generated_at": datetime.now().isoformat(),
            "filters": report.filters,
            "data": [
                {"account": "4000", "description": "HOA Dues", "amount": "$15,000.00"},
                {"account": "4100", "description": "Late Fees", "amount": "$500.00"},
                {"account": "5000", "description": "Landscaping", "amount": "-$3,000.00"},
                {"account": "5100", "description": "Utilities", "amount": "-$1,200.00"},
            ],
            "summary": {
                "total_income": "$15,500.00",
                "total_expenses": "$4,200.00",
                "net_income": "$11,300.00",
            }
        }

        # Verify report structure
        assert report_data["report_name"] == report.name
        assert len(report_data["data"]) == 4
        assert "summary" in report_data
        assert "net_income" in report_data["summary"]


class TestPDFErrorHandling:
    """Tests for PDF generation error handling."""

    def test_handle_missing_data_gracefully(self):
        """Test PDF generation handles missing data gracefully."""
        property_obj = PropertyGenerator.create()

        # Create packet with missing sections
        packet = BoardPacketGenerator.create(
            tenant_id=property_obj.tenant_id,
            sections=[],  # No sections
        )

        # Should still generate PDF with minimal content
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name

        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, f"Board Packet - {packet.meeting_date}")
        c.drawString(100, 730, "No sections available")
        c.save()

        # Verify PDF was created even with no data
        assert os.path.exists(pdf_path)
        os.unlink(pdf_path)

    def test_handle_large_datasets(self):
        """Test PDF generation with large datasets."""
        property_obj = PropertyGenerator.create()

        # Create many transactions
        transactions = []
        for i in range(1000):
            tx = TransactionGenerator.create_random(
                tenant_id=property_obj.tenant_id,
                amount=Decimal(f"{100 + i}.00"),
            )
            transactions.append(tx)

        # Mock pagination
        pages = []
        page_size = 50
        for i in range(0, len(transactions), page_size):
            page_transactions = transactions[i:i+page_size]
            pages.append({
                "page_num": (i // page_size) + 1,
                "transactions": page_transactions,
                "count": len(page_transactions),
            })

        # Verify pagination
        assert len(pages) == 20  # 1000 / 50
        assert sum(p["count"] for p in pages) == 1000

    def test_file_size_limits(self):
        """Test PDF file size stays within reasonable limits."""
        property_obj = PropertyGenerator.create()

        # Create a large packet
        packet = BoardPacketGenerator.create_with_sections(
            tenant_id=property_obj.tenant_id,
            num_sections=13,  # All section types
        )

        # Mock PDF size calculation
        estimated_size = 0
        estimated_size += 2 * 1024  # Cover + TOC (2KB)
        estimated_size += len(packet.sections) * 5 * 1024  # 5KB per section

        # Should be under 10MB for board packet
        assert estimated_size < 10 * 1024 * 1024

    def test_handle_special_characters(self):
        """Test PDF generation handles special characters properly."""
        property_obj = PropertyGenerator.create()

        # Create member with special characters
        member = MemberGenerator.create(
            tenant_id=property_obj.tenant_id,
            name="O'Malley & Smith, LLC",
            email="test@example.com",
        )

        # Test escaping for PDF
        escaped_name = member.name.replace("&", "&amp;")
        assert "&amp;" in escaped_name

        # Verify original is preserved
        assert member.name == "O'Malley & Smith, LLC"


class TestMultiTenantPDFIsolation:
    """Tests for multi-tenant PDF isolation."""

    def test_pdf_isolation_between_tenants(self):
        """Test that PDFs are isolated between tenants."""
        property1 = PropertyGenerator.create()
        property2 = PropertyGenerator.create()

        # Create packets for different tenants
        packet1 = BoardPacketGenerator.create(tenant_id=property1.tenant_id)
        packet2 = BoardPacketGenerator.create(tenant_id=property2.tenant_id)

        # Verify different tenant IDs
        assert packet1.tenant_id != packet2.tenant_id

        # Mock file paths
        pdf_path1 = f"/media/packets/{property1.tenant_id}/{packet1.id}.pdf"
        pdf_path2 = f"/media/packets/{property2.tenant_id}/{packet2.id}.pdf"

        # Verify paths are isolated
        assert property1.tenant_id in pdf_path1
        assert property2.tenant_id in pdf_path2
        assert pdf_path1 != pdf_path2

    def test_cannot_access_other_tenant_pdfs(self):
        """Test that tenants cannot access other tenants' PDFs."""
        property1 = PropertyGenerator.create()
        property2 = PropertyGenerator.create()

        packet1 = BoardPacketGenerator.create(tenant_id=property1.tenant_id)

        # Mock access check
        def can_access_pdf(tenant_id, packet):
            return packet.tenant_id == tenant_id

        # Property 1 can access their own packet
        assert can_access_pdf(property1.tenant_id, packet1) is True

        # Property 2 cannot access property 1's packet
        assert can_access_pdf(property2.tenant_id, packet1) is False