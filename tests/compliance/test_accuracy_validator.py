"""
Tests for Accuracy Validator

Tests point-in-time reconstruction accuracy validation:
- Variance calculation and severity classification
- Member balance comparison
- Fund balance comparison
- Accuracy report generation
- Tolerance validation
- Edge cases (zero balances, large variances)
"""

import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from qa_testing.compliance import (
    AccuracyValidator,
    AccuracyReport,
    BalanceVariance,
    FundBalanceComparison,
    MemberBalanceComparison,
    VarianceSeverity,
)


class TestVarianceSeverityCalculation:
    """Test variance severity classification."""

    def test_no_variance(self):
        """Test that identical values have no variance."""
        severity = AccuracyValidator.calculate_variance_severity(
            expected=Decimal("1000.00"),
            actual=Decimal("1000.00"),
        )
        assert severity == VarianceSeverity.NONE

    def test_minor_variance(self):
        """Test minor variance (< 1%)."""
        severity = AccuracyValidator.calculate_variance_severity(
            expected=Decimal("1000.00"),
            actual=Decimal("1005.00"),  # 0.5% variance
        )
        assert severity == VarianceSeverity.MINOR

    def test_moderate_variance(self):
        """Test moderate variance (1-5%)."""
        severity = AccuracyValidator.calculate_variance_severity(
            expected=Decimal("1000.00"),
            actual=Decimal("1030.00"),  # 3% variance
        )
        assert severity == VarianceSeverity.MODERATE

    def test_major_variance(self):
        """Test major variance (5-10%)."""
        severity = AccuracyValidator.calculate_variance_severity(
            expected=Decimal("1000.00"),
            actual=Decimal("1070.00"),  # 7% variance
        )
        assert severity == VarianceSeverity.MAJOR

    def test_critical_variance(self):
        """Test critical variance (> 10%)."""
        severity = AccuracyValidator.calculate_variance_severity(
            expected=Decimal("1000.00"),
            actual=Decimal("1200.00"),  # 20% variance
        )
        assert severity == VarianceSeverity.CRITICAL

    def test_zero_expected_zero_actual(self):
        """Test zero expected and zero actual."""
        severity = AccuracyValidator.calculate_variance_severity(
            expected=Decimal("0.00"),
            actual=Decimal("0.00"),
        )
        assert severity == VarianceSeverity.NONE

    def test_zero_expected_nonzero_actual(self):
        """Test zero expected with non-zero actual (critical)."""
        severity = AccuracyValidator.calculate_variance_severity(
            expected=Decimal("0.00"),
            actual=Decimal("100.00"),
        )
        assert severity == VarianceSeverity.CRITICAL

    def test_negative_variance(self):
        """Test that negative variance uses absolute value."""
        severity = AccuracyValidator.calculate_variance_severity(
            expected=Decimal("1000.00"),
            actual=Decimal("970.00"),  # -3% variance
        )
        assert severity == VarianceSeverity.MODERATE


class TestMemberBalanceComparison:
    """Test member balance comparison."""

    def test_compare_matching_balances(self):
        """Test comparison with matching balances."""
        member_id = uuid4()
        tenant_id = uuid4()

        comparison = AccuracyValidator.compare_member_balance(
            member_id=member_id,
            tenant_id=tenant_id,
            as_of_date=date(2025, 1, 31),
            expected_total_owed=Decimal("1000.00"),
            expected_total_paid=Decimal("800.00"),
            actual_total_owed=Decimal("1000.00"),
            actual_total_paid=Decimal("800.00"),
        )

        assert comparison.member_id == member_id
        assert comparison.tenant_id == tenant_id
        assert comparison.expected_balance == Decimal("-200.00")  # paid - owed
        assert comparison.actual_balance == Decimal("-200.00")
        assert comparison.owed_variance == Decimal("0.00")
        assert comparison.paid_variance == Decimal("0.00")
        assert comparison.balance_variance == Decimal("0.00")

    def test_compare_with_owed_variance(self):
        """Test comparison with variance in owed amount."""
        comparison = AccuracyValidator.compare_member_balance(
            member_id=uuid4(),
            tenant_id=uuid4(),
            as_of_date=date(2025, 1, 31),
            expected_total_owed=Decimal("1000.00"),
            expected_total_paid=Decimal("800.00"),
            actual_total_owed=Decimal("1050.00"),  # $50 more owed
            actual_total_paid=Decimal("800.00"),
        )

        assert comparison.owed_variance == Decimal("50.00")
        assert comparison.paid_variance == Decimal("0.00")
        assert comparison.balance_variance == Decimal("-50.00")  # More owed = worse balance

    def test_compare_with_paid_variance(self):
        """Test comparison with variance in paid amount."""
        comparison = AccuracyValidator.compare_member_balance(
            member_id=uuid4(),
            tenant_id=uuid4(),
            as_of_date=date(2025, 1, 31),
            expected_total_owed=Decimal("1000.00"),
            expected_total_paid=Decimal("800.00"),
            actual_total_owed=Decimal("1000.00"),
            actual_total_paid=Decimal("850.00"),  # $50 more paid
        )

        assert comparison.owed_variance == Decimal("0.00")
        assert comparison.paid_variance == Decimal("50.00")
        assert comparison.balance_variance == Decimal("50.00")  # More paid = better balance


class TestFundBalanceComparison:
    """Test fund balance comparison."""

    def test_compare_matching_balances(self):
        """Test comparison with matching balances."""
        fund_id = uuid4()
        tenant_id = uuid4()

        comparison = AccuracyValidator.compare_fund_balance(
            fund_id=fund_id,
            tenant_id=tenant_id,
            as_of_date=date(2025, 1, 31),
            expected_debits=Decimal("5000.00"),
            expected_credits=Decimal("3000.00"),
            actual_debits=Decimal("5000.00"),
            actual_credits=Decimal("3000.00"),
        )

        assert comparison.fund_id == fund_id
        assert comparison.tenant_id == tenant_id
        assert comparison.expected_balance == Decimal("2000.00")  # debits - credits
        assert comparison.actual_balance == Decimal("2000.00")
        assert comparison.debit_variance == Decimal("0.00")
        assert comparison.credit_variance == Decimal("0.00")
        assert comparison.balance_variance == Decimal("0.00")

    def test_compare_with_debit_variance(self):
        """Test comparison with variance in debits."""
        comparison = AccuracyValidator.compare_fund_balance(
            fund_id=uuid4(),
            tenant_id=uuid4(),
            as_of_date=date(2025, 1, 31),
            expected_debits=Decimal("5000.00"),
            expected_credits=Decimal("3000.00"),
            actual_debits=Decimal("5100.00"),  # $100 more debits
            actual_credits=Decimal("3000.00"),
        )

        assert comparison.debit_variance == Decimal("100.00")
        assert comparison.credit_variance == Decimal("0.00")
        assert comparison.balance_variance == Decimal("100.00")

    def test_compare_with_credit_variance(self):
        """Test comparison with variance in credits."""
        comparison = AccuracyValidator.compare_fund_balance(
            fund_id=uuid4(),
            tenant_id=uuid4(),
            as_of_date=date(2025, 1, 31),
            expected_debits=Decimal("5000.00"),
            expected_credits=Decimal("3000.00"),
            actual_debits=Decimal("5000.00"),
            actual_credits=Decimal("3200.00"),  # $200 more credits
        )

        assert comparison.debit_variance == Decimal("0.00")
        assert comparison.credit_variance == Decimal("200.00")
        assert comparison.balance_variance == Decimal("-200.00")  # More credits = lower balance


class TestBalanceVarianceCreation:
    """Test BalanceVariance record creation."""

    def test_create_variance_with_no_variance(self):
        """Test creating variance record with matching balances."""
        variance = AccuracyValidator.create_balance_variance(
            entity_type="member",
            entity_id=uuid4(),
            as_of_date=date(2025, 1, 31),
            expected_balance=Decimal("1000.00"),
            actual_balance=Decimal("1000.00"),
            entity_name="John Doe",
        )

        assert variance.entity_type == "member"
        assert variance.entity_name == "John Doe"
        assert variance.variance_amount == Decimal("0.00")
        assert variance.variance_percentage == Decimal("0.00")
        assert variance.severity == VarianceSeverity.NONE

    def test_create_variance_with_minor_difference(self):
        """Test creating variance record with minor difference."""
        variance = AccuracyValidator.create_balance_variance(
            entity_type="fund",
            entity_id=uuid4(),
            as_of_date=date(2025, 1, 31),
            expected_balance=Decimal("10000.00"),
            actual_balance=Decimal("10050.00"),  # 0.5% variance
        )

        assert variance.variance_amount == Decimal("50.00")
        assert variance.variance_percentage == Decimal("0.50")
        assert variance.severity == VarianceSeverity.MINOR

    def test_create_variance_with_critical_difference(self):
        """Test creating variance record with critical difference."""
        variance = AccuracyValidator.create_balance_variance(
            entity_type="property",
            entity_id=uuid4(),
            as_of_date=date(2025, 1, 31),
            expected_balance=Decimal("5000.00"),
            actual_balance=Decimal("6000.00"),  # 20% variance
            notes="Large discrepancy - investigate",
        )

        assert variance.variance_amount == Decimal("1000.00")
        assert variance.variance_percentage == Decimal("20.00")
        assert variance.severity == VarianceSeverity.CRITICAL
        assert variance.notes == "Large discrepancy - investigate"

    def test_create_variance_negative_actual(self):
        """Test creating variance with negative actual balance."""
        variance = AccuracyValidator.create_balance_variance(
            entity_type="member",
            entity_id=uuid4(),
            as_of_date=date(2025, 1, 31),
            expected_balance=Decimal("100.00"),
            actual_balance=Decimal("-100.00"),  # 200% variance (wrong sign)
        )

        assert variance.variance_amount == Decimal("-200.00")
        assert variance.severity == VarianceSeverity.CRITICAL


class TestAccuracyReportGeneration:
    """Test accuracy report generation."""

    def test_generate_report_all_accurate(self):
        """Test report generation with all accurate balances."""
        tenant_id = uuid4()
        variances = [
            BalanceVariance(
                entity_type="member",
                entity_id=uuid4(),
                as_of_date=date(2025, 1, 31),
                expected_balance=Decimal("1000.00"),
                actual_balance=Decimal("1000.00"),
                variance_amount=Decimal("0.00"),
                variance_percentage=Decimal("0.00"),
                severity=VarianceSeverity.NONE,
            ),
            BalanceVariance(
                entity_type="fund",
                entity_id=uuid4(),
                as_of_date=date(2025, 1, 31),
                expected_balance=Decimal("5000.00"),
                actual_balance=Decimal("5000.00"),
                variance_amount=Decimal("0.00"),
                variance_percentage=Decimal("0.00"),
                severity=VarianceSeverity.NONE,
            ),
        ]

        report = AccuracyValidator.generate_accuracy_report(
            tenant_id=tenant_id,
            as_of_date=date(2025, 1, 31),
            variances=variances,
        )

        assert report.tenant_id == tenant_id
        assert report.total_entities_checked == 2
        assert report.entities_with_variances == 0
        assert report.entities_accurate == 2
        assert report.critical_variances == 0
        assert report.major_variances == 0
        assert report.moderate_variances == 0
        assert report.minor_variances == 0
        assert report.average_accuracy == Decimal("100.00")
        assert report.is_accurate is True
        assert report.accuracy_threshold_met is True

    def test_generate_report_with_minor_variances(self):
        """Test report generation with minor variances."""
        tenant_id = uuid4()
        variances = [
            BalanceVariance(
                entity_type="member",
                entity_id=uuid4(),
                as_of_date=date(2025, 1, 31),
                expected_balance=Decimal("1000.00"),
                actual_balance=Decimal("1005.00"),
                variance_amount=Decimal("5.00"),
                variance_percentage=Decimal("0.50"),
                severity=VarianceSeverity.MINOR,
            ),
            BalanceVariance(
                entity_type="fund",
                entity_id=uuid4(),
                as_of_date=date(2025, 1, 31),
                expected_balance=Decimal("5000.00"),
                actual_balance=Decimal("5000.00"),
                variance_amount=Decimal("0.00"),
                variance_percentage=Decimal("0.00"),
                severity=VarianceSeverity.NONE,
            ),
        ]

        report = AccuracyValidator.generate_accuracy_report(
            tenant_id=tenant_id,
            as_of_date=date(2025, 1, 31),
            variances=variances,
        )

        assert report.total_entities_checked == 2
        assert report.entities_with_variances == 1
        assert report.entities_accurate == 1
        assert report.minor_variances == 1
        assert report.average_accuracy == Decimal("100.00")  # Both none and minor count as accurate
        assert report.is_accurate is True  # No critical/major
        assert report.accuracy_threshold_met is True  # >= 99%

    def test_generate_report_with_critical_variances(self):
        """Test report generation with critical variances."""
        tenant_id = uuid4()
        variances = [
            BalanceVariance(
                entity_type="member",
                entity_id=uuid4(),
                as_of_date=date(2025, 1, 31),
                expected_balance=Decimal("1000.00"),
                actual_balance=Decimal("1500.00"),
                variance_amount=Decimal("500.00"),
                variance_percentage=Decimal("50.00"),
                severity=VarianceSeverity.CRITICAL,
            ),
            BalanceVariance(
                entity_type="fund",
                entity_id=uuid4(),
                as_of_date=date(2025, 1, 31),
                expected_balance=Decimal("5000.00"),
                actual_balance=Decimal("5000.00"),
                variance_amount=Decimal("0.00"),
                variance_percentage=Decimal("0.00"),
                severity=VarianceSeverity.NONE,
            ),
        ]

        report = AccuracyValidator.generate_accuracy_report(
            tenant_id=tenant_id,
            as_of_date=date(2025, 1, 31),
            variances=variances,
        )

        assert report.total_entities_checked == 2
        assert report.entities_with_variances == 1
        assert report.critical_variances == 1
        assert report.average_accuracy == Decimal("50.00")  # Only 1 of 2 accurate
        assert report.is_accurate is False  # Has critical variance
        assert report.accuracy_threshold_met is False  # < 99%

    def test_generate_report_empty_variances(self):
        """Test report generation with no variances."""
        report = AccuracyValidator.generate_accuracy_report(
            tenant_id=uuid4(),
            as_of_date=date(2025, 1, 31),
            variances=[],
        )

        assert report.total_entities_checked == 0
        assert report.entities_with_variances == 0
        assert report.entities_accurate == 0
        assert report.average_accuracy == Decimal("100.00")
        assert report.is_accurate is True
        assert report.accuracy_threshold_met is True


class TestBalanceValidation:
    """Test balance validation with tolerance."""

    def test_validate_exact_match(self):
        """Test validation with exact match."""
        is_valid = AccuracyValidator.validate_balances_match(
            expected=Decimal("1000.00"),
            actual=Decimal("1000.00"),
        )
        assert is_valid is True

    def test_validate_within_tolerance(self):
        """Test validation within tolerance."""
        is_valid = AccuracyValidator.validate_balances_match(
            expected=Decimal("1000.00"),
            actual=Decimal("1000.01"),  # 1 cent difference
            tolerance=Decimal("0.01"),
        )
        assert is_valid is True

    def test_validate_exceeds_tolerance(self):
        """Test validation exceeds tolerance."""
        is_valid = AccuracyValidator.validate_balances_match(
            expected=Decimal("1000.00"),
            actual=Decimal("1000.02"),  # 2 cents difference
            tolerance=Decimal("0.01"),
        )
        assert is_valid is False

    def test_validate_negative_variance(self):
        """Test validation with negative variance."""
        is_valid = AccuracyValidator.validate_balances_match(
            expected=Decimal("1000.00"),
            actual=Decimal("999.99"),  # 1 cent less
            tolerance=Decimal("0.01"),
        )
        assert is_valid is True


class TestAccuracyPercentageCalculation:
    """Test accuracy percentage calculation."""

    def test_calculate_100_percent_accuracy(self):
        """Test 100% accuracy (exact match)."""
        accuracy = AccuracyValidator.calculate_accuracy_percentage(
            expected=Decimal("1000.00"),
            actual=Decimal("1000.00"),
        )
        assert accuracy == Decimal("100.00")

    def test_calculate_99_percent_accuracy(self):
        """Test 99% accuracy."""
        accuracy = AccuracyValidator.calculate_accuracy_percentage(
            expected=Decimal("1000.00"),
            actual=Decimal("990.00"),  # 1% off
        )
        assert accuracy == Decimal("99.00")

    def test_calculate_50_percent_accuracy(self):
        """Test 50% accuracy."""
        accuracy = AccuracyValidator.calculate_accuracy_percentage(
            expected=Decimal("1000.00"),
            actual=Decimal("500.00"),  # 50% off
        )
        assert accuracy == Decimal("50.00")

    def test_calculate_zero_percent_accuracy(self):
        """Test 0% accuracy (completely wrong)."""
        accuracy = AccuracyValidator.calculate_accuracy_percentage(
            expected=Decimal("1000.00"),
            actual=Decimal("0.00"),  # 100% off
        )
        assert accuracy == Decimal("0.00")

    def test_calculate_accuracy_zero_expected(self):
        """Test accuracy calculation with zero expected."""
        # When expected is zero and actual is zero
        accuracy = AccuracyValidator.calculate_accuracy_percentage(
            expected=Decimal("0.00"),
            actual=Decimal("0.00"),
        )
        assert accuracy == Decimal("100.00")

        # When expected is zero and actual is non-zero
        accuracy = AccuracyValidator.calculate_accuracy_percentage(
            expected=Decimal("0.00"),
            actual=Decimal("100.00"),
        )
        assert accuracy == Decimal("0.00")

    def test_calculate_accuracy_negative_variance(self):
        """Test accuracy calculation with negative variance."""
        accuracy = AccuracyValidator.calculate_accuracy_percentage(
            expected=Decimal("1000.00"),
            actual=Decimal("1100.00"),  # 10% over
        )
        assert accuracy == Decimal("90.00")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_large_amounts(self):
        """Test variance calculation with very large amounts."""
        variance = AccuracyValidator.create_balance_variance(
            entity_type="property",
            entity_id=uuid4(),
            as_of_date=date(2025, 1, 31),
            expected_balance=Decimal("999999999.99"),
            actual_balance=Decimal("1000000000.00"),
        )

        assert variance.severity == VarianceSeverity.NONE  # Very small percentage

    def test_very_small_amounts(self):
        """Test variance calculation with very small amounts."""
        variance = AccuracyValidator.create_balance_variance(
            entity_type="member",
            entity_id=uuid4(),
            as_of_date=date(2025, 1, 31),
            expected_balance=Decimal("0.01"),
            actual_balance=Decimal("0.02"),
        )

        assert variance.variance_percentage == Decimal("100.00")
        assert variance.severity == VarianceSeverity.CRITICAL

    def test_negative_balances(self):
        """Test variance calculation with negative balances."""
        variance = AccuracyValidator.create_balance_variance(
            entity_type="member",
            entity_id=uuid4(),
            as_of_date=date(2025, 1, 31),
            expected_balance=Decimal("-1000.00"),
            actual_balance=Decimal("-1050.00"),
        )

        assert variance.variance_amount == Decimal("-50.00")
        assert variance.variance_percentage == Decimal("5.00")
        assert variance.severity == VarianceSeverity.MAJOR  # 5% is at boundary (5-10% = MAJOR)
