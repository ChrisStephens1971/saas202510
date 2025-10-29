"""Budget data generator for realistic HOA budget test data."""

from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from faker import Faker

from qa_testing.models import Budget, BudgetLine, BudgetStatus, VarianceReport, BudgetLineVariance

fake = Faker()


class BudgetGenerator:
    """
    Generator for creating realistic Budget test data.

    Usage:
        # Create a single budget
        budget = BudgetGenerator.create(tenant_id=tenant.id, fund_id=fund.id)

        # Create budget with lines
        budget = BudgetGenerator.create_with_lines(
            tenant_id=tenant.id,
            fund_id=fund.id,
            num_lines=10
        )

        # Create variance report
        report = BudgetGenerator.create_variance_report(budget_id=budget.id)
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        fund_id: Optional[UUID] = None,
        fiscal_year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[BudgetStatus] = None,
        name: Optional[str] = None,
        notes: Optional[str] = None,
        approved_by: Optional[UUID] = None,
        approved_at: Optional[date] = None,
        created_by: Optional[UUID] = None,
    ) -> Budget:
        """
        Create a single Budget with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            fund_id: Fund ID (optional - null means all funds)
            fiscal_year: Fiscal year (defaults to current year)
            start_date: Budget period start (defaults to Jan 1 of fiscal year)
            end_date: Budget period end (defaults to Dec 31 of fiscal year)
            status: Budget status (defaults to DRAFT)
            name: Budget name (generates if not provided)
            notes: Budget notes (generates if not provided)
            approved_by: User ID who approved (None if not approved)
            approved_at: Approval date (None if not approved)
            created_by: User ID who created (generates if not provided)

        Returns:
            Budget instance with realistic data
        """
        tenant_id = tenant_id or uuid4()
        created_by = created_by or uuid4()

        # Default to current fiscal year
        if fiscal_year is None:
            fiscal_year = date.today().year

        # Default dates
        if start_date is None:
            start_date = date(fiscal_year, 1, 1)
        if end_date is None:
            end_date = date(fiscal_year, 12, 31)

        # Default status
        if status is None:
            status = BudgetStatus.DRAFT

        # Generate name
        if name is None:
            name = f"FY {fiscal_year} Operating Budget"
            if fund_id:
                name = f"FY {fiscal_year} Fund Budget"

        # Generate notes
        if notes is None:
            notes = BudgetGenerator._generate_notes(fiscal_year)

        # Set approval data if status is approved or active
        if status in [BudgetStatus.APPROVED, BudgetStatus.ACTIVE, BudgetStatus.CLOSED]:
            if approved_by is None:
                approved_by = uuid4()
            if approved_at is None:
                # Approved a few days before start
                approved_at = date(start_date.year - 1, 12, 20)

        return Budget(
            tenant_id=tenant_id,
            name=name,
            fiscal_year=fiscal_year,
            start_date=start_date,
            end_date=end_date,
            fund_id=fund_id,
            status=status,
            approved_by=approved_by,
            approved_at=approved_at,
            notes=notes,
            created_by=created_by,
        )

    @staticmethod
    def create_budget_line(
        *,
        tenant_id: Optional[UUID] = None,
        budget_id: UUID,
        account_id: Optional[UUID] = None,
        account_number: Optional[str] = None,
        account_name: Optional[str] = None,
        budgeted_amount: Optional[Decimal] = None,
        notes: Optional[str] = None,
    ) -> BudgetLine:
        """
        Create a budget line item.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            budget_id: Budget this line belongs to (required)
            account_id: Account ID (generates if not provided)
            account_number: Account number (generates if not provided)
            account_name: Account name (generates if not provided)
            budgeted_amount: Budgeted amount (generates if not provided)
            notes: Line notes (generates if not provided)

        Returns:
            BudgetLine instance
        """
        tenant_id = tenant_id or uuid4()
        account_id = account_id or uuid4()

        # Generate account details if not provided
        if account_number is None or account_name is None:
            acc_num, acc_name = BudgetGenerator._generate_account_details()
            account_number = account_number or acc_num
            account_name = account_name or acc_name

        # Generate realistic budgeted amount (between $1,000 and $50,000)
        if budgeted_amount is None:
            dollars = fake.random.randint(1000, 50000)
            cents = fake.random.randint(0, 99)
            budgeted_amount = Decimal(f"{dollars}.{cents:02d}")

        # Generate notes
        if notes is None:
            notes = fake.sentence(nb_words=10)

        return BudgetLine(
            tenant_id=tenant_id,
            budget_id=budget_id,
            account_id=account_id,
            account_number=account_number,
            account_name=account_name,
            budgeted_amount=budgeted_amount,
            notes=notes,
        )

    @staticmethod
    def create_with_lines(
        *,
        tenant_id: Optional[UUID] = None,
        fund_id: Optional[UUID] = None,
        fiscal_year: Optional[int] = None,
        num_lines: int = 10,
        status: Optional[BudgetStatus] = None,
    ) -> tuple[Budget, List[BudgetLine]]:
        """
        Create a budget with multiple budget lines.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            fund_id: Fund ID (optional)
            fiscal_year: Fiscal year (defaults to current year)
            num_lines: Number of budget lines to create
            status: Budget status

        Returns:
            Tuple of (Budget, List[BudgetLine])
        """
        tenant_id = tenant_id or uuid4()

        # Create budget
        budget = BudgetGenerator.create(
            tenant_id=tenant_id,
            fund_id=fund_id,
            fiscal_year=fiscal_year,
            status=status,
        )

        # Create budget lines
        lines = []
        for _ in range(num_lines):
            line = BudgetGenerator.create_budget_line(
                tenant_id=tenant_id,
                budget_id=budget.id,
            )
            lines.append(line)

        return budget, lines

    @staticmethod
    def create_variance_report(
        *,
        tenant_id: Optional[UUID] = None,
        budget_id: UUID,
        budget_name: str,
        fiscal_year: int,
        period_start: date,
        period_end: date,
        as_of_date: Optional[date] = None,
        total_budgeted: Optional[Decimal] = None,
        total_actual: Optional[Decimal] = None,
    ) -> VarianceReport:
        """
        Create a variance report.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            budget_id: Budget ID (required)
            budget_name: Budget name (required)
            fiscal_year: Fiscal year (required)
            period_start: Period start date (required)
            period_end: Period end date (required)
            as_of_date: Date actuals calculated through (defaults to today)
            total_budgeted: Total budgeted amount (generates if not provided)
            total_actual: Total actual amount (generates if not provided)

        Returns:
            VarianceReport instance
        """
        tenant_id = tenant_id or uuid4()
        as_of_date = as_of_date or date.today()

        # Generate realistic totals
        if total_budgeted is None:
            total_budgeted = Decimal(str(fake.random.randint(100000, 500000)))

        if total_actual is None:
            # Actual is typically 70-110% of budget
            variance_factor = Decimal(str(fake.random.uniform(0.7, 1.1)))
            total_actual = (total_budgeted * variance_factor).quantize(Decimal("0.01"))

        total_variance = total_budgeted - total_actual
        variance_percentage = (
            (total_variance / total_budgeted * Decimal("100"))
            if total_budgeted != 0
            else Decimal("0.00")
        ).quantize(Decimal("0.01"))

        return VarianceReport(
            tenant_id=tenant_id,
            budget_id=budget_id,
            budget_name=budget_name,
            fiscal_year=fiscal_year,
            period_start=period_start,
            period_end=period_end,
            as_of_date=as_of_date,
            total_budgeted=total_budgeted,
            total_actual=total_actual,
            total_variance=total_variance,
            variance_percentage=variance_percentage,
        )

    @staticmethod
    def create_line_variance(
        *,
        tenant_id: Optional[UUID] = None,
        budget_line_id: UUID,
        account_number: str,
        account_name: str,
        budgeted: Decimal,
        actual: Optional[Decimal] = None,
    ) -> BudgetLineVariance:
        """
        Create a budget line variance.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            budget_line_id: Budget line ID (required)
            account_number: Account number (required)
            account_name: Account name (required)
            budgeted: Budgeted amount (required)
            actual: Actual amount (generates if not provided)

        Returns:
            BudgetLineVariance instance
        """
        tenant_id = tenant_id or uuid4()

        # Generate actual amount if not provided
        if actual is None:
            variance_factor = Decimal(str(fake.random.uniform(0.7, 1.1)))
            actual = (budgeted * variance_factor).quantize(Decimal("0.01"))

        variance = budgeted - actual
        variance_percentage = (
            (variance / budgeted * Decimal("100"))
            if budgeted != 0
            else Decimal("0.00")
        ).quantize(Decimal("0.01"))

        # Determine status
        if abs(variance_percentage) <= Decimal("5.00"):
            status = "on_track"
        elif variance > Decimal("0.00"):
            status = "favorable"
        else:
            status = "unfavorable"

        return BudgetLineVariance(
            tenant_id=tenant_id,
            budget_line_id=budget_line_id,
            account_number=account_number,
            account_name=account_name,
            budgeted=budgeted,
            actual=actual,
            variance=variance,
            variance_percentage=variance_percentage,
            status=status,
        )

    @staticmethod
    def _generate_notes(fiscal_year: int) -> str:
        """Generate realistic budget notes."""
        templates = [
            f"FY {fiscal_year} budget approved by board on 12/20/{fiscal_year - 1}. "
            "Based on prior year actual expenses with 3% inflation adjustment.",

            f"FY {fiscal_year} operating budget assumes no special assessments. "
            "Reserve fund contributions maintained at 10% of operating revenue.",

            f"FY {fiscal_year} budget includes increased insurance and utility costs. "
            "Landscaping contract renewed at same rate.",
        ]
        return fake.random.choice(templates)

    @staticmethod
    def _generate_account_details() -> tuple[str, str]:
        """Generate realistic account number and name."""
        accounts = [
            ("5000", "Management Fees"),
            ("5100", "Insurance - Property"),
            ("5200", "Landscaping Services"),
            ("5300", "Utilities - Common Areas"),
            ("5400", "Repairs and Maintenance"),
            ("5500", "Pool Maintenance"),
            ("5600", "Legal Fees"),
            ("5700", "Accounting Fees"),
            ("5800", "Administrative Expenses"),
            ("4000", "Assessment Income"),
            ("4100", "Late Fees"),
            ("4200", "Interest Income"),
        ]
        return fake.random.choice(accounts)
