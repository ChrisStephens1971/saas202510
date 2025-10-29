"""
Integration tests for reserve planning functionality.

Tests the complete reserve study lifecycle including:
- Reserve study creation and validation
- Reserve component management
- Funding scenarios (baseline, aggressive, minimal)
- Multi-year funding projections
- Funding adequacy calculations
- Inflation and interest calculations
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from qa_testing.generators import (
    FundGenerator,
    PropertyGenerator,
    ReserveComponentGenerator,
    ReserveProjectionGenerator,
    ReserveScenarioGenerator,
    ReserveStudyGenerator,
)
from qa_testing.models import (
    ComponentCategory,
    FundingStatus,
    ReserveComponent,
    ReserveProjection,
    ReserveScenario,
    ReserveStudy,
)


class TestReserveStudyCreation:
    """Tests for reserve study creation and validation."""

    def test_create_reserve_study_with_valid_data(self):
        """Test creating a reserve study with valid horizon and rates."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(
            tenant_id=property_obj.tenant_id,
            horizon_years=20,
            inflation_rate=Decimal("3.00"),
            interest_rate=Decimal("1.50"),
        )

        assert study.horizon_years == 20
        assert study.inflation_rate == Decimal("3.00")
        assert study.interest_rate == Decimal("1.50")
        assert study.current_reserve_balance >= Decimal("0.00")

    def test_reserve_study_horizon_validation(self):
        """Test that horizon years must be between 5 and 30."""
        property_obj = PropertyGenerator.create()

        # Too short
        with pytest.raises(ValueError, match="horizon_years must be between 5 and 30"):
            ReserveStudyGenerator.create(
                tenant_id=property_obj.tenant_id,
                horizon_years=3,  # Too short
            )

        # Too long
        with pytest.raises(ValueError, match="horizon_years must be between 5 and 30"):
            ReserveStudyGenerator.create(
                tenant_id=property_obj.tenant_id,
                horizon_years=40,  # Too long
            )

    def test_reserve_study_inflation_rate_validation(self):
        """Test that inflation rate must be reasonable."""
        property_obj = PropertyGenerator.create()

        with pytest.raises(ValueError, match="inflation_rate must be between 0 and 20 percent"):
            ReserveStudyGenerator.create(
                tenant_id=property_obj.tenant_id,
                inflation_rate=Decimal("25.00"),  # Too high
            )

    def test_reserve_study_interest_rate_validation(self):
        """Test that interest rate must be reasonable."""
        property_obj = PropertyGenerator.create()

        with pytest.raises(ValueError, match="interest_rate must be between 0 and 10 percent"):
            ReserveStudyGenerator.create(
                tenant_id=property_obj.tenant_id,
                interest_rate=Decimal("15.00"),  # Too high
            )

    def test_reserve_study_current_balance_validation(self):
        """Test that current reserve balance cannot be negative."""
        property_obj = PropertyGenerator.create()

        with pytest.raises(ValueError, match="current_reserve_balance cannot be negative"):
            ReserveStudyGenerator.create(
                tenant_id=property_obj.tenant_id,
                current_reserve_balance=Decimal("-1000.00"),  # Invalid
            )


class TestReserveComponents:
    """Tests for reserve component creation and management."""

    def test_create_roofing_component(self):
        """Test creating a roofing component."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        component = ReserveComponentGenerator.create_roofing(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        assert component.category == ComponentCategory.ROOFING
        assert component.useful_life_years > 0
        assert component.replacement_cost > Decimal("0.00")

    def test_create_paving_component(self):
        """Test creating a paving component."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        component = ReserveComponentGenerator.create_paving(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        assert component.category == ComponentCategory.PAVING
        assert component.replacement_cost > Decimal("0.00")

    def test_create_painting_component(self):
        """Test creating a painting component."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        component = ReserveComponentGenerator.create_painting(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        assert component.category == ComponentCategory.PAINTING
        assert component.useful_life_years > 0

    def test_create_pool_component(self):
        """Test creating a pool equipment component."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        component = ReserveComponentGenerator.create_pool(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        assert component.category == ComponentCategory.POOL
        assert component.replacement_cost > Decimal("0.00")

    def test_component_remaining_life_validation(self):
        """Test that remaining life cannot exceed useful life."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        with pytest.raises(ValueError, match="remaining_life_years cannot exceed useful_life_years"):
            ReserveComponentGenerator.create(
                tenant_id=property_obj.tenant_id,
                reserve_study_id=study.id,
                useful_life_years=20,
                remaining_life_years=25,  # Invalid: exceeds useful life
            )

    def test_component_replacement_cost_validation(self):
        """Test that replacement cost must be positive."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        with pytest.raises(ValueError, match="replacement_cost must be positive"):
            ReserveComponentGenerator.create(
                tenant_id=property_obj.tenant_id,
                reserve_study_id=study.id,
                replacement_cost=Decimal("0.00"),  # Invalid
            )

    def test_calculate_inflated_cost(self):
        """Test calculating future replacement cost with inflation."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        component = ReserveComponentGenerator.create(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            replacement_cost=Decimal("100000.00"),
        )

        # Calculate cost 10 years from now at 3% inflation
        future_cost = component.calculate_inflated_cost(
            years_from_now=10,
            inflation_rate=Decimal("3.00")
        )

        # (1.03)^10 = 1.3439... so cost should be ~$134,390
        expected_range = (Decimal("134000.00"), Decimal("135000.00"))
        assert expected_range[0] <= future_cost <= expected_range[1]

    def test_create_components_for_all_categories(self):
        """Test creating components for each category."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        # Create a component for each category
        for category in ComponentCategory:
            component = ReserveComponentGenerator.create(
                tenant_id=property_obj.tenant_id,
                reserve_study_id=study.id,
                category=category,
            )
            assert component.category == category
            assert component.replacement_cost > Decimal("0.00")


class TestReserveScenarios:
    """Tests for reserve funding scenarios."""

    def test_create_baseline_scenario(self):
        """Test creating a baseline funding scenario."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            monthly_contribution=Decimal("5000.00"),
        )

        assert scenario.is_baseline is True
        assert scenario.monthly_contribution == Decimal("5000.00")
        assert scenario.name == "Baseline Funding"

    def test_create_aggressive_scenario(self):
        """Test creating an aggressive funding scenario."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        scenario = ReserveScenarioGenerator.create_aggressive(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        assert scenario.is_baseline is False
        assert scenario.contribution_increase_rate == Decimal("3.00")
        assert scenario.monthly_contribution > Decimal("0.00")

    def test_create_minimal_scenario(self):
        """Test creating a minimal funding scenario."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        scenario = ReserveScenarioGenerator.create_minimal(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        assert scenario.is_baseline is False
        assert scenario.monthly_contribution > Decimal("0.00")

    def test_scenario_monthly_contribution_validation(self):
        """Test that monthly contribution cannot be negative."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        with pytest.raises(ValueError, match="monthly_contribution cannot be negative"):
            ReserveScenarioGenerator.create(
                tenant_id=property_obj.tenant_id,
                reserve_study_id=study.id,
                monthly_contribution=Decimal("-1000.00"),  # Invalid
            )

    def test_scenario_one_time_contribution_validation(self):
        """Test that one-time contribution cannot be negative."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        with pytest.raises(ValueError, match="one_time_contribution cannot be negative"):
            ReserveScenarioGenerator.create(
                tenant_id=property_obj.tenant_id,
                reserve_study_id=study.id,
                one_time_contribution=Decimal("-5000.00"),  # Invalid
            )

    def test_scenario_contribution_increase_rate_validation(self):
        """Test that contribution increase rate must be reasonable."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        with pytest.raises(ValueError, match="contribution_increase_rate must be between 0 and 20 percent"):
            ReserveScenarioGenerator.create(
                tenant_id=property_obj.tenant_id,
                reserve_study_id=study.id,
                contribution_increase_rate=Decimal("25.00"),  # Too high
            )


class TestFundingProjections:
    """Tests for multi-year funding projections."""

    def test_create_single_year_projection(self):
        """Test creating a single year projection."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        projection = ReserveProjectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            scenario_id=scenario.id,
            year_number=1,
            calendar_year=2025,
            beginning_balance=Decimal("100000.00"),
            annual_contribution=Decimal("60000.00"),
            expenditures=Decimal("25000.00"),
            interest_rate=Decimal("1.50"),
        )

        assert projection.year_number == 1
        assert projection.beginning_balance == Decimal("100000.00")
        assert projection.annual_contribution == Decimal("60000.00")
        assert projection.expenditures == Decimal("25000.00")
        assert projection.interest_earned > Decimal("0.00")
        assert projection.ending_balance > projection.beginning_balance

    def test_projection_ending_balance_calculation(self):
        """Test that ending balance is calculated correctly."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        projection = ReserveProjectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            scenario_id=scenario.id,
            year_number=1,
            calendar_year=2025,
            beginning_balance=Decimal("100000.00"),
            annual_contribution=Decimal("60000.00"),
            expenditures=Decimal("25000.00"),
            interest_rate=Decimal("1.50"),
        )

        # Verify ending balance = beginning + contributions + interest - expenditures
        expected_ending = (
            projection.beginning_balance
            + projection.annual_contribution
            + projection.interest_earned
            - projection.expenditures
        )
        assert projection.ending_balance == expected_ending

    def test_projection_interest_earned_calculation(self):
        """Test that interest earned is calculated on average balance."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        projection = ReserveProjectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            scenario_id=scenario.id,
            year_number=1,
            calendar_year=2025,
            beginning_balance=Decimal("100000.00"),
            annual_contribution=Decimal("60000.00"),
            expenditures=Decimal("0.00"),
            interest_rate=Decimal("2.00"),
        )

        # Average balance = 100000 + 60000/2 = 130000
        # Interest = 130000 * 0.02 = 2600
        expected_interest = Decimal("2600.00")
        assert projection.interest_earned == expected_interest

    def test_multi_year_projection_sequence(self):
        """Test creating a sequence of projections across multiple years."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            monthly_contribution=Decimal("5000.00"),
        )

        projections = []
        balance = Decimal("100000.00")

        for year in range(1, 6):  # 5 years
            projection = ReserveProjectionGenerator.create(
                tenant_id=property_obj.tenant_id,
                scenario_id=scenario.id,
                year_number=year,
                calendar_year=2024 + year,
                beginning_balance=balance,
                annual_contribution=scenario.monthly_contribution * 12,
                expenditures=Decimal("20000.00"),
                interest_rate=study.interest_rate,
            )
            projections.append(projection)
            balance = projection.ending_balance

        assert len(projections) == 5
        # Balance should grow over time with positive contributions
        assert projections[-1].ending_balance > projections[0].beginning_balance


class TestFundingAdequacy:
    """Tests for funding adequacy calculations."""

    def test_well_funded_status(self):
        """Test identifying well-funded reserves (>100%)."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        # High balance, low expenditures = well funded
        projection = ReserveProjectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            scenario_id=scenario.id,
            year_number=1,
            calendar_year=2025,
            beginning_balance=Decimal("500000.00"),
            annual_contribution=Decimal("60000.00"),
            expenditures=Decimal("10000.00"),
            interest_rate=Decimal("1.50"),
        )

        assert projection.funding_status == FundingStatus.WELL_FUNDED
        assert projection.is_well_funded() is True

    def test_adequate_funding_status(self):
        """Test identifying adequate funding (70-100%)."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        # Moderate balance
        projection = ReserveProjectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            scenario_id=scenario.id,
            year_number=1,
            calendar_year=2025,
            beginning_balance=Decimal("100000.00"),
            annual_contribution=Decimal("60000.00"),
            expenditures=Decimal("50000.00"),
            interest_rate=Decimal("1.50"),
        )

        # Should be adequate or well funded
        assert projection.funding_status in [FundingStatus.ADEQUATE, FundingStatus.WELL_FUNDED]

    def test_underfunded_status(self):
        """Test identifying underfunded reserves (<70%)."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        # Low balance, high expenditures = underfunded
        projection = ReserveProjectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            scenario_id=scenario.id,
            year_number=1,
            calendar_year=2025,
            beginning_balance=Decimal("10000.00"),
            annual_contribution=Decimal("12000.00"),
            expenditures=Decimal("100000.00"),
            interest_rate=Decimal("1.50"),
        )

        assert projection.funding_status == FundingStatus.UNDERFUNDED
        assert projection.is_underfunded() is True

    def test_percent_funded_calculation(self):
        """Test percent funded ratio calculation."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        projection = ReserveProjectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            scenario_id=scenario.id,
            year_number=1,
            calendar_year=2025,
            beginning_balance=Decimal("100000.00"),
            annual_contribution=Decimal("60000.00"),
            expenditures=Decimal("50000.00"),
            interest_rate=Decimal("1.50"),
        )

        # Percent funded should be non-negative
        assert projection.percent_funded >= Decimal("0.00")


class TestReserveDataTypes:
    """Tests for proper data type usage in reserve planning."""

    def test_reserve_study_amounts_use_decimal(self):
        """Test that all reserve study amounts use Decimal, not float."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        assert isinstance(study.inflation_rate, Decimal)
        assert isinstance(study.interest_rate, Decimal)
        assert isinstance(study.current_reserve_balance, Decimal)

        # Verify exactly 2 decimal places for money amounts
        assert study.current_reserve_balance.as_tuple().exponent == -2

    def test_component_amounts_use_decimal(self):
        """Test that component costs use Decimal with 2 decimal places."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        component = ReserveComponentGenerator.create(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        assert isinstance(component.replacement_cost, Decimal)
        assert component.replacement_cost.as_tuple().exponent == -2

    def test_scenario_amounts_use_decimal(self):
        """Test that scenario contributions use Decimal with 2 decimal places."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        assert isinstance(scenario.monthly_contribution, Decimal)
        assert isinstance(scenario.one_time_contribution, Decimal)
        assert isinstance(scenario.contribution_increase_rate, Decimal)

        # Verify exactly 2 decimal places for money amounts
        assert scenario.monthly_contribution.as_tuple().exponent == -2
        assert scenario.one_time_contribution.as_tuple().exponent == -2

    def test_projection_amounts_use_decimal(self):
        """Test that projection amounts use Decimal with 2 decimal places."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        projection = ReserveProjectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            scenario_id=scenario.id,
            year_number=1,
            calendar_year=2025,
            beginning_balance=Decimal("100000.00"),
            annual_contribution=Decimal("60000.00"),
            expenditures=Decimal("25000.00"),
            interest_rate=Decimal("1.50"),
        )

        # Verify all money amounts use Decimal
        assert isinstance(projection.beginning_balance, Decimal)
        assert isinstance(projection.annual_contribution, Decimal)
        assert isinstance(projection.interest_earned, Decimal)
        assert isinstance(projection.expenditures, Decimal)
        assert isinstance(projection.ending_balance, Decimal)

        # Verify exactly 2 decimal places
        assert projection.beginning_balance.as_tuple().exponent == -2
        assert projection.annual_contribution.as_tuple().exponent == -2
        assert projection.interest_earned.as_tuple().exponent == -2
        assert projection.expenditures.as_tuple().exponent == -2
        assert projection.ending_balance.as_tuple().exponent == -2

    def test_reserve_dates_use_date_type(self):
        """Test that reserve dates use date, not datetime."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        assert isinstance(study.study_date, date)
        assert isinstance(study.created_at, date)

    def test_inflated_cost_preserves_precision(self):
        """Test that inflation calculations maintain decimal precision."""
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        component = ReserveComponentGenerator.create(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            replacement_cost=Decimal("100000.33"),
        )

        future_cost = component.calculate_inflated_cost(
            years_from_now=5,
            inflation_rate=Decimal("2.50")
        )

        # Verify result is Decimal with exact precision
        assert isinstance(future_cost, Decimal)
        assert future_cost.as_tuple().exponent == -2
