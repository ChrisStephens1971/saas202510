"""
Property-based tests for reporting invariants.

Uses Hypothesis to verify that reporting operations maintain critical invariants:
- Execution time matches completed_at - started_at duration
- Completed executions have completed_at timestamp
- Failed executions have error messages
- Status transitions are valid (PENDING → RUNNING → COMPLETED/FAILED)
- Columns list is never empty
- Sort_by structure is always valid (field + direction)
- Filters are always valid dictionaries
- Timestamps use datetime for execution tracking
- All integer fields (execution_time_ms, row_count) are non-negative
"""

from datetime import datetime, timedelta

from hypothesis import assume, given
from hypothesis import strategies as st
import pytest

from qa_testing.generators import (
    CustomReportGenerator,
    PropertyGenerator,
    ReportExecutionGenerator,
)
from qa_testing.models import ExecutionStatus, ReportType


# Custom strategies for reporting tests
@st.composite
def execution_time_strategy(draw):
    """Generate realistic execution times (50ms to 10000ms)."""
    return draw(st.integers(min_value=50, max_value=10000))


@st.composite
def row_count_strategy(draw):
    """Generate realistic row counts (0 to 10000)."""
    return draw(st.integers(min_value=0, max_value=10000))


@st.composite
def report_type_strategy(draw):
    """Generate random report type."""
    return draw(st.sampled_from(list(ReportType)))


@st.composite
def sort_direction_strategy(draw):
    """Generate valid sort directions."""
    return draw(st.sampled_from(["asc", "desc"]))


class TestReportExecutionInvariants:
    """Property-based tests for report execution invariants."""

    @given(
        execution_time_ms=execution_time_strategy(),
    )
    def test_execution_time_matches_duration(self, execution_time_ms):
        """
        INVARIANT: execution_time_ms must match completed_at - started_at.

        When a report completes, the execution time should match the actual duration.
        """
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        started = datetime.now()
        completed = started + timedelta(milliseconds=execution_time_ms)

        execution = ReportExecutionGenerator.create(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
            status=ExecutionStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            execution_time_ms=execution_time_ms,
        )

        # Calculate actual duration
        duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)

        # Allow small rounding differences (within 100ms)
        assert abs(execution.execution_time_ms - duration_ms) <= 100

    @given(
        execution_time_ms=execution_time_strategy(),
        row_count=row_count_strategy(),
    )
    def test_completed_at_always_after_started_at(self, execution_time_ms, row_count):
        """
        INVARIANT: completed_at must always be after started_at.

        A report cannot complete before it starts.
        """
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
            execution_time_ms=execution_time_ms,
            row_count=row_count,
        )

        assert execution.completed_at > execution.started_at

    @given(
        execution_time_ms=execution_time_strategy(),
    )
    def test_completed_execution_has_completed_timestamp(self, execution_time_ms):
        """
        INVARIANT: COMPLETED status requires completed_at timestamp.

        All completed executions must have a completion timestamp.
        """
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
            execution_time_ms=execution_time_ms,
        )

        if execution.status == ExecutionStatus.COMPLETED:
            assert execution.completed_at is not None

    def test_failed_execution_has_error_message(self):
        """
        INVARIANT: FAILED status requires error_message.

        All failed executions must have an error message explaining the failure.
        """
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

        if execution.status == ExecutionStatus.FAILED:
            assert len(execution.error_message) > 0


class TestReportFilterInvariants:
    """Property-based tests for report filter invariants."""

    @given(
        report_type=report_type_strategy(),
    )
    def test_filters_always_valid_dict(self, report_type):
        """
        INVARIANT: filters must always be a valid dictionary.

        Report filters should be a dict, never None or other types.
        """
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_for_type(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            report_type=report_type,
        )

        assert isinstance(report.filters, dict)

    @given(
        report_type=report_type_strategy(),
    )
    def test_columns_is_list_of_strings(self, report_type):
        """
        INVARIANT: columns must be a list of strings.

        Report columns should be list[str], never other types.
        """
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_for_type(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            report_type=report_type,
        )

        assert isinstance(report.columns, list)
        assert all(isinstance(col, str) for col in report.columns)

    @given(
        report_type=report_type_strategy(),
    )
    def test_columns_never_empty(self, report_type):
        """
        INVARIANT: columns must contain at least one column.

        A report must display at least one column.
        """
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_for_type(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            report_type=report_type,
        )

        assert len(report.columns) > 0

    @given(
        report_type=report_type_strategy(),
    )
    def test_sort_by_structure_valid(self, report_type):
        """
        INVARIANT: sort_by entries must have 'field' and 'direction' keys.

        Each sort entry must be a valid dict with required keys.
        """
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_for_type(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            report_type=report_type,
        )

        assert isinstance(report.sort_by, list)
        for sort_item in report.sort_by:
            assert "field" in sort_item
            assert "direction" in sort_item
            assert sort_item["direction"] in ["asc", "desc"]


class TestExecutionStatusInvariants:
    """Property-based tests for execution status transition invariants."""

    def test_pending_execution_no_completed_timestamp(self):
        """
        INVARIANT: PENDING status should not have completed_at.

        Pending executions haven't completed yet.
        """
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

        if execution.status == ExecutionStatus.PENDING:
            assert execution.completed_at is None

    def test_pending_execution_zero_time(self):
        """
        INVARIANT: PENDING status should have zero execution_time_ms.

        Pending executions haven't run yet.
        """
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

        if execution.status == ExecutionStatus.PENDING:
            assert execution.execution_time_ms == 0

    def test_failed_execution_zero_rows(self):
        """
        INVARIANT: FAILED status should have zero row_count.

        Failed executions don't produce results.
        """
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

        if execution.status == ExecutionStatus.FAILED:
            assert execution.row_count == 0

    @given(
        execution_time_ms=execution_time_strategy(),
    )
    def test_completed_execution_no_error_message(self, execution_time_ms):
        """
        INVARIANT: COMPLETED status should have empty error_message.

        Successful executions don't have errors.
        """
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
            execution_time_ms=execution_time_ms,
        )

        if execution.status == ExecutionStatus.COMPLETED:
            assert execution.error_message == ""


class TestDataTypeInvariants:
    """Property-based tests for reporting data type invariants."""

    @given(
        execution_time_ms=execution_time_strategy(),
        row_count=row_count_strategy(),
    )
    def test_execution_timestamps_use_datetime(self, execution_time_ms, row_count):
        """
        INVARIANT: started_at and completed_at must use datetime.

        Execution tracking requires precise timestamps, so use datetime not date.
        """
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
            execution_time_ms=execution_time_ms,
            row_count=row_count,
        )

        # Verify datetime type
        assert isinstance(execution.started_at, datetime)
        assert isinstance(execution.completed_at, datetime)

    @given(
        execution_time_ms=execution_time_strategy(),
    )
    def test_execution_time_ms_is_positive_integer(self, execution_time_ms):
        """
        INVARIANT: execution_time_ms must be a non-negative integer.

        Execution time cannot be negative.
        """
        # Ensure non-negative
        assume(execution_time_ms >= 0)

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
            execution_time_ms=execution_time_ms,
        )

        assert isinstance(execution.execution_time_ms, int)
        assert execution.execution_time_ms >= 0

    @given(
        row_count=row_count_strategy(),
    )
    def test_row_count_is_non_negative_integer(self, row_count):
        """
        INVARIANT: row_count must be a non-negative integer.

        Row count cannot be negative.
        """
        # Ensure non-negative
        assume(row_count >= 0)

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
            row_count=row_count,
        )

        assert isinstance(execution.row_count, int)
        assert execution.row_count >= 0

    @given(
        report_type=report_type_strategy(),
    )
    def test_all_report_types_create_valid_reports(self, report_type):
        """
        INVARIANT: All ReportType enum values produce valid reports.

        Every report type must be supported by generators.
        """
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create_for_type(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            report_type=report_type,
        )

        assert report.report_type == report_type
        assert report.report_type in ReportType

    @given(
        field_name=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=("Cs",))),
        direction=sort_direction_strategy(),
    )
    def test_sort_by_accepts_any_valid_field(self, field_name, direction):
        """
        INVARIANT: sort_by can accept any field name with valid direction.

        Sort configuration should be flexible for any column name.
        """
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id

        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            columns=["date", "amount"],
            sort_by=[{"field": field_name, "direction": direction}],
        )

        assert len(report.sort_by) == 1
        assert report.sort_by[0]["field"] == field_name
        assert report.sort_by[0]["direction"] == direction

    @given(
        execution_time_ms=execution_time_strategy(),
    )
    def test_result_cache_is_dict_or_none(self, execution_time_ms):
        """
        INVARIANT: result_cache must be dict or None.

        Cached results should be JSON-serializable dict or not cached (None).
        """
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
        )

        # Completed executions have cache
        execution_completed = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
            execution_time_ms=execution_time_ms,
        )

        assert execution_completed.result_cache is None or isinstance(execution_completed.result_cache, dict)

        # Failed executions don't have cache
        execution_failed = ReportExecutionGenerator.create_failed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        assert execution_failed.result_cache is None

    @given(
        report_type=report_type_strategy(),
    )
    def test_parameters_is_always_dict(self, report_type):
        """
        INVARIANT: parameters must always be a dict.

        Runtime parameters should be dict, never None or other types.
        """
        property_obj = PropertyGenerator.create()
        user_id = property_obj.id
        report = CustomReportGenerator.create_for_type(
            tenant_id=property_obj.tenant_id,
            created_by=user_id,
            report_type=report_type,
        )

        execution = ReportExecutionGenerator.create_completed(
            tenant_id=property_obj.tenant_id,
            custom_report_id=report.id,
            executed_by=user_id,
        )

        assert isinstance(execution.parameters, dict)
