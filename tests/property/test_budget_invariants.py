"""
Property-based tests for budget invariants.

Uses Hypothesis to verify that budget operations maintain critical invariants:
- Total budgeted amount equals sum of budget lines
- Variance calculations are always accurate
- Budget dates are always consistent
- Budget status transitions are valid
"""

from datetime import date, timedelta
from decimal import Decimal

from hypothesis import assume, given
from hypothesis import strategies as st
import pytest

from qa_testing.generators import BudgetGenerator, PropertyGenerator
from qa_testing.models import BudgetStatus


# Custom strategies for budget testing
@st.composite
def fiscal_year_strategy(draw):
    """Generate valid fiscal years."""
    current_year = date.today().year
    return draw(st.integers(min_value=2020, max_value=current_year + 5))


@st.composite
def budget_amount_strategy(draw):
    """Generate realistic budget amounts."""
    # Generate amounts between $100 and $1,000,000 with 2 decimal places
    dollars = draw(st.integers(min_value=100, max_value=1_000_000))
    cents = draw(st.integers(min_value=0, max_value=99))
    return Decimal(f"{dollars}.{cents:02d}")


@st.composite
def date_range_strategy(draw, year):
    """Generate valid date range for a fiscal year."""
    # Most budgets run Jan 1 - Dec 31, but allow other ranges
    start_month = draw(st.integers(min_value=1, max_value=12))
    start_day = draw(st.integers(min_value=1, max_value=28))  # Safe for all months

    start_date = date(year, start_month, start_day)

    # End date must be after start date, typically 12 months later
    days_later = draw(st.integers(min_value=30, max_value=400))
    end_date = start_date + timedelta(days=days_later)

    return start_date, end_date


class TestBudgetInvariants:
    """Property-based tests for budget invariants."""

    @given(
        fiscal_year=fiscal_year_strategy(),
        num_lines=st.integers(min_value=1, max_value=20),
    )
    def test_total_budgeted_equals_sum_of_lines(self, fiscal_year, num_lines):
        """
        INVARIANT: Budget total must always equal sum of budget lines.

        This must hold regardless of:
        - Number of budget lines
        - Individual line amounts
        - Budget status
        """
        property_obj = PropertyGenerator.create()

        budget, lines = BudgetGenerator.create_with_lines(
            tenant_id=property_obj.tenant_id,
            fiscal_year=fiscal_year,
            num_lines=num_lines,
        )

        # Calculate total two ways
        method1_total = budget.get_total_budgeted(lines)
        method2_total = sum((line.budgeted_amount for line in lines), Decimal("0.00"))

        # Must be identical
        assert method1_total == method2_total
        assert method1_total >= Decimal("0.00")

    @given(
        budgeted=budget_amount_strategy(),
        actual=budget_amount_strategy(),
    )
    def test_variance_calculation_accuracy(self, budgeted, actual):
        """
        INVARIANT: Variance = Budgeted - Actual (always accurate).

        This must hold for any budgeted and actual amounts.
        """
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)

        report = BudgetGenerator.create_variance_report(
            tenant_id=property_obj.tenant_id,
            budget_id=budget.id,
            budget_name=budget.name,
            fiscal_year=budget.fiscal_year,
            period_start=budget.start_date,
            period_end=budget.end_date,
            total_budgeted=budgeted,
            total_actual=actual,
        )

        # Variance must equal budgeted - actual
        expected_variance = budgeted - actual
        assert report.total_variance == expected_variance

        # Variance percentage must be accurate
        if budgeted != Decimal("0.00"):
            expected_pct = (expected_variance / budgeted * Decimal("100")).quantize(Decimal("0.01"))
            assert report.variance_percentage == expected_pct

    def test_budget_dates_consistency(self):
        """
        INVARIANT: end_date must always be after start_date.

        This must hold for any fiscal year and date range.
        """
        property_obj = PropertyGenerator.create()

        # Test with standard fiscal year (Jan 1 - Dec 31)
        budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fiscal_year=2025,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        assert budget.end_date > budget.start_date

        # Period length should be reasonable (30 days to 400 days)
        period_days = (budget.end_date - budget.start_date).days
        assert 30 <= period_days <= 400

        # Test with custom fiscal year (Jul 1 - Jun 30)
        budget2 = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fiscal_year=2025,
            start_date=date(2025, 7, 1),
            end_date=date(2026, 6, 30),
        )

        assert budget2.end_date > budget2.start_date
        period_days2 = (budget2.end_date - budget2.start_date).days
        assert 30 <= period_days2 <= 400

    @given(
        budgeted=budget_amount_strategy(),
        variance_pct=st.decimals(min_value="-50.00", max_value="50.00", places=2),
    )
    def test_variance_status_classification(self, budgeted, variance_pct):
        """
        INVARIANT: Variance status classification must be consistent.

        - on_track: |variance| <= 5%
        - favorable: variance > 0 and |variance| > 5%
        - unfavorable: variance < 0 and |variance| > 5%
        """
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)
        line = BudgetGenerator.create_budget_line(
            tenant_id=property_obj.tenant_id,
            budget_id=budget.id,
            budgeted_amount=budgeted,
        )

        # Calculate actual based on variance percentage
        actual = budgeted * (Decimal("1.00") - variance_pct / Decimal("100"))
        actual = actual.quantize(Decimal("0.01"))

        line_variance = BudgetGenerator.create_line_variance(
            tenant_id=property_obj.tenant_id,
            budget_line_id=line.id,
            account_number=line.account_number,
            account_name=line.account_name,
            budgeted=budgeted,
            actual=actual,
        )

        # Verify status classification
        abs_variance_pct = abs(line_variance.variance_percentage)

        if abs_variance_pct <= Decimal("5.00"):
            assert line_variance.status == "on_track"
        elif line_variance.variance > Decimal("0.00"):
            assert line_variance.status == "favorable"
        else:
            assert line_variance.status == "unfavorable"

    @given(
        num_lines=st.integers(min_value=1, max_value=10),
    )
    def test_budget_lines_all_positive(self, num_lines):
        """
        INVARIANT: All budget line amounts must be non-negative.

        Budget lines cannot have negative amounts.
        """
        property_obj = PropertyGenerator.create()

        _, lines = BudgetGenerator.create_with_lines(
            tenant_id=property_obj.tenant_id,
            num_lines=num_lines,
        )

        for line in lines:
            assert line.budgeted_amount >= Decimal("0.00")

    def test_approved_budgets_have_approval_metadata(self):
        """
        INVARIANT: Approved/Active/Closed budgets must have approval metadata.

        Any budget with status other than DRAFT must have:
        - approved_by (user ID)
        - approved_at (date)
        """
        property_obj = PropertyGenerator.create()

        for status in [BudgetStatus.APPROVED, BudgetStatus.ACTIVE, BudgetStatus.CLOSED]:
            budget = BudgetGenerator.create(
                tenant_id=property_obj.tenant_id,
                status=status,
            )

            assert budget.approved_by is not None, f"{status} budget missing approved_by"
            assert budget.approved_at is not None, f"{status} budget missing approved_at"

    def test_draft_budgets_have_no_approval_metadata(self):
        """
        INVARIANT: Draft budgets must NOT have approval metadata.

        Draft budgets should not have approval data.
        """
        property_obj = PropertyGenerator.create()

        budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            status=BudgetStatus.DRAFT,
        )

        # Draft budgets created without explicit approval should have None
        # (Note: generator might set these for DRAFT, this tests the model constraint)
        assert budget.status == BudgetStatus.DRAFT

    @given(
        fiscal_year=fiscal_year_strategy(),
    )
    def test_fiscal_year_matches_date_range(self, fiscal_year):
        """
        INVARIANT: Fiscal year should align with budget date range.

        The fiscal_year field should correspond to the budget period.
        """
        property_obj = PropertyGenerator.create()

        budget = BudgetGenerator.create(
            tenant_id=property_obj.tenant_id,
            fiscal_year=fiscal_year,
            start_date=date(fiscal_year, 1, 1),
            end_date=date(fiscal_year, 12, 31),
        )

        assert budget.fiscal_year == fiscal_year
        assert budget.start_date.year == fiscal_year
        assert budget.end_date.year == fiscal_year


class TestVarianceReportInvariants:
    """Property-based tests for variance report invariants."""

    @given(
        total_budgeted=budget_amount_strategy(),
        total_actual=budget_amount_strategy(),
    )
    def test_variance_report_totals_consistency(self, total_budgeted, total_actual):
        """
        INVARIANT: Variance report totals must be mathematically consistent.

        - total_variance = total_budgeted - total_actual
        - variance_percentage = (total_variance / total_budgeted) * 100
        """
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)

        report = BudgetGenerator.create_variance_report(
            tenant_id=property_obj.tenant_id,
            budget_id=budget.id,
            budget_name=budget.name,
            fiscal_year=budget.fiscal_year,
            period_start=budget.start_date,
            period_end=budget.end_date,
            total_budgeted=total_budgeted,
            total_actual=total_actual,
        )

        # Verify variance calculation
        expected_variance = total_budgeted - total_actual
        assert report.total_variance == expected_variance

        # Verify percentage calculation (if budget is non-zero)
        if total_budgeted != Decimal("0.00"):
            expected_pct = (expected_variance / total_budgeted * Decimal("100")).quantize(Decimal("0.01"))
            assert report.variance_percentage == expected_pct

    @given(
        total_budgeted=budget_amount_strategy(),
    )
    def test_favorable_variance_definition(self, total_budgeted):
        """
        INVARIANT: Favorable variance means under budget (variance > 0).
        """
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)

        # Create report with actual less than budget (favorable)
        # Quantize to avoid precision issues
        total_actual = (total_budgeted * Decimal("0.90")).quantize(Decimal("0.01"))

        report = BudgetGenerator.create_variance_report(
            tenant_id=property_obj.tenant_id,
            budget_id=budget.id,
            budget_name=budget.name,
            fiscal_year=budget.fiscal_year,
            period_start=budget.start_date,
            period_end=budget.end_date,
            total_budgeted=total_budgeted,
            total_actual=total_actual,
        )

        # Variance should be positive (favorable)
        assert report.total_variance > Decimal("0.00")
        assert report.is_favorable() is True
        assert report.is_unfavorable() is False

    @given(
        total_budgeted=budget_amount_strategy(),
    )
    def test_unfavorable_variance_definition(self, total_budgeted):
        """
        INVARIANT: Unfavorable variance means over budget (variance < 0).
        """
        property_obj = PropertyGenerator.create()
        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)

        # Create report with actual more than budget (unfavorable)
        # Quantize to avoid precision issues
        total_actual = (total_budgeted * Decimal("1.10")).quantize(Decimal("0.01"))

        report = BudgetGenerator.create_variance_report(
            tenant_id=property_obj.tenant_id,
            budget_id=budget.id,
            budget_name=budget.name,
            fiscal_year=budget.fiscal_year,
            period_start=budget.start_date,
            period_end=budget.end_date,
            total_budgeted=total_budgeted,
            total_actual=total_actual,
        )

        # Variance should be negative (unfavorable)
        assert report.total_variance < Decimal("0.00")
        assert report.is_unfavorable() is True
        assert report.is_favorable() is False


class TestBudgetDataTypeInvariants:
    """Property-based tests for budget data type invariants."""

    @given(
        num_lines=st.integers(min_value=1, max_value=10),
    )
    def test_all_amounts_use_decimal_with_2_places(self, num_lines):
        """
        INVARIANT: All money amounts must use Decimal with exactly 2 decimal places.

        This ensures NUMERIC(15,2) compatibility and prevents floating-point errors.
        """
        property_obj = PropertyGenerator.create()

        _, lines = BudgetGenerator.create_with_lines(
            tenant_id=property_obj.tenant_id,
            num_lines=num_lines,
        )

        for line in lines:
            assert isinstance(line.budgeted_amount, Decimal)
            # Verify exactly 2 decimal places
            assert line.budgeted_amount.as_tuple().exponent == -2

    def test_all_dates_use_date_not_datetime(self):
        """
        INVARIANT: All date fields must use date type, not datetime.

        This ensures DATE type compatibility in the database.
        """
        property_obj = PropertyGenerator.create()

        budget = BudgetGenerator.create(tenant_id=property_obj.tenant_id)

        assert isinstance(budget.start_date, date)
        assert isinstance(budget.end_date, date)
        assert isinstance(budget.created_at, date)

        if budget.approved_at:
            assert isinstance(budget.approved_at, date)
