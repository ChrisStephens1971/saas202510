"""
Accuracy Validator for Point-in-Time Financial Data

Validates that point-in-time reconstruction produces accurate results by:
- Comparing expected vs actual balances
- Detecting variances and discrepancies
- Generating accuracy reports
- Verifying financial data integrity

Critical for:
- Audit compliance (proving reconstruction accuracy)
- Data integrity verification
- Error detection in financial calculations
- Compliance reporting
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VarianceSeverity(str, Enum):
    """Severity level of a variance."""
    NONE = "none"  # No variance
    MINOR = "minor"  # < 1% variance
    MODERATE = "moderate"  # 1-5% variance
    MAJOR = "major"  # 5-10% variance
    CRITICAL = "critical"  # > 10% variance


class BalanceVariance(BaseModel):
    """Represents a variance between expected and actual balance."""
    entity_type: str  # "member", "fund", "property"
    entity_id: UUID
    entity_name: Optional[str] = None
    as_of_date: date

    # Expected values (from point-in-time reconstruction)
    expected_balance: Decimal

    # Actual values (from current database state)
    actual_balance: Decimal

    # Variance calculation
    variance_amount: Decimal  # actual - expected
    variance_percentage: Decimal  # (variance / expected) * 100
    severity: VarianceSeverity

    # Additional context
    notes: Optional[str] = None


class AccuracyReport(BaseModel):
    """
    Comprehensive accuracy report for point-in-time reconstruction.

    Summarizes all variances found and provides overall accuracy metrics.
    """
    tenant_id: UUID
    report_date: datetime
    as_of_date: date  # Date being validated

    # Validation results
    total_entities_checked: int = 0
    entities_with_variances: int = 0
    entities_accurate: int = 0

    # Variance breakdown by severity
    critical_variances: int = 0
    major_variances: int = 0
    moderate_variances: int = 0
    minor_variances: int = 0

    # Detailed variances
    variances: list[BalanceVariance] = Field(default_factory=list)

    # Summary statistics
    total_expected: Decimal = Decimal("0.00")
    total_actual: Decimal = Decimal("0.00")
    total_variance: Decimal = Decimal("0.00")
    average_accuracy: Decimal = Decimal("100.00")  # Percentage

    # Overall status
    is_accurate: bool = True  # True if no critical/major variances
    accuracy_threshold_met: bool = True  # True if average accuracy >= 99%


class MemberBalanceComparison(BaseModel):
    """Comparison of expected vs actual member balance."""
    member_id: UUID
    tenant_id: UUID
    as_of_date: date

    # Expected (from reconstruction)
    expected_total_owed: Decimal
    expected_total_paid: Decimal
    expected_balance: Decimal

    # Actual (from current state)
    actual_total_owed: Decimal
    actual_total_paid: Decimal
    actual_balance: Decimal

    # Variances
    owed_variance: Decimal
    paid_variance: Decimal
    balance_variance: Decimal


class FundBalanceComparison(BaseModel):
    """Comparison of expected vs actual fund balance."""
    fund_id: UUID
    tenant_id: UUID
    as_of_date: date

    # Expected (from reconstruction)
    expected_debits: Decimal
    expected_credits: Decimal
    expected_balance: Decimal

    # Actual (from current state)
    actual_debits: Decimal
    actual_credits: Decimal
    actual_balance: Decimal

    # Variances
    debit_variance: Decimal
    credit_variance: Decimal
    balance_variance: Decimal


class AccuracyValidator:
    """
    Validates accuracy of point-in-time financial reconstruction.

    Compares expected (reconstructed) balances against actual balances
    and generates detailed variance reports.
    """

    # Variance thresholds (as percentages)
    MINOR_THRESHOLD = Decimal("1.0")  # < 1%
    MODERATE_THRESHOLD = Decimal("5.0")  # 1-5%
    MAJOR_THRESHOLD = Decimal("10.0")  # 5-10%
    # > 10% is CRITICAL

    @staticmethod
    def calculate_variance_severity(
        expected: Decimal,
        actual: Decimal
    ) -> VarianceSeverity:
        """
        Calculate severity of variance between expected and actual values.

        Args:
            expected: Expected balance
            actual: Actual balance

        Returns:
            VarianceSeverity level
        """
        if expected == Decimal("0.00"):
            # Special case: if expected is zero
            if actual == Decimal("0.00"):
                return VarianceSeverity.NONE
            else:
                # Any variance when expected is zero is critical
                return VarianceSeverity.CRITICAL

        variance = abs(actual - expected)
        percentage = (variance / abs(expected)) * Decimal("100")

        if percentage < Decimal("0.01"):  # Less than 0.01%
            return VarianceSeverity.NONE
        elif percentage < AccuracyValidator.MINOR_THRESHOLD:
            return VarianceSeverity.MINOR
        elif percentage < AccuracyValidator.MODERATE_THRESHOLD:
            return VarianceSeverity.MODERATE
        elif percentage < AccuracyValidator.MAJOR_THRESHOLD:
            return VarianceSeverity.MAJOR
        else:
            return VarianceSeverity.CRITICAL

    @staticmethod
    def compare_member_balance(
        member_id: UUID,
        tenant_id: UUID,
        as_of_date: date,
        expected_total_owed: Decimal,
        expected_total_paid: Decimal,
        actual_total_owed: Decimal,
        actual_total_paid: Decimal,
    ) -> MemberBalanceComparison:
        """
        Compare expected vs actual member balance.

        Args:
            member_id: Member ID
            tenant_id: Tenant ID
            as_of_date: Date of comparison
            expected_total_owed: Expected amount owed
            expected_total_paid: Expected amount paid
            actual_total_owed: Actual amount owed
            actual_total_paid: Actual amount paid

        Returns:
            MemberBalanceComparison with variances
        """
        expected_balance = expected_total_paid - expected_total_owed
        actual_balance = actual_total_paid - actual_total_owed

        return MemberBalanceComparison(
            member_id=member_id,
            tenant_id=tenant_id,
            as_of_date=as_of_date,
            expected_total_owed=expected_total_owed,
            expected_total_paid=expected_total_paid,
            expected_balance=expected_balance,
            actual_total_owed=actual_total_owed,
            actual_total_paid=actual_total_paid,
            actual_balance=actual_balance,
            owed_variance=actual_total_owed - expected_total_owed,
            paid_variance=actual_total_paid - expected_total_paid,
            balance_variance=actual_balance - expected_balance,
        )

    @staticmethod
    def compare_fund_balance(
        fund_id: UUID,
        tenant_id: UUID,
        as_of_date: date,
        expected_debits: Decimal,
        expected_credits: Decimal,
        actual_debits: Decimal,
        actual_credits: Decimal,
    ) -> FundBalanceComparison:
        """
        Compare expected vs actual fund balance.

        Args:
            fund_id: Fund ID
            tenant_id: Tenant ID
            as_of_date: Date of comparison
            expected_debits: Expected total debits
            expected_credits: Expected total credits
            actual_debits: Actual total debits
            actual_credits: Actual total credits

        Returns:
            FundBalanceComparison with variances
        """
        expected_balance = expected_debits - expected_credits
        actual_balance = actual_debits - actual_credits

        return FundBalanceComparison(
            fund_id=fund_id,
            tenant_id=tenant_id,
            as_of_date=as_of_date,
            expected_debits=expected_debits,
            expected_credits=expected_credits,
            expected_balance=expected_balance,
            actual_debits=actual_debits,
            actual_credits=actual_credits,
            actual_balance=actual_balance,
            debit_variance=actual_debits - expected_debits,
            credit_variance=actual_credits - expected_credits,
            balance_variance=actual_balance - expected_balance,
        )

    @staticmethod
    def create_balance_variance(
        entity_type: str,
        entity_id: UUID,
        as_of_date: date,
        expected_balance: Decimal,
        actual_balance: Decimal,
        entity_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> BalanceVariance:
        """
        Create a BalanceVariance record.

        Args:
            entity_type: Type of entity ("member", "fund", "property")
            entity_id: Entity ID
            as_of_date: Date of comparison
            expected_balance: Expected balance from reconstruction
            actual_balance: Actual balance from database
            entity_name: Optional entity name
            notes: Optional notes about the variance

        Returns:
            BalanceVariance record
        """
        variance_amount = actual_balance - expected_balance

        # Calculate percentage variance (always positive - magnitude of error)
        if expected_balance == Decimal("0.00"):
            if actual_balance == Decimal("0.00"):
                variance_percentage = Decimal("0.00")
            else:
                # Infinite variance - use 100% as proxy
                variance_percentage = Decimal("100.00")
        else:
            variance_percentage = (abs(variance_amount) / abs(expected_balance)) * Decimal("100")

        severity = AccuracyValidator.calculate_variance_severity(
            expected_balance,
            actual_balance
        )

        return BalanceVariance(
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            as_of_date=as_of_date,
            expected_balance=expected_balance,
            actual_balance=actual_balance,
            variance_amount=variance_amount,
            variance_percentage=variance_percentage,
            severity=severity,
            notes=notes,
        )

    @staticmethod
    def generate_accuracy_report(
        tenant_id: UUID,
        as_of_date: date,
        variances: list[BalanceVariance],
    ) -> AccuracyReport:
        """
        Generate comprehensive accuracy report from variances.

        Args:
            tenant_id: Tenant ID
            as_of_date: Date being validated
            variances: List of balance variances

        Returns:
            AccuracyReport with summary statistics
        """
        # Count entities
        total_checked = len(variances)
        entities_with_variances = sum(
            1 for v in variances if v.severity != VarianceSeverity.NONE
        )
        entities_accurate = total_checked - entities_with_variances

        # Count by severity
        critical_count = sum(1 for v in variances if v.severity == VarianceSeverity.CRITICAL)
        major_count = sum(1 for v in variances if v.severity == VarianceSeverity.MAJOR)
        moderate_count = sum(1 for v in variances if v.severity == VarianceSeverity.MODERATE)
        minor_count = sum(1 for v in variances if v.severity == VarianceSeverity.MINOR)

        # Calculate totals
        total_expected = sum(v.expected_balance for v in variances)
        total_actual = sum(v.actual_balance for v in variances)
        total_variance = total_actual - total_expected

        # Calculate average accuracy
        if total_checked > 0:
            accurate_count = sum(
                1 for v in variances
                if v.severity in [VarianceSeverity.NONE, VarianceSeverity.MINOR]
            )
            average_accuracy = (Decimal(accurate_count) / Decimal(total_checked)) * Decimal("100")
        else:
            average_accuracy = Decimal("100.00")

        # Determine overall status
        is_accurate = (critical_count == 0 and major_count == 0)
        accuracy_threshold_met = average_accuracy >= Decimal("99.00")

        return AccuracyReport(
            tenant_id=tenant_id,
            report_date=datetime.now(),
            as_of_date=as_of_date,
            total_entities_checked=total_checked,
            entities_with_variances=entities_with_variances,
            entities_accurate=entities_accurate,
            critical_variances=critical_count,
            major_variances=major_count,
            moderate_variances=moderate_count,
            minor_variances=minor_count,
            variances=variances,
            total_expected=total_expected,
            total_actual=total_actual,
            total_variance=total_variance,
            average_accuracy=average_accuracy,
            is_accurate=is_accurate,
            accuracy_threshold_met=accuracy_threshold_met,
        )

    @staticmethod
    def validate_balances_match(
        expected: Decimal,
        actual: Decimal,
        tolerance: Decimal = Decimal("0.01"),
    ) -> bool:
        """
        Validate that expected and actual balances match within tolerance.

        Args:
            expected: Expected balance
            actual: Actual balance
            tolerance: Acceptable difference (default: 1 cent)

        Returns:
            True if balances match within tolerance
        """
        variance = abs(actual - expected)
        return variance <= tolerance

    @staticmethod
    def calculate_accuracy_percentage(
        expected: Decimal,
        actual: Decimal,
    ) -> Decimal:
        """
        Calculate accuracy as a percentage.

        Args:
            expected: Expected balance
            actual: Actual balance

        Returns:
            Accuracy percentage (0-100)
        """
        if expected == Decimal("0.00"):
            if actual == Decimal("0.00"):
                return Decimal("100.00")
            else:
                return Decimal("0.00")

        variance = abs(actual - expected)
        accuracy = (Decimal("1.00") - (variance / abs(expected))) * Decimal("100")

        # Clamp to 0-100 range
        if accuracy < Decimal("0.00"):
            accuracy = Decimal("0.00")
        elif accuracy > Decimal("100.00"):
            accuracy = Decimal("100.00")

        return accuracy
