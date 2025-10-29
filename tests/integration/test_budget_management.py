"""
Integration tests for budget management functionality.

Tests the complete budget lifecycle including:
- Budget creation and validation
- Budget line management
- Budget approval workflow
- Variance calculation and reporting
- Multi-year budget tracking
"""

from datetime import date
from decimal import Decimal

import pytest

from qa_testing.generators import BudgetGenerator, FundGenerator, PropertyGenerator
from qa_testing.models import Budget, BudgetLine, BudgetStatus, VarianceReport


class TestBudgetCreation:
    """Tests for budget creation and validation."""

    def test_create_budget_with_valid_data(self):
        """Test creating a budget with valid fiscal year and dates."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fiscal_year=2025,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        assert budget.fiscal_year == 2025
        assert budget.start_date == date(2025, 1, 1)
        assert budget.end_date == date(2025, 12, 31)
        assert budget.status == BudgetStatus.DRAFT

    def test_budget_requires_end_date_after_start_date(self):
        """Test that budget end_date must be after start_date."""
        property_obj = PropertyGenerator.create()

        with pytest.raises(ValueError, match="end_date must be after start_date"):
            BudgetGenerator.create(
                tenant_id=property_obj.tenant_id,
                fiscal_year=2025,
                start_date=date(2025, 12, 31),
                end_date=date(2025, 1, 1),  # Invalid: before start_date
            )

    def test_budget_fiscal_year_validation(self):
        """Test that fiscal year must be reasonable."""
        property_obj = PropertyGenerator.create()

        with pytest.raises(ValueError, match="fiscal_year must be between"):
            BudgetGenerator.create(
                tenant_id=property_obj.tenant_id,
                fiscal_year=1999,  # Too old
            )

        with pytest.raises(ValueError, match="fiscal_year must be between"):
            BudgetGenerator.create(
                tenant_id=property_obj.tenant_id,
                fiscal_year=2050,  # Too far in future
            )

    def test_create_budget_for_specific_fund(self):
        """Test creating a budget for a specific fund."""
        property_obj = PropertyGenerator.create()
        fund = FundGenerator.create(property_id=property_obj.id)

        budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fund_id=fund.id,
            fiscal_year=2025,
        )

        assert budget.fund_id == fund.id
        assert "Fund Budget" in budget.name


class TestBudgetLines:
    """Tests for budget line items."""

    def test_create_budget_line(self):
        """Test creating a budget line item."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fiscal_year=2025,
        )

        line = BudgetGenerator.create_budget_line(
            tenant_id=property_obj.tenant_id,
            budget_id=budget.id,
            account_number="5000",
            account_name="Management Fees",
            budgeted_amount=Decimal("12000.00"),
        )

        assert line.budget_id == budget.id
        assert line.account_number == "5000"
        assert line.account_name == "Management Fees"
        assert line.budgeted_amount == Decimal("12000.00")

    def test_budget_line_amount_must_be_non_negative(self):
        """Test that budget line amounts cannot be negative."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)

        with pytest.raises(ValueError, match="budgeted_amount cannot be negative"):
            BudgetGenerator.create_budget_line(
                tenant_id=property_obj.tenant_id,
                budget_id=budget.id,
                budgeted_amount=Decimal("-1000.00"),  # Invalid
            )

    def test_create_budget_with_multiple_lines(self):
        """Test creating a budget with multiple line items."""
        property_obj = PropertyGenerator.create()

        budget, lines = BudgetGenerator.create_with_lines(
            tenant_id=property_obj.tenant_id,
            fiscal_year=2025,
            num_lines=10,
        )

        assert len(lines) == 10
        assert all(line.budget_id == budget.id for line in lines)
        assert all(line.budgeted_amount > Decimal("0.00") for line in lines)

    def test_calculate_total_budgeted_amount(self):
        """Test calculating total budgeted amount across all lines."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)

        lines = [
            BudgetGenerator.create_budget_line(
                tenant_id=property_obj.tenant_id,
                budget_id=budget.id,
                budgeted_amount=Decimal("1000.00"),
            ),
            BudgetGenerator.create_budget_line(
                tenant_id=property_obj.tenant_id,
                budget_id=budget.id,
                budgeted_amount=Decimal("2500.00"),
            ),
            BudgetGenerator.create_budget_line(
                tenant_id=property_obj.tenant_id,
                budget_id=budget.id,
                budgeted_amount=Decimal("3750.00"),
            ),
        ]

        total = budget.get_total_budgeted(lines)
        assert total == Decimal("7250.00")


class TestBudgetApprovalWorkflow:
    """Tests for budget approval workflow."""

    def test_draft_budget_has_no_approval_data(self):
        """Test that draft budgets have no approval data."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            status=BudgetStatus.DRAFT,
        )

        assert budget.status == BudgetStatus.DRAFT
        assert budget.approved_by is None
        assert budget.approved_at is None

    def test_approved_budget_has_approval_data(self):
        """Test that approved budgets have required approval data."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            status=BudgetStatus.APPROVED,
        )

        assert budget.status == BudgetStatus.APPROVED
        assert budget.approved_by is not None
        assert budget.approved_at is not None

    def test_active_budget_has_approval_data(self):
        """Test that active budgets have approval data."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fiscal_year=date.today().year,
            status=BudgetStatus.ACTIVE,
        )

        assert budget.status == BudgetStatus.ACTIVE
        assert budget.approved_by is not None
        assert budget.approved_at is not None

    def test_is_active_check(self):
        """Test budget is_active() method."""
        property_obj = PropertyGenerator.create()

        # Active budget for current year
        active_budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fiscal_year=date.today().year,
            start_date=date(date.today().year, 1, 1),
            end_date=date(date.today().year, 12, 31),
            status=BudgetStatus.ACTIVE,
        )
        assert active_budget.is_active() is True

        # Draft budget should not be active
        draft_budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fiscal_year=date.today().year,
            status=BudgetStatus.DRAFT,
        )
        assert draft_budget.is_active() is False

        # Past year budget should not be active
        past_budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fiscal_year=2020,
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            status=BudgetStatus.CLOSED,
        )
        assert past_budget.is_active() is False


class TestVarianceReporting:
    """Tests for budget variance reporting."""

    def test_create_variance_report(self):
        """Test creating a variance report."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fiscal_year=2025,
        )

        report = BudgetGenerator.create_variance_report(
            tenant_id=property_obj.tenant_id,
            budget_id=budget.id,
            budget_name=budget.name,
            fiscal_year=budget.fiscal_year,
            period_start=budget.start_date,
            period_end=budget.end_date,
            total_budgeted=Decimal("100000.00"),
            total_actual=Decimal("95000.00"),
        )

        assert report.budget_id == budget.id
        assert report.total_budgeted == Decimal("100000.00")
        assert report.total_actual == Decimal("95000.00")
        assert report.total_variance == Decimal("5000.00")
        assert report.variance_percentage == Decimal("5.00")

    def test_favorable_variance(self):
        """Test identifying favorable variance (under budget)."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)

        report = BudgetGenerator.create_variance_report(
            tenant_id=property_obj.tenant_id,
            budget_id=budget.id,
            budget_name=budget.name,
            fiscal_year=budget.fiscal_year,
            period_start=budget.start_date,
            period_end=budget.end_date,
            total_budgeted=Decimal("100000.00"),
            total_actual=Decimal("90000.00"),  # Under budget
        )

        assert report.is_favorable() is True
        assert report.is_unfavorable() is False
        assert report.total_variance > Decimal("0.00")

    def test_unfavorable_variance(self):
        """Test identifying unfavorable variance (over budget)."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)

        report = BudgetGenerator.create_variance_report(
            tenant_id=property_obj.tenant_id,
            budget_id=budget.id,
            budget_name=budget.name,
            fiscal_year=budget.fiscal_year,
            period_start=budget.start_date,
            period_end=budget.end_date,
            total_budgeted=Decimal("100000.00"),
            total_actual=Decimal("110000.00"),  # Over budget
        )

        assert report.is_favorable() is False
        assert report.is_unfavorable() is True
        assert report.total_variance < Decimal("0.00")

    def test_on_track_variance(self):
        """Test identifying on-track variance (within ±5%)."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)

        report = BudgetGenerator.create_variance_report(
            tenant_id=property_obj.tenant_id,
            budget_id=budget.id,
            budget_name=budget.name,
            fiscal_year=budget.fiscal_year,
            period_start=budget.start_date,
            period_end=budget.end_date,
            total_budgeted=Decimal("100000.00"),
            total_actual=Decimal("98000.00"),  # 2% under
        )

        assert report.is_on_track() is True
        assert abs(report.variance_percentage) <= Decimal("5.00")

    def test_line_variance_status(self):
        """Test budget line variance status calculation."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)
        line = BudgetGenerator.create_budget_line(
            tenant_id=property_obj.tenant_id,
            budget_id=budget.id,
            budgeted_amount=Decimal("10000.00"),
        )

        # Favorable (under budget)
        favorable = BudgetGenerator.create_line_variance(
            tenant_id=property_obj.tenant_id,
            budget_line_id=line.id,
            account_number=line.account_number,
            account_name=line.account_name,
            budgeted=Decimal("10000.00"),
            actual=Decimal("8000.00"),
        )
        assert favorable.status == "favorable"
        assert favorable.variance > Decimal("0.00")

        # Unfavorable (over budget)
        unfavorable = BudgetGenerator.create_line_variance(
            tenant_id=property_obj.tenant_id,
            budget_line_id=line.id,
            account_number=line.account_number,
            account_name=line.account_name,
            budgeted=Decimal("10000.00"),
            actual=Decimal("12000.00"),
        )
        assert unfavorable.status == "unfavorable"
        assert unfavorable.variance < Decimal("0.00")

        # On track (within 5%)
        on_track = BudgetGenerator.create_line_variance(
            tenant_id=property_obj.tenant_id,
            budget_line_id=line.id,
            account_number=line.account_number,
            account_name=line.account_name,
            budgeted=Decimal("10000.00"),
            actual=Decimal("9900.00"),
        )
        assert on_track.status == "on_track"


class TestMultiYearBudgets:
    """Tests for multi-year budget tracking."""

    def test_create_budgets_for_multiple_years(self):
        """Test creating and tracking budgets across multiple fiscal years."""
        property_obj = PropertyGenerator.create()

        budgets = []
        for year in [2023, 2024, 2025]:
            budget = BudgetGenerator.create(
                tenant_id=property_obj.tenant_id,
                fiscal_year=year,
                start_date=date(year, 1, 1),
                end_date=date(year, 12, 31),
            )
            budgets.append(budget)

        assert len(budgets) == 3
        assert [b.fiscal_year for b in budgets] == [2023, 2024, 2025]

    def test_budget_year_over_year_comparison(self):
        """Test comparing budgets across fiscal years."""
        property_obj = PropertyGenerator.create()

        # Create 2024 budget
        budget_2024 = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fiscal_year=2024,
        )
        _, lines_2024 = BudgetGenerator.create_with_lines(
            tenant_id=property_obj.tenant_id,
            fiscal_year=2024,
            num_lines=5,
        )
        total_2024 = budget_2024.get_total_budgeted(lines_2024)

        # Create 2025 budget with 10% increase
        budget_2025 = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fiscal_year=2025,
        )
        lines_2025 = []
        for line in lines_2024:
            # Increase by 10% and quantize to 2 decimal places
            increased_amount = (line.budgeted_amount * Decimal("1.10")).quantize(Decimal("0.01"))
            new_line = BudgetGenerator.create_budget_line(
                tenant_id=property_obj.tenant_id,
                budget_id=budget_2025.id,
                account_number=line.account_number,
                account_name=line.account_name,
                budgeted_amount=increased_amount,
            )
            lines_2025.append(new_line)

        total_2025 = budget_2025.get_total_budgeted(lines_2025)

        # Verify 10% increase
        expected_increase = total_2024 * Decimal("0.10")
        actual_increase = total_2025 - total_2024
        assert abs(actual_increase - expected_increase) < Decimal("0.01")


class TestBudgetDataTypes:
    """Tests for proper data type usage in budgets."""

    def test_budget_amounts_use_decimal(self):
        """Test that all budget amounts use Decimal, not float."""
        property_obj = PropertyGenerator.create()
        budget, lines = BudgetGenerator.create_with_lines(
            tenant_id=property_obj.tenant_id,
            num_lines=5,
        )

        for line in lines:
            assert isinstance(line.budgeted_amount, Decimal)
            # Verify exactly 2 decimal places
            assert line.budgeted_amount.as_tuple().exponent == -2

    def test_budget_dates_use_date_type(self):
        """Test that budget dates use date, not datetime."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)

        assert isinstance(budget.start_date, date)
        assert isinstance(budget.end_date, date)
        if budget.approved_at:
            assert isinstance(budget.approved_at, date)

    def test_variance_calculations_preserve_precision(self):
        """Test that variance calculations maintain decimal precision."""
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)

        report = BudgetGenerator.create_variance_report(
            tenant_id=property_obj.tenant_id,
            budget_id=budget.id,
            budget_name=budget.name,
            fiscal_year=budget.fiscal_year,
            period_start=budget.start_date,
            period_end=budget.end_date,
            total_budgeted=Decimal("100000.33"),
            total_actual=Decimal("95123.67"),
        )

        # Verify all amounts are Decimal with exact precision
        assert isinstance(report.total_budgeted, Decimal)
        assert isinstance(report.total_actual, Decimal)
        assert isinstance(report.total_variance, Decimal)
        assert isinstance(report.variance_percentage, Decimal)

        # Verify calculated variance is exact
        expected_variance = Decimal("100000.33") - Decimal("95123.67")
        assert report.total_variance == expected_variance
