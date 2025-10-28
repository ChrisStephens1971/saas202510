"""
Tests for Advanced Report Generation

Covers:
- Report template creation
- Custom column selection
- Report data generation
- Filtering (date, fund, property, member, amount)
- Summary calculations
- CSV export
- Excel export
- PDF export
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4
import os
import tempfile

import pytest

from qa_testing.reports import (
    AdvancedReportGenerator,
    ReportTemplate,
    ReportFormat,
    ReportFilter,
    ReportColumn,
    ColumnType,
)


@pytest.fixture
def tenant_id():
    """Create a test tenant ID."""
    return uuid4()


@pytest.fixture
def fund_id():
    """Create a test fund ID."""
    return uuid4()


@pytest.fixture
def property_id():
    """Create a test property ID."""
    return uuid4()


@pytest.fixture
def member_id():
    """Create a test member ID."""
    return uuid4()


@pytest.fixture
def sample_transaction_data(tenant_id, fund_id, property_id, member_id):
    """Create sample transaction data for testing."""
    return [
        {
            "transaction_date": date(2024, 1, 15),
            "reference": "TXN-001",
            "description": "Monthly dues",
            "account": "1100",
            "debit": Decimal("500.00"),
            "credit": Decimal("0.00"),
            "fund_id": fund_id,
            "property_id": property_id,
            "member_id": member_id,
            "amount": Decimal("500.00")
        },
        {
            "transaction_date": date(2024, 2, 15),
            "reference": "TXN-002",
            "description": "Assessment",
            "account": "1100",
            "debit": Decimal("1000.00"),
            "credit": Decimal("0.00"),
            "fund_id": fund_id,
            "property_id": property_id,
            "member_id": member_id,
            "amount": Decimal("1000.00")
        },
        {
            "transaction_date": date(2024, 3, 15),
            "reference": "TXN-003",
            "description": "Payment received",
            "account": "1000",
            "debit": Decimal("0.00"),
            "credit": Decimal("1500.00"),
            "fund_id": fund_id,
            "property_id": property_id,
            "member_id": member_id,
            "amount": Decimal("1500.00")
        },
    ]


@pytest.fixture
def sample_balance_sheet_data():
    """Create sample balance sheet data."""
    return [
        {
            "account_code": "1000",
            "account_name": "Cash",
            "debit_balance": Decimal("5000.00"),
            "credit_balance": Decimal("0.00"),
            "net_balance": Decimal("5000.00")
        },
        {
            "account_code": "1100",
            "account_name": "Accounts Receivable",
            "debit_balance": Decimal("3000.00"),
            "credit_balance": Decimal("0.00"),
            "net_balance": Decimal("3000.00")
        },
        {
            "account_code": "2000",
            "account_name": "Accounts Payable",
            "debit_balance": Decimal("0.00"),
            "credit_balance": Decimal("2000.00"),
            "net_balance": Decimal("-2000.00")
        },
    ]


@pytest.fixture
def basic_filter(tenant_id):
    """Create a basic report filter."""
    return ReportFilter(tenant_id=tenant_id)


# ==============================================================================
# Test Template Creation
# ==============================================================================

class TestTemplateCreation:
    """Test creating report templates."""

    def test_create_balance_sheet_template(self):
        """Test creating a balance sheet template."""
        template = AdvancedReportGenerator.create_balance_sheet_template()

        assert template.name == "Balance Sheet"
        assert template.report_type == "balance_sheet"
        assert len(template.columns) == 5
        assert template.show_summary is True
        assert template.sort_by == "account_code"

    def test_create_balance_sheet_template_with_custom_columns(self):
        """Test creating balance sheet with custom columns."""
        custom_columns = ["account_code", "account_name", "net_balance"]
        template = AdvancedReportGenerator.create_balance_sheet_template(columns=custom_columns)

        assert len(template.columns) == 3
        column_keys = [col.key for col in template.columns]
        assert column_keys == custom_columns

    def test_create_income_statement_template(self):
        """Test creating an income statement template."""
        template = AdvancedReportGenerator.create_income_statement_template()

        assert template.name == "Income Statement"
        assert template.report_type == "income_statement"
        assert len(template.columns) == 4
        assert template.group_by == "account_type"

    def test_create_transaction_detail_template(self):
        """Test creating a transaction detail template."""
        template = AdvancedReportGenerator.create_transaction_detail_template()

        assert template.name == "Transaction Detail"
        assert template.report_type == "transaction_detail"
        assert len(template.columns) == 6
        assert template.default_format == ReportFormat.EXCEL

    def test_create_transaction_detail_with_custom_columns(self):
        """Test creating transaction detail with custom columns."""
        custom_columns = ["transaction_date", "reference", "description"]
        template = AdvancedReportGenerator.create_transaction_detail_template(columns=custom_columns)

        assert len(template.columns) == 3


# ==============================================================================
# Test Report Generation
# ==============================================================================

class TestReportGeneration:
    """Test generating report data."""

    def test_generate_basic_report(
        self,
        sample_transaction_data,
        basic_filter
    ):
        """Test generating a basic report."""
        template = AdvancedReportGenerator.create_transaction_detail_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=basic_filter
        )

        assert report.row_count == 3
        assert len(report.rows) == 3
        assert report.template_id == template.template_id
        assert report.summary is not None

    def test_generate_report_with_date_filter(
        self,
        sample_transaction_data,
        tenant_id
    ):
        """Test report generation with date filtering."""
        filters = ReportFilter(
            tenant_id=tenant_id,
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 28)
        )

        template = AdvancedReportGenerator.create_transaction_detail_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=filters
        )

        assert report.row_count == 1
        assert report.rows[0]["transaction_date"] == date(2024, 2, 15)

    def test_generate_report_with_amount_filter(
        self,
        sample_transaction_data,
        tenant_id
    ):
        """Test report generation with amount filtering."""
        filters = ReportFilter(
            tenant_id=tenant_id,
            min_amount=Decimal("1000.00")
        )

        template = AdvancedReportGenerator.create_transaction_detail_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=filters
        )

        assert report.row_count == 2
        for row in report.rows:
            assert Decimal(str(row["amount"])) >= Decimal("1000.00")

    def test_generate_report_with_fund_filter(
        self,
        sample_transaction_data,
        tenant_id,
        fund_id
    ):
        """Test report generation with fund filtering."""
        # Add data for different fund
        other_fund_id = uuid4()
        sample_transaction_data.append({
            "transaction_date": date(2024, 4, 15),
            "reference": "TXN-004",
            "description": "Other fund transaction",
            "account": "1100",
            "debit": Decimal("200.00"),
            "credit": Decimal("0.00"),
            "fund_id": other_fund_id,
            "amount": Decimal("200.00")
        })

        filters = ReportFilter(
            tenant_id=tenant_id,
            fund_ids=[fund_id]
        )

        template = AdvancedReportGenerator.create_transaction_detail_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=filters
        )

        assert report.row_count == 3  # Should exclude other fund
        for row in report.rows:
            assert row["fund_id"] == fund_id

    def test_generate_report_with_sorting(
        self,
        sample_transaction_data,
        basic_filter
    ):
        """Test report generation with custom sorting."""
        template = AdvancedReportGenerator.create_transaction_detail_template()
        template.sort_by = "amount"
        template.sort_order = "desc"

        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=basic_filter
        )

        # Verify descending order by amount
        amounts = [Decimal(str(row["amount"])) for row in report.rows]
        assert amounts == sorted(amounts, reverse=True)


# ==============================================================================
# Test Summary Calculations
# ==============================================================================

class TestSummaryCalculations:
    """Test summary calculation functionality."""

    def test_calculate_summary_with_amounts(
        self,
        sample_transaction_data,
        basic_filter
    ):
        """Test summary calculation for amount columns."""
        template = AdvancedReportGenerator.create_transaction_detail_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=basic_filter
        )

        assert report.summary is not None
        assert "total_debit" in report.summary
        assert "total_credit" in report.summary
        assert report.summary["total_debit"] == 1500.00
        assert report.summary["total_credit"] == 1500.00

    def test_summary_with_no_data(self, tenant_id):
        """Test summary calculation with no data."""
        template = AdvancedReportGenerator.create_transaction_detail_template()
        filters = ReportFilter(tenant_id=tenant_id)

        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=[],
            filters=filters
        )

        assert report.summary is not None
        assert report.summary["total_rows"] == 0


# ==============================================================================
# Test CSV Export
# ==============================================================================

class TestCSVExport:
    """Test CSV export functionality."""

    def test_export_to_csv_basic(
        self,
        sample_transaction_data,
        basic_filter
    ):
        """Test basic CSV export."""
        template = AdvancedReportGenerator.create_transaction_detail_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=basic_filter
        )

        csv_output = AdvancedReportGenerator.export_to_csv(report, template)

        assert csv_output is not None
        lines = csv_output.strip().split('\n')
        assert len(lines) >= 4  # Header + 3 data rows + summary

        # Verify header
        header = lines[0]
        assert "Date" in header
        assert "Reference" in header
        assert "Description" in header

    def test_csv_export_includes_summary(
        self,
        sample_transaction_data,
        basic_filter
    ):
        """Test CSV export includes summary."""
        template = AdvancedReportGenerator.create_transaction_detail_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=basic_filter
        )

        csv_output = AdvancedReportGenerator.export_to_csv(report, template)

        assert "SUMMARY" in csv_output
        assert "total_debit" in csv_output

    def test_csv_export_with_custom_columns(
        self,
        sample_transaction_data,
        basic_filter
    ):
        """Test CSV export with custom columns."""
        template = AdvancedReportGenerator.create_transaction_detail_template(
            columns=["transaction_date", "reference", "description"]
        )
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=basic_filter
        )

        csv_output = AdvancedReportGenerator.export_to_csv(report, template)
        header = csv_output.split('\n')[0]

        # Should only have 3 columns
        assert header.count(",") == 2


# ==============================================================================
# Test Excel Export
# ==============================================================================

class TestExcelExport:
    """Test Excel export functionality."""

    def test_export_to_excel_creates_file(
        self,
        sample_transaction_data,
        basic_filter
    ):
        """Test Excel export creates a file."""
        template = AdvancedReportGenerator.create_transaction_detail_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=basic_filter
        )

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            filepath = tmp.name

        try:
            AdvancedReportGenerator.export_to_excel(report, template, filepath)

            assert os.path.exists(filepath)
            assert os.path.getsize(filepath) > 0
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_excel_export_with_summary(
        self,
        sample_balance_sheet_data,
        basic_filter
    ):
        """Test Excel export includes summary."""
        template = AdvancedReportGenerator.create_balance_sheet_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_balance_sheet_data,
            filters=basic_filter
        )

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            filepath = tmp.name

        try:
            AdvancedReportGenerator.export_to_excel(report, template, filepath)

            # Verify file was created
            assert os.path.exists(filepath)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)


# ==============================================================================
# Test PDF Export
# ==============================================================================

class TestPDFExport:
    """Test PDF export functionality."""

    def test_export_to_pdf_creates_file(
        self,
        sample_transaction_data,
        basic_filter
    ):
        """Test PDF export creates a file."""
        template = AdvancedReportGenerator.create_transaction_detail_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=basic_filter
        )

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            filepath = tmp.name

        try:
            AdvancedReportGenerator.export_to_pdf(report, template, filepath)

            assert os.path.exists(filepath)
            assert os.path.getsize(filepath) > 0
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_pdf_export_with_header_footer(
        self,
        sample_balance_sheet_data,
        basic_filter
    ):
        """Test PDF export with header and footer."""
        template = AdvancedReportGenerator.create_balance_sheet_template()
        template.show_header = True
        template.show_footer = True

        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_balance_sheet_data,
            filters=basic_filter
        )

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            filepath = tmp.name

        try:
            AdvancedReportGenerator.export_to_pdf(report, template, filepath)

            assert os.path.exists(filepath)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_pdf_export_with_summary(
        self,
        sample_balance_sheet_data,
        basic_filter
    ):
        """Test PDF export includes summary."""
        template = AdvancedReportGenerator.create_balance_sheet_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_balance_sheet_data,
            filters=basic_filter
        )

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            filepath = tmp.name

        try:
            AdvancedReportGenerator.export_to_pdf(report, template, filepath)

            assert os.path.exists(filepath)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)


# ==============================================================================
# Test Edge Cases
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_generate_report_with_empty_data(self, tenant_id):
        """Test generating report with no data."""
        template = AdvancedReportGenerator.create_transaction_detail_template()
        filters = ReportFilter(tenant_id=tenant_id)

        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=[],
            filters=filters
        )

        assert report.row_count == 0
        assert len(report.rows) == 0
        assert report.summary is not None

    def test_filter_with_no_matches(
        self,
        sample_transaction_data,
        tenant_id
    ):
        """Test filtering that returns no matches."""
        filters = ReportFilter(
            tenant_id=tenant_id,
            start_date=date(2024, 5, 1),
            end_date=date(2024, 5, 31)
        )

        template = AdvancedReportGenerator.create_transaction_detail_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=filters
        )

        assert report.row_count == 0

    def test_multiple_filters_combined(
        self,
        sample_transaction_data,
        tenant_id,
        fund_id
    ):
        """Test combining multiple filters."""
        filters = ReportFilter(
            tenant_id=tenant_id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 28),
            fund_ids=[fund_id],
            min_amount=Decimal("500.00")
        )

        template = AdvancedReportGenerator.create_transaction_detail_template()
        report = AdvancedReportGenerator.generate_report(
            template=template,
            data=sample_transaction_data,
            filters=filters
        )

        # Should match 2 transactions (Jan and Feb with amount >= 500)
        assert report.row_count == 2
