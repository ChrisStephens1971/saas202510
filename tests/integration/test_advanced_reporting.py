"""
Integration tests for advanced reporting functionality.

Tests the complete custom reporting lifecycle including:
- Custom report creation for all 9 report types
- Report filter and column configurations
- Report sharing (public vs private)
- Favorite reports
- Report execution tracking
- Execution status transitions (PENDING → RUNNING → COMPLETED/FAILED)
- Result caching and cache hits
- Execution performance tracking
- Error handling and failure scenarios
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from qa_testing.generators import (
    CustomReportGenerator,
    PropertyGenerator,
    ReportExecutionGenerator,
)
from qa_testing.models import (
    CustomReport,
    ExecutionStatus,
    ReportExecution,
    ReportType,
)


class TestCustomReportCreation:
    """Tests for custom report creation and validation."""

    def test_create_general_ledger_report(self):
        """Test creating a general ledger report."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id  # Use property as user for testing

        report = CustomReportGenerator.create_general_ledger_report(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        assert report.report_type == ReportType.GENERAL_LEDGER
        assert "date" in report.columns
        assert "account_code" in report.columns
        assert len(report.columns) > 0
        assert isinstance(report.filters, dict)

    def test_create_trial_balance_report(self):
        """Test creating a trial balance report."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_trial_balance_report(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        assert report.report_type == ReportType.TRIAL_BALANCE
        assert "account_code" in report.columns
        assert "debit_balance" in report.columns
        assert "credit_balance" in report.columns

    def test_create_income_statement_report(self):
        """Test creating an income statement report."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_income_statement_report(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        assert report.report_type == ReportType.INCOME_STATEMENT
        assert "account_name" in report.columns
        assert report.name.lower().find("income") >= 0

    def test_create_balance_sheet_report(self):
        """Test creating a balance sheet report."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_balance_sheet_report(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        assert report.report_type == ReportType.BALANCE_SHEET
        assert "current_balance" in report.columns

    def test_create_cash_flow_report(self):
        """Test creating a cash flow statement report."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_cash_flow_report(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        assert report.report_type == ReportType.CASH_FLOW
        assert "category" in report.columns

    def test_create_ar_aging_report(self):
        """Test creating an AR aging report."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_ar_aging_report(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        assert report.report_type == ReportType.AR_AGING
        assert "owner_name" in report.columns
        assert "30_days" in report.columns
        assert "60_days" in report.columns
        assert "90_days" in report.columns

    def test_create_owner_ledger_report(self):
        """Test creating an owner ledger report."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_owner_ledger_report(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        assert report.report_type == ReportType.OWNER_LEDGER
        assert "charges" in report.columns
        assert "payments" in report.columns
        assert "balance" in report.columns

    def test_create_budget_variance_report(self):
        """Test creating a budget variance report."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_budget_variance_report(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        assert report.report_type == ReportType.BUDGET_VARIANCE
        assert "budget" in report.columns
        assert "actual" in report.columns
        assert "variance" in report.columns

    def test_create_reserve_funding_report(self):
        """Test creating a reserve funding report."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_reserve_funding_report(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        assert report.report_type == ReportType.RESERVE_FUNDING
        assert "beginning_balance" in report.columns
        assert "contributions" in report.columns
        assert "ending_balance" in report.columns

    def test_create_all_report_types(self):
        """Test creating reports for all 9 report types."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        reports = []
        for report_type in ReportType:
            report = CustomReportGenerator.create_for_type(
                tenant_id=property_obj.tenant_id,
                created_by=user_id,
                report_type=report_type,
            )
            reports.append(report)
            assert report.report_type == report_type

        # Verify we created all 9 types
        assert len(reports) == 9

    def test_report_columns_not_empty(self):
        """Test that reports must have at least one column."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        with pytest.raises(ValueError, match="columns must contain at least one column"):
            CustomReport(
                tenant_id=property_obj.tenant_id,
                name="Empty Report",
                report_type=ReportType.GENERAL_LEDGER,
                columns=[],  # Invalid: empty columns
                created_by=user_id,
            )


class TestReportFilters:
    """Tests for report filter configurations."""

    def test_report_filters_as_dict(self):
        """Test that report filters are stored as dictionary."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            filters={"fund": str(property_obj.id), "date_from": "2025-01-01"},
        )

        assert isinstance(report.filters, dict)
        assert "fund" in report.filters
        assert "date_from" in report.filters

    def test_report_columns_as_list(self):
        """Test that report columns are stored as list of strings."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            columns=["date", "account", "amount"],
        )

        assert isinstance(report.columns, list)
        assert all(isinstance(col, str) for col in report.columns)
        assert len(report.columns) == 3

    def test_report_sort_by_structure(self):
        """Test that sort_by has correct structure."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            sort_by=[
                {"field": "date", "direction": "desc"},
                {"field": "amount", "direction": "asc"},
            ],
        )

        assert isinstance(report.sort_by, list)
        assert len(report.sort_by) == 2
        assert report.sort_by[0]["field"] == "date"
        assert report.sort_by[0]["direction"] == "desc"
        assert report.sort_by[1]["direction"] == "asc"

    def test_sort_by_validation(self):
        """Test that sort_by entries must have required fields."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        # Missing 'direction' field
        with pytest.raises(ValueError, match="sort_by items must have 'field' and 'direction' keys"):
            CustomReport(
                tenant_id=property_obj.tenant_id,
                name="Bad Sort Report",
                report_type=ReportType.GENERAL_LEDGER,
                columns=["date", "amount"],
                sort_by=[{"field": "date"}],  # Missing direction
                created_by=user_id,
            )

    def test_sort_by_direction_validation(self):
        """Test that sort_by direction must be asc or desc."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        with pytest.raises(ValueError, match="sort_by direction must be 'asc' or 'desc'"):
            CustomReport(
                tenant_id=property_obj.tenant_id,
                name="Bad Direction Report",
                report_type=ReportType.GENERAL_LEDGER,
                columns=["date", "amount"],
                sort_by=[{"field": "date", "direction": "invalid"}],  # Bad direction
                created_by=user_id,
            )


class TestReportSharing:
    """Tests for public vs private reports and favorites."""

    def test_create_private_report(self):
        """Test creating a private report (default)."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            is_public=False,
        )

        assert report.is_public is False

    def test_create_public_report(self):
        """Test creating a public (shared) report."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            is_public=True,
        )

        assert report.is_public is True

    def test_mark_report_as_favorite(self):
        """Test marking a report as favorite."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            is_favorite=True,
        )

        assert report.is_favorite is True

    def test_report_not_favorite_by_default(self):
        """Test that reports are not favorites by default."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        assert report.is_favorite is False


class TestReportExecution:
    """Tests for report execution tracking."""

    def test_create_completed_execution(self):
        """Test creating a completed report execution."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.is_completed() is True
        assert execution.row_count >= 0
        assert execution.execution_time_ms > 0
        assert execution.completed_at is not None

    def test_create_failed_execution(self):
        """Test creating a failed report execution."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_failed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        assert execution.status == ExecutionStatus.FAILED
        assert execution.is_failed() is True
        assert len(execution.error_message) > 0
        assert execution.row_count == 0

    def test_create_pending_execution(self):
        """Test creating a pending report execution."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_pending(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        assert execution.status == ExecutionStatus.PENDING
        assert execution.completed_at is None
        assert execution.execution_time_ms == 0

    def test_execution_status_transitions(self):
        """Test that execution transitions through statuses correctly."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        # Start with PENDING
        execution_pending = ReportExecutionGenerator.create_pending(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )
        assert execution_pending.status == ExecutionStatus.PENDING

        # Then RUNNING
        execution_running = ReportExecutionGenerator.create(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
            status=ExecutionStatus.RUNNING,
            completed_at=None,
        )
        assert execution_running.status == ExecutionStatus.RUNNING
        assert execution_running.is_running() is True

        # Finally COMPLETED
        execution_completed = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )
        assert execution_completed.status == ExecutionStatus.COMPLETED


class TestExecutionCaching:
    """Tests for report result caching."""

    def test_completed_execution_has_cache(self):
        """Test that completed executions have result cache."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        assert execution.result_cache is not None
        assert execution.is_cached() is True
        assert isinstance(execution.result_cache, dict)

    def test_failed_execution_no_cache(self):
        """Test that failed executions don't have result cache."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_failed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        assert execution.result_cache is None
        assert execution.is_cached() is False

    def test_cache_structure(self):
        """Test that result cache has expected structure."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
            row_count=500,
        )

        # Cache should contain row metadata
        assert "rows" in execution.result_cache
        assert execution.result_cache["rows"] == 500


class TestExecutionPerformance:
    """Tests for execution performance tracking."""

    def test_execution_time_tracked_in_milliseconds(self):
        """Test that execution time is tracked in milliseconds."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
            execution_time_ms=1250,
        )

        assert execution.execution_time_ms == 1250
        assert isinstance(execution.execution_time_ms, int)

    def test_row_count_tracked(self):
        """Test that row count is tracked."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
            row_count=5432,
        )

        assert execution.row_count == 5432
        assert isinstance(execution.row_count, int)

    def test_execution_time_matches_duration(self):
        """Test that execution_time_ms matches completed_at - started_at."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        started = datetime.now()
        execution_time = 2500  # 2.5 seconds
        completed = started + timedelta(milliseconds=execution_time)

        execution = ReportExecutionGenerator.create(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
            status=ExecutionStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            execution_time_ms=execution_time,
        )

        # Calculate actual duration
        duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
        assert abs(execution.execution_time_ms - duration_ms) <= 100  # Allow 100ms tolerance


class TestExecutionFailures:
    """Tests for execution failure scenarios."""

    def test_failed_execution_has_error_message(self):
        """Test that failed executions have error messages."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_failed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
            error_message="Query timeout after 30 seconds",
        )

        assert execution.status == ExecutionStatus.FAILED
        assert execution.error_message == "Query timeout after 30 seconds"
        assert len(execution.error_message) > 0

    def test_completed_execution_no_error_message(self):
        """Test that completed executions don't have error messages."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.error_message == ""

    def test_failed_execution_has_zero_rows(self):
        """Test that failed executions have zero rows."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_failed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        assert execution.row_count == 0


class TestReportDataTypes:
    """Tests for proper data type usage in reporting."""

    def test_execution_timestamps_use_datetime(self):
        """Test that execution timestamps use datetime for precise tracking."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        # started_at and completed_at should use datetime
        assert isinstance(execution.started_at, datetime)
        assert isinstance(execution.completed_at, datetime)

    def test_completed_at_after_started_at(self):
        """Test that completed_at is after started_at."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        assert execution.completed_at > execution.started_at

    def test_completed_at_validation(self):
        """Test that completed_at cannot be before started_at."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        started = datetime.now()
        completed = started - timedelta(seconds=10)  # Invalid: before started

        with pytest.raises(ValueError, match="completed_at must be after started_at"):
            ReportExecution(
                tenant_id=property_obj.tenant_id,
                custom_report_id=report.id,
                status=ExecutionStatus.COMPLETED,
                started_at=started,
                completed_at=completed,  # Invalid
                row_count=100,
                execution_time_ms=1000,
                executed_by=user_id,
            )

    def test_execution_time_is_positive_integer(self):
        """Test that execution_time_ms is a positive integer."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        assert isinstance(execution.execution_time_ms, int)
        assert execution.execution_time_ms >= 0

    def test_row_count_is_non_negative_integer(self):
        """Test that row_count is a non-negative integer."""
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        execution = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        assert isinstance(execution.row_count, int)
        assert execution.row_count >= 0
