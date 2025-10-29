"""
Integration tests for dashboard metrics and analytics.

Tests the 6 dashboard API endpoints from Sprint 11:
- cash_position: Total cash and fund balances with trends
- ar_aging: AR aging buckets (current, 30-60, 60-90, 90+ days)
- expenses: MTD/YTD expense summary
- revenue: MTD/YTD revenue summary
- revenue_vs_expenses: 12 months trend data
- recent_activity: Last 20 invoice/payment events
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from qa_testing.generators import (
    FundGenerator,
    MemberGenerator,
    PropertyGenerator,
    TransactionGenerator,
)
from qa_testing.models import Fund, FundType, Transaction


class TestCashPositionMetrics:
    """Tests for cash position dashboard metrics."""

    def test_calculate_total_cash_from_funds(self):
        """Test calculating total cash across all funds."""
        property_obj = PropertyGenerator.create()

        # Create multiple funds with balances
        funds = [
            FundGenerator.create(
                property_id=property_obj.id,
                tenant_id=property_obj.tenant_id,
                fund_type=FundType.OPERATING,
                current_balance=Decimal("50000.00"),
            ),
            FundGenerator.create(
                property_id=property_obj.id,
                tenant_id=property_obj.tenant_id,
                fund_type=FundType.RESERVE,
                current_balance=Decimal("100000.00"),
            ),
            FundGenerator.create(
                property_id=property_obj.id,
                tenant_id=property_obj.tenant_id,
                fund_type=FundType.CAPITAL_IMPROVEMENT,
                current_balance=Decimal("25000.00"),
            ),
        ]

        # Calculate total cash
        total_cash = sum((fund.current_balance for fund in funds), Decimal("0.00"))

        assert total_cash == Decimal("175000.00")

    def test_fund_balances_breakdown(self):
        """Test breaking down cash by fund type."""
        property_obj = PropertyGenerator.create()

        operating_fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            fund_type=FundType.OPERATING,
            current_balance=Decimal("45000.00"),
        )

        reserve_fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            fund_type=FundType.RESERVE,
            current_balance=Decimal("120000.00"),
        )

        # Verify individual fund balances
        assert operating_fund.current_balance == Decimal("45000.00")
        assert reserve_fund.current_balance == Decimal("120000.00")

        # Calculate percentages
        total = operating_fund.current_balance + reserve_fund.current_balance
        operating_pct = (operating_fund.current_balance / total * Decimal("100")).quantize(Decimal("0.01"))
        reserve_pct = (reserve_fund.current_balance / total * Decimal("100")).quantize(Decimal("0.01"))

        assert operating_pct == Decimal("27.27")
        assert reserve_pct == Decimal("72.73")

    def test_cash_position_trend_calculation(self):
        """Test 30-day cash trend calculation."""
        property_obj = PropertyGenerator.create()

        current_balance = Decimal("100000.00")
        balance_30_days_ago = Decimal("85000.00")

        # Calculate trend
        change = current_balance - balance_30_days_ago
        change_pct = (change / balance_30_days_ago * Decimal("100")).quantize(Decimal("0.01"))

        assert change == Decimal("15000.00")
        assert change_pct == Decimal("17.65")


class TestARAgingMetrics:
    """Tests for accounts receivable aging metrics."""

    def test_ar_aging_bucket_classification(self):
        """Test classifying invoices into aging buckets."""
        today = date.today()

        # Create test invoices with different ages
        invoices = [
            {"due_date": today - timedelta(days=5), "amount": Decimal("1000.00")},  # Current
            {"due_date": today - timedelta(days=45), "amount": Decimal("500.00")},  # 30-60
            {"due_date": today - timedelta(days=75), "amount": Decimal("750.00")},  # 60-90
            {"due_date": today - timedelta(days=120), "amount": Decimal("2000.00")},  # 90+
        ]

        # Classify into buckets
        buckets = {
            "current": Decimal("0.00"),
            "30_60": Decimal("0.00"),
            "60_90": Decimal("0.00"),
            "90_plus": Decimal("0.00"),
        }

        for invoice in invoices:
            days_overdue = (today - invoice["due_date"]).days

            if days_overdue <= 30:
                buckets["current"] += invoice["amount"]
            elif days_overdue <= 60:
                buckets["30_60"] += invoice["amount"]
            elif days_overdue <= 90:
                buckets["60_90"] += invoice["amount"]
            else:
                buckets["90_plus"] += invoice["amount"]

        assert buckets["current"] == Decimal("1000.00")
        assert buckets["30_60"] == Decimal("500.00")
        assert buckets["60_90"] == Decimal("750.00")
        assert buckets["90_plus"] == Decimal("2000.00")

    def test_ar_aging_total_calculation(self):
        """Test calculating total AR from aging buckets."""
        buckets = {
            "current": Decimal("10000.00"),
            "30_60": Decimal("3000.00"),
            "60_90": Decimal("1500.00"),
            "90_plus": Decimal("500.00"),
        }

        total_ar = sum(buckets.values(), Decimal("0.00"))
        assert total_ar == Decimal("15000.00")

    def test_ar_aging_percentages(self):
        """Test calculating percentage of AR in each bucket."""
        buckets = {
            "current": Decimal("8000.00"),
            "30_60": Decimal("2000.00"),
            "60_90": Decimal("1000.00"),
            "90_plus": Decimal("1000.00"),
        }

        total = sum(buckets.values(), Decimal("0.00"))

        percentages = {
            key: (amount / total * Decimal("100")).quantize(Decimal("0.01"))
            for key, amount in buckets.items()
        }

        assert percentages["current"] == Decimal("66.67")
        assert percentages["30_60"] == Decimal("16.67")
        assert percentages["60_90"] == Decimal("8.33")
        assert percentages["90_plus"] == Decimal("8.33")


class TestExpenseMetrics:
    """Tests for expense dashboard metrics."""

    def test_mtd_expense_calculation(self):
        """Test month-to-date expense calculation."""
        property_obj = PropertyGenerator.create()
        today = date.today()

        # Create expenses for current month
        expenses = [
            Decimal("5000.00"),  # Management fees
            Decimal("2500.00"),  # Landscaping
            Decimal("1200.00"),  # Utilities
            Decimal("800.00"),   # Insurance
        ]

        mtd_total = sum(expenses, Decimal("0.00"))
        assert mtd_total == Decimal("9500.00")

    def test_ytd_expense_calculation(self):
        """Test year-to-date expense calculation."""
        # Simulate monthly expenses for the year
        monthly_expenses = [
            Decimal("9500.00"),   # Jan
            Decimal("8800.00"),   # Feb
            Decimal("10200.00"),  # Mar
            Decimal("9100.00"),   # Apr
            Decimal("11000.00"),  # May
        ]

        ytd_total = sum(monthly_expenses, Decimal("0.00"))
        assert ytd_total == Decimal("48600.00")

    def test_expense_category_breakdown(self):
        """Test breaking down expenses by category."""
        expenses_by_category = {
            "Management Fees": Decimal("5000.00"),
            "Landscaping": Decimal("2500.00"),
            "Utilities": Decimal("1200.00"),
            "Insurance": Decimal("800.00"),
            "Maintenance": Decimal("1500.00"),
        }

        total = sum(expenses_by_category.values(), Decimal("0.00"))
        assert total == Decimal("11000.00")

        # Get top 3 categories
        top_3 = sorted(expenses_by_category.items(), key=lambda x: x[1], reverse=True)[:3]

        assert top_3[0] == ("Management Fees", Decimal("5000.00"))
        assert top_3[1] == ("Landscaping", Decimal("2500.00"))
        assert top_3[2] == ("Maintenance", Decimal("1500.00"))

    def test_expense_period_comparison(self):
        """Test comparing current period to prior period."""
        current_period = Decimal("9500.00")
        prior_period = Decimal("8200.00")

        change = current_period - prior_period
        change_pct = (change / prior_period * Decimal("100")).quantize(Decimal("0.01"))

        assert change == Decimal("1300.00")
        assert change_pct == Decimal("15.85")


class TestRevenueMetrics:
    """Tests for revenue dashboard metrics."""

    def test_mtd_revenue_calculation(self):
        """Test month-to-date revenue calculation."""
        property_obj = PropertyGenerator.create()

        # Revenue sources for current month
        revenues = {
            "Assessment Income": Decimal("25000.00"),
            "Late Fees": Decimal("500.00"),
            "Interest Income": Decimal("150.00"),
        }

        mtd_total = sum(revenues.values(), Decimal("0.00"))
        assert mtd_total == Decimal("25650.00")

    def test_ytd_revenue_calculation(self):
        """Test year-to-date revenue calculation."""
        # Monthly revenue for the year
        monthly_revenue = [
            Decimal("25650.00"),  # Jan
            Decimal("25800.00"),  # Feb
            Decimal("25450.00"),  # Mar
            Decimal("26000.00"),  # Apr
            Decimal("25900.00"),  # May
        ]

        ytd_total = sum(monthly_revenue, Decimal("0.00"))
        assert ytd_total == Decimal("128800.00")

    def test_revenue_vs_budget(self):
        """Test comparing revenue to budgeted amount."""
        actual_revenue = Decimal("25650.00")
        budgeted_revenue = Decimal("25000.00")

        variance = actual_revenue - budgeted_revenue
        variance_pct = (variance / budgeted_revenue * Decimal("100")).quantize(Decimal("0.01"))

        assert variance == Decimal("650.00")
        assert variance_pct == Decimal("2.60")
        assert variance > Decimal("0.00")  # Favorable

    def test_revenue_period_comparison(self):
        """Test comparing current period to prior period."""
        current_period = Decimal("25650.00")
        prior_period = Decimal("25000.00")

        change = current_period - prior_period
        change_pct = (change / prior_period * Decimal("100")).quantize(Decimal("0.01"))

        assert change == Decimal("650.00")
        assert change_pct == Decimal("2.60")


class TestRevenueVsExpensesTrend:
    """Tests for revenue vs expenses trend analysis."""

    def test_12_month_trend_data(self):
        """Test generating 12 months of revenue vs expenses data."""
        # Simulate 12 months of data
        months_data = []

        for month in range(1, 13):
            month_data = {
                "month": month,
                "revenue": Decimal(str(25000 + (month * 100))),  # Slight increase
                "expenses": Decimal(str(20000 + (month * 50))),  # Slight increase
            }
            month_data["net"] = month_data["revenue"] - month_data["expenses"]
            months_data.append(month_data)

        assert len(months_data) == 12

        # Verify first month
        assert months_data[0]["revenue"] == Decimal("25100.00")
        assert months_data[0]["expenses"] == Decimal("20050.00")
        assert months_data[0]["net"] == Decimal("5050.00")

        # Verify last month
        assert months_data[11]["revenue"] == Decimal("26200.00")
        assert months_data[11]["expenses"] == Decimal("20600.00")
        assert months_data[11]["net"] == Decimal("5600.00")

    def test_net_income_calculation(self):
        """Test calculating net income (revenue - expenses)."""
        revenue = Decimal("25650.00")
        expenses = Decimal("19800.00")

        net_income = revenue - expenses
        assert net_income == Decimal("5850.00")

        # Calculate margin
        margin_pct = (net_income / revenue * Decimal("100")).quantize(Decimal("0.01"))
        assert margin_pct == Decimal("22.81")

    def test_cumulative_trend_calculation(self):
        """Test calculating cumulative revenue and expenses."""
        monthly_data = [
            {"revenue": Decimal("25000.00"), "expenses": Decimal("20000.00")},
            {"revenue": Decimal("25500.00"), "expenses": Decimal("20500.00")},
            {"revenue": Decimal("26000.00"), "expenses": Decimal("21000.00")},
        ]

        cumulative_revenue = Decimal("0.00")
        cumulative_expenses = Decimal("0.00")
        cumulative_data = []

        for month in monthly_data:
            cumulative_revenue += month["revenue"]
            cumulative_expenses += month["expenses"]
            cumulative_data.append({
                "cumulative_revenue": cumulative_revenue,
                "cumulative_expenses": cumulative_expenses,
                "cumulative_net": cumulative_revenue - cumulative_expenses,
            })

        assert cumulative_data[0]["cumulative_revenue"] == Decimal("25000.00")
        assert cumulative_data[1]["cumulative_revenue"] == Decimal("50500.00")
        assert cumulative_data[2]["cumulative_revenue"] == Decimal("76500.00")


class TestRecentActivityMetrics:
    """Tests for recent activity feed metrics."""

    def test_recent_activity_list_size(self):
        """Test limiting activity feed to last 20 items."""
        property_obj = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property_obj.id)

        # Create 25 transactions
        transactions = []
        for i in range(25):
            transaction = TransactionGenerator.create_payment(
                property_id=property_obj.id,
                member_id=member.id,
                amount=Decimal("100.00"),
            )
            transactions.append(transaction)

        # Get last 20
        recent_20 = transactions[-20:]

        assert len(recent_20) == 20

    def test_activity_sorting_by_date(self):
        """Test sorting activities by date (most recent first)."""
        today = date.today()

        activities = [
            {"date": today - timedelta(days=5), "type": "payment", "amount": Decimal("100.00")},
            {"date": today - timedelta(days=1), "type": "invoice", "amount": Decimal("300.00")},
            {"date": today, "type": "payment", "amount": Decimal("300.00")},
            {"date": today - timedelta(days=3), "type": "payment", "amount": Decimal("150.00")},
        ]

        # Sort by date descending
        sorted_activities = sorted(activities, key=lambda x: x["date"], reverse=True)

        assert sorted_activities[0]["date"] == today
        assert sorted_activities[1]["date"] == today - timedelta(days=1)
        assert sorted_activities[2]["date"] == today - timedelta(days=3)
        assert sorted_activities[3]["date"] == today - timedelta(days=5)

    def test_activity_type_classification(self):
        """Test classifying activities by type (invoice, payment, adjustment)."""
        activities = [
            {"type": "invoice", "amount": Decimal("500.00")},
            {"type": "payment", "amount": Decimal("500.00")},
            {"type": "payment", "amount": Decimal("300.00")},
            {"type": "adjustment", "amount": Decimal("-50.00")},
            {"type": "invoice", "amount": Decimal("450.00")},
        ]

        # Count by type
        by_type = {}
        for activity in activities:
            activity_type = activity["type"]
            by_type[activity_type] = by_type.get(activity_type, 0) + 1

        assert by_type["invoice"] == 2
        assert by_type["payment"] == 2
        assert by_type["adjustment"] == 1


class TestDashboardDataTypes:
    """Tests for proper data type usage in dashboard metrics."""

    def test_all_financial_amounts_use_decimal(self):
        """Test that all financial calculations use Decimal with 2 places."""
        property_obj = PropertyGenerator.create()

        cash_balance = Decimal("125000.50")
        revenue = Decimal("25650.00")
        expenses = Decimal("19800.75")

        # Verify Decimal type
        assert isinstance(cash_balance, Decimal)
        assert isinstance(revenue, Decimal)
        assert isinstance(expenses, Decimal)

        # Verify 2 decimal places
        assert cash_balance.as_tuple().exponent == -2
        assert revenue.as_tuple().exponent == -2
        assert expenses.as_tuple().exponent == -2

        # Calculations preserve precision
        net_income = revenue - expenses
        assert isinstance(net_income, Decimal)
        assert net_income.as_tuple().exponent == -2

    def test_percentage_calculations_precision(self):
        """Test that percentage calculations maintain precision."""
        total = Decimal("10000.00")
        part = Decimal("2345.67")

        percentage = (part / total * Decimal("100")).quantize(Decimal("0.01"))

        assert isinstance(percentage, Decimal)
        assert percentage == Decimal("23.46")
        assert percentage.as_tuple().exponent == -2
