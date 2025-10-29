"""Report data generator for realistic custom report and execution test data."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from faker import Faker

from qa_testing.models import (
    CustomReport,
    ExecutionStatus,
    ReportExecution,
    ReportType,
)

fake = Faker()


class CustomReportGenerator:
    """
    Generator for creating realistic CustomReport test data.

    Usage:
        # Create a general ledger report
        report = CustomReportGenerator.create_general_ledger_report(
            tenant_id=tenant.id,
            created_by=user.id
        )

        # Create any random report
        report = CustomReportGenerator.create(
            tenant_id=tenant.id,
            created_by=user.id
        )

        # Create with specific filters
        report = CustomReportGenerator.create_for_type(
            tenant_id=tenant.id,
            created_by=user.id,
            report_type=ReportType.INCOME_STATEMENT
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        name: Optional[str] = None,
        report_type: Optional[ReportType] = None,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, str]] = None,
        sort_by: Optional[List[Dict[str, str]]] = None,
        is_public: bool = False,
        is_favorite: bool = False,
        created_by: Optional[UUID] = None,
        description: Optional[str] = None,
    ) -> CustomReport:
        """
        Create a custom report with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            name: Report name (generates if not provided)
            report_type: Type of report (random if not provided)
            columns: List of columns (generates based on type if not provided)
            filters: Filter dictionary (generates if not provided)
            sort_by: Sort order list (generates if not provided)
            is_public: Whether report is public
            is_favorite: Whether report is favorite
            created_by: User who created report (generates if not provided)
            description: Report description (generates if not provided)

        Returns:
            CustomReport instance with realistic data
        """
        tenant_id = tenant_id or uuid4()
        created_by = created_by or uuid4()

        # Select random report type if not provided
        if report_type is None:
            report_type = fake.random.choice(list(ReportType))

        # Generate name based on report type
        if name is None:
            name = CustomReportGenerator._generate_name(report_type)

        # Generate columns based on report type
        if columns is None:
            columns = CustomReportGenerator._generate_columns(report_type)

        # Generate filters
        if filters is None:
            filters = CustomReportGenerator._generate_filters(report_type)

        # Generate sort order
        if sort_by is None:
            sort_by = CustomReportGenerator._generate_sort_by(report_type)

        # Generate description
        if description is None:
            description = CustomReportGenerator._generate_description(report_type)

        return CustomReport(
            tenant_id=tenant_id,
            name=name,
            report_type=report_type,
            columns=columns,
            filters=filters,
            sort_by=sort_by,
            is_public=is_public,
            is_favorite=is_favorite,
            created_by=created_by,
            description=description,
        )

    @staticmethod
    def create_for_type(
        *,
        tenant_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        report_type: ReportType,
        is_public: bool = False,
        is_favorite: bool = False,
    ) -> CustomReport:
        """Create a custom report for a specific report type."""
        return CustomReportGenerator.create(
            tenant_id=tenant_id,
            created_by=created_by,
            report_type=report_type,
            is_public=is_public,
            is_favorite=is_favorite,
        )

    @staticmethod
    def create_general_ledger_report(
        *,
        tenant_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        is_public: bool = False,
    ) -> CustomReport:
        """Create a general ledger report."""
        return CustomReportGenerator.create(
            tenant_id=tenant_id,
            created_by=created_by,
            report_type=ReportType.GENERAL_LEDGER,
            name="General Ledger - All Transactions",
            columns=["date", "account_code", "account_name", "debit", "credit", "balance", "description"],
            filters={"date_from": "2025-01-01", "date_to": "2025-12-31"},
            sort_by=[{"field": "date", "direction": "asc"}, {"field": "account_code", "direction": "asc"}],
            is_public=is_public,
        )

    @staticmethod
    def create_trial_balance_report(
        *,
        tenant_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        is_public: bool = False,
    ) -> CustomReport:
        """Create a trial balance report."""
        return CustomReportGenerator.create(
            tenant_id=tenant_id,
            created_by=created_by,
            report_type=ReportType.TRIAL_BALANCE,
            name="Trial Balance - Monthly",
            columns=["account_code", "account_name", "debit_balance", "credit_balance"],
            filters={"as_of_date": "2025-12-31"},
            sort_by=[{"field": "account_code", "direction": "asc"}],
            is_public=is_public,
        )

    @staticmethod
    def create_income_statement_report(
        *,
        tenant_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        is_public: bool = False,
    ) -> CustomReport:
        """Create an income statement report."""
        return CustomReportGenerator.create(
            tenant_id=tenant_id,
            created_by=created_by,
            report_type=ReportType.INCOME_STATEMENT,
            name="Income Statement - Year to Date",
            columns=["account_name", "current_period", "year_to_date", "budget", "variance"],
            filters={"date_from": "2025-01-01", "date_to": "2025-12-31"},
            sort_by=[{"field": "account_name", "direction": "asc"}],
            is_public=is_public,
        )

    @staticmethod
    def create_balance_sheet_report(
        *,
        tenant_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        is_public: bool = False,
    ) -> CustomReport:
        """Create a balance sheet report."""
        return CustomReportGenerator.create(
            tenant_id=tenant_id,
            created_by=created_by,
            report_type=ReportType.BALANCE_SHEET,
            name="Balance Sheet - End of Year",
            columns=["account_category", "account_name", "current_balance", "prior_period"],
            filters={"as_of_date": "2025-12-31"},
            sort_by=[{"field": "account_category", "direction": "asc"}],
            is_public=is_public,
        )

    @staticmethod
    def create_cash_flow_report(
        *,
        tenant_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        is_public: bool = False,
    ) -> CustomReport:
        """Create a cash flow statement report."""
        return CustomReportGenerator.create(
            tenant_id=tenant_id,
            created_by=created_by,
            report_type=ReportType.CASH_FLOW,
            name="Cash Flow Statement - Quarterly",
            columns=["category", "description", "amount", "percentage"],
            filters={"date_from": "2025-01-01", "date_to": "2025-03-31"},
            sort_by=[{"field": "category", "direction": "asc"}],
            is_public=is_public,
        )

    @staticmethod
    def create_ar_aging_report(
        *,
        tenant_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        is_public: bool = False,
    ) -> CustomReport:
        """Create an accounts receivable aging report."""
        return CustomReportGenerator.create(
            tenant_id=tenant_id,
            created_by=created_by,
            report_type=ReportType.AR_AGING,
            name="AR Aging - 90 Days",
            columns=["owner_name", "unit", "current", "30_days", "60_days", "90_days", "total_due"],
            filters={"as_of_date": "2025-12-31", "include_paid": "false"},
            sort_by=[{"field": "total_due", "direction": "desc"}],
            is_public=is_public,
        )

    @staticmethod
    def create_owner_ledger_report(
        *,
        tenant_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        is_public: bool = False,
    ) -> CustomReport:
        """Create an owner ledger report."""
        return CustomReportGenerator.create(
            tenant_id=tenant_id,
            created_by=created_by,
            report_type=ReportType.OWNER_LEDGER,
            name="Owner Ledger - All Units",
            columns=["date", "description", "charges", "payments", "balance"],
            filters={"date_from": "2025-01-01", "date_to": "2025-12-31"},
            sort_by=[{"field": "date", "direction": "asc"}],
            is_public=is_public,
        )

    @staticmethod
    def create_budget_variance_report(
        *,
        tenant_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        is_public: bool = False,
    ) -> CustomReport:
        """Create a budget variance report."""
        return CustomReportGenerator.create(
            tenant_id=tenant_id,
            created_by=created_by,
            report_type=ReportType.BUDGET_VARIANCE,
            name="Budget vs Actual - Monthly",
            columns=["account_name", "budget", "actual", "variance", "variance_percent"],
            filters={"date_from": "2025-01-01", "date_to": "2025-01-31"},
            sort_by=[{"field": "variance_percent", "direction": "desc"}],
            is_public=is_public,
        )

    @staticmethod
    def create_reserve_funding_report(
        *,
        tenant_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        is_public: bool = False,
    ) -> CustomReport:
        """Create a reserve funding report."""
        return CustomReportGenerator.create(
            tenant_id=tenant_id,
            created_by=created_by,
            report_type=ReportType.RESERVE_FUNDING,
            name="Reserve Funding Analysis - 5 Year",
            columns=["year", "beginning_balance", "contributions", "expenditures", "ending_balance", "percent_funded"],
            filters={"projection_years": "5"},
            sort_by=[{"field": "year", "direction": "asc"}],
            is_public=is_public,
        )

    @staticmethod
    def _generate_name(report_type: ReportType) -> str:
        """Generate realistic report name based on type."""
        templates = {
            ReportType.GENERAL_LEDGER: [
                "General Ledger - All Transactions",
                "GL Report - Monthly",
                "Complete General Ledger",
            ],
            ReportType.TRIAL_BALANCE: [
                "Trial Balance - Monthly",
                "TB Report - End of Period",
                "Trial Balance Summary",
            ],
            ReportType.INCOME_STATEMENT: [
                "Income Statement - Year to Date",
                "P&L Report - Monthly",
                "Income & Expenses Summary",
            ],
            ReportType.BALANCE_SHEET: [
                "Balance Sheet - End of Year",
                "Assets & Liabilities Report",
                "Balance Sheet Summary",
            ],
            ReportType.CASH_FLOW: [
                "Cash Flow Statement - Quarterly",
                "Cash Flow Analysis",
                "Statement of Cash Flows",
            ],
            ReportType.AR_AGING: [
                "AR Aging - 90 Days",
                "Accounts Receivable Aging",
                "Outstanding Balances Report",
            ],
            ReportType.OWNER_LEDGER: [
                "Owner Ledger - All Units",
                "Unit Owner Account Statement",
                "Owner Account History",
            ],
            ReportType.BUDGET_VARIANCE: [
                "Budget vs Actual - Monthly",
                "Budget Variance Analysis",
                "Budget Performance Report",
            ],
            ReportType.RESERVE_FUNDING: [
                "Reserve Funding Analysis - 5 Year",
                "Reserve Study Projections",
                "Long-Term Reserve Planning",
            ],
        }
        return fake.random.choice(templates.get(report_type, ["Custom Report"]))

    @staticmethod
    def _generate_columns(report_type: ReportType) -> List[str]:
        """Generate typical columns for report type."""
        column_sets = {
            ReportType.GENERAL_LEDGER: ["date", "account_code", "account_name", "debit", "credit", "balance"],
            ReportType.TRIAL_BALANCE: ["account_code", "account_name", "debit_balance", "credit_balance"],
            ReportType.INCOME_STATEMENT: ["account_name", "current_period", "year_to_date", "budget"],
            ReportType.BALANCE_SHEET: ["account_category", "account_name", "current_balance"],
            ReportType.CASH_FLOW: ["category", "description", "amount"],
            ReportType.AR_AGING: ["owner_name", "unit", "current", "30_days", "60_days", "90_days", "total_due"],
            ReportType.OWNER_LEDGER: ["date", "description", "charges", "payments", "balance"],
            ReportType.BUDGET_VARIANCE: ["account_name", "budget", "actual", "variance"],
            ReportType.RESERVE_FUNDING: ["year", "beginning_balance", "contributions", "ending_balance"],
        }
        return column_sets.get(report_type, ["date", "description", "amount"])

    @staticmethod
    def _generate_filters(report_type: ReportType) -> Dict[str, str]:
        """Generate typical filters for report type."""
        # Most reports filter by date range
        if report_type in [ReportType.GENERAL_LEDGER, ReportType.INCOME_STATEMENT,
                           ReportType.CASH_FLOW, ReportType.OWNER_LEDGER, ReportType.BUDGET_VARIANCE]:
            return {
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
            }
        # Some reports use as_of_date
        elif report_type in [ReportType.TRIAL_BALANCE, ReportType.BALANCE_SHEET, ReportType.AR_AGING]:
            return {
                "as_of_date": "2025-12-31",
            }
        # Reserve reports use projection parameters
        elif report_type == ReportType.RESERVE_FUNDING:
            return {
                "projection_years": "5",
            }
        else:
            return {}

    @staticmethod
    def _generate_sort_by(report_type: ReportType) -> List[Dict[str, str]]:
        """Generate typical sort order for report type."""
        # Most reports sort by date or account
        if report_type in [ReportType.GENERAL_LEDGER, ReportType.OWNER_LEDGER]:
            return [{"field": "date", "direction": "asc"}]
        elif report_type in [ReportType.TRIAL_BALANCE, ReportType.INCOME_STATEMENT, ReportType.BALANCE_SHEET]:
            return [{"field": "account_code", "direction": "asc"}]
        elif report_type == ReportType.AR_AGING:
            return [{"field": "total_due", "direction": "desc"}]
        elif report_type == ReportType.RESERVE_FUNDING:
            return [{"field": "year", "direction": "asc"}]
        else:
            return [{"field": "date", "direction": "desc"}]

    @staticmethod
    def _generate_description(report_type: ReportType) -> str:
        """Generate realistic report description."""
        descriptions = {
            ReportType.GENERAL_LEDGER: "Complete listing of all financial transactions by date and account.",
            ReportType.TRIAL_BALANCE: "Summary of all account balances to verify debits equal credits.",
            ReportType.INCOME_STATEMENT: "Revenue and expense summary showing profit/loss for the period.",
            ReportType.BALANCE_SHEET: "Snapshot of assets, liabilities, and equity at a specific date.",
            ReportType.CASH_FLOW: "Analysis of cash inflows and outflows by category.",
            ReportType.AR_AGING: "Outstanding owner balances grouped by age of debt.",
            ReportType.OWNER_LEDGER: "Detailed transaction history for each owner account.",
            ReportType.BUDGET_VARIANCE: "Comparison of actual results to budgeted amounts.",
            ReportType.RESERVE_FUNDING: "Multi-year projection of reserve fund adequacy.",
        }
        return descriptions.get(report_type, "Custom financial report.")


class ReportExecutionGenerator:
    """
    Generator for creating realistic ReportExecution test data.

    Usage:
        # Create a completed execution
        execution = ReportExecutionGenerator.create_completed(
            custom_report_id=report.id,
            tenant_id=tenant.id,
            executed_by=user.id
        )

        # Create a failed execution
        execution = ReportExecutionGenerator.create_failed(
            custom_report_id=report.id,
            tenant_id=tenant.id,
            executed_by=user.id
        )

        # Create with specific parameters
        execution = ReportExecutionGenerator.create(
            custom_report_id=report.id,
            tenant_id=tenant.id,
            executed_by=user.id,
            status=ExecutionStatus.RUNNING
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        custom_report_id: UUID,
        status: Optional[ExecutionStatus] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        row_count: Optional[int] = None,
        execution_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        result_cache: Optional[Dict] = None,
        parameters: Optional[Dict[str, str]] = None,
        executed_by: Optional[UUID] = None,
    ) -> ReportExecution:
        """
        Create a report execution with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            custom_report_id: Report being executed (required)
            status: Execution status (defaults to COMPLETED)
            started_at: Start timestamp (defaults to now)
            completed_at: Completion timestamp (calculates based on execution_time_ms)
            row_count: Number of rows (generates if not provided)
            execution_time_ms: Execution time in ms (generates if not provided)
            error_message: Error message (empty if not provided)
            result_cache: Cached results (generates if status is COMPLETED)
            parameters: Runtime parameters (generates if not provided)
            executed_by: User who executed (generates if not provided)

        Returns:
            ReportExecution instance with realistic data
        """
        tenant_id = tenant_id or uuid4()
        executed_by = executed_by or uuid4()

        # Default status
        if status is None:
            status = ExecutionStatus.COMPLETED

        # Default started_at
        if started_at is None:
            started_at = datetime.now()

        # Generate execution time (50ms to 5000ms)
        if execution_time_ms is None:
            execution_time_ms = fake.random.randint(50, 5000)

        # Calculate completed_at based on execution time
        if completed_at is None and status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]:
            completed_at = started_at + timedelta(milliseconds=execution_time_ms)

        # Generate row count (0 to 10000 rows)
        if row_count is None:
            if status == ExecutionStatus.COMPLETED:
                row_count = fake.random.randint(0, 10000)
            else:
                row_count = 0

        # Generate error message for failed executions
        if error_message is None:
            if status == ExecutionStatus.FAILED:
                error_message = ReportExecutionGenerator._generate_error_message()
            else:
                error_message = ""

        # Generate result cache for completed executions
        if result_cache is None and status == ExecutionStatus.COMPLETED:
            result_cache = ReportExecutionGenerator._generate_result_cache(row_count)

        # Generate runtime parameters
        if parameters is None:
            parameters = {
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
            }

        return ReportExecution(
            tenant_id=tenant_id,
            custom_report_id=custom_report_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
            error_message=error_message,
            result_cache=result_cache,
            parameters=parameters,
            executed_by=executed_by,
        )

    @staticmethod
    def create_completed(
        *,
        tenant_id: Optional[UUID] = None,
        custom_report_id: UUID,
        executed_by: Optional[UUID] = None,
        row_count: Optional[int] = None,
        execution_time_ms: Optional[int] = None,
    ) -> ReportExecution:
        """Create a completed report execution with cached results."""
        return ReportExecutionGenerator.create(
            tenant_id=tenant_id,
            custom_report_id=custom_report_id,
            executed_by=executed_by,
            status=ExecutionStatus.COMPLETED,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
        )

    @staticmethod
    def create_failed(
        *,
        tenant_id: Optional[UUID] = None,
        custom_report_id: UUID,
        executed_by: Optional[UUID] = None,
        error_message: Optional[str] = None,
    ) -> ReportExecution:
        """Create a failed report execution with error message."""
        return ReportExecutionGenerator.create(
            tenant_id=tenant_id,
            custom_report_id=custom_report_id,
            executed_by=executed_by,
            status=ExecutionStatus.FAILED,
            error_message=error_message,
            row_count=0,
            execution_time_ms=fake.random.randint(50, 500),
        )

    @staticmethod
    def create_pending(
        *,
        tenant_id: Optional[UUID] = None,
        custom_report_id: UUID,
        executed_by: Optional[UUID] = None,
    ) -> ReportExecution:
        """Create a pending report execution (not yet started)."""
        return ReportExecution(
            tenant_id=tenant_id or uuid4(),
            custom_report_id=custom_report_id,
            status=ExecutionStatus.PENDING,
            started_at=datetime.now(),
            completed_at=None,
            row_count=0,
            execution_time_ms=0,
            error_message="",
            result_cache=None,
            parameters={},
            executed_by=executed_by or uuid4(),
        )

    @staticmethod
    def _generate_error_message() -> str:
        """Generate realistic error message."""
        errors = [
            "Query timeout after 30 seconds",
            "Database connection failed",
            "Invalid date range: start date must be before end date",
            "Account not found: invalid account_id in filters",
            "Permission denied: user cannot access this fund",
            "Report generation failed: insufficient data for period",
        ]
        return fake.random.choice(errors)

    @staticmethod
    def _generate_result_cache(row_count: int) -> Dict:
        """Generate realistic cached result data."""
        return {
            "rows": row_count,
            "columns": ["date", "account", "amount", "description"],
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_debits": str(Decimal(str(fake.random.randint(10000, 500000))) + Decimal("0.00")),
                "total_credits": str(Decimal(str(fake.random.randint(10000, 500000))) + Decimal("0.00")),
            },
        }
