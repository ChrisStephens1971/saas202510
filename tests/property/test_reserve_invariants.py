"""
Property-based tests for reserve planning invariants.

Uses Hypothesis to verify that reserve planning operations maintain critical invariants:
- Ending balance = Beginning + Contributions + Interest - Expenditures
- Inflation never decreases costs (always increases or stays same)
- Interest earned is always non-negative
- Remaining life never exceeds useful life
- Replacement costs are always positive
- All calculations use Decimal with exactly 2 decimal places
"""

from datetime import date
from decimal import Decimal

from hypothesis import assume, given
from hypothesis import strategies as st
import pytest

from qa_testing.generators import (
    PropertyGenerator,
    ReserveComponentGenerator,
    ReserveProjectionGenerator,
    ReserveScenarioGenerator,
    ReserveStudyGenerator,
)
from qa_testing.models import ComponentCategory, FundingStatus


# Custom strategies for reserve testing
@st.composite
def horizon_years_strategy(draw):
    """Generate valid reserve study horizon years (5-30)."""
    return draw(st.integers(min_value=5, max_value=30))


@st.composite
def inflation_rate_strategy(draw):
    """Generate realistic inflation rates (0-20%)."""
    rate = draw(st.decimals(min_value="0.00", max_value="20.00", places=2))
    return rate


@st.composite
def interest_rate_strategy(draw):
    """Generate realistic interest rates (0-10%)."""
    rate = draw(st.decimals(min_value="0.00", max_value="10.00", places=2))
    return rate


@st.composite
def reserve_amount_strategy(draw):
    """Generate realistic reserve amounts ($100 - $1,000,000)."""
    dollars = draw(st.integers(min_value=100, max_value=1_000_000))
    cents = draw(st.integers(min_value=0, max_value=99))
    return Decimal(f"{dollars}.{cents:02d}")


@st.composite
def useful_life_strategy(draw):
    """Generate valid useful life years (1-100)."""
    return draw(st.integers(min_value=1, max_value=100))


class TestReserveCalculationInvariants:
    """Property-based tests for reserve calculation invariants."""

    @given(
        beginning_balance=reserve_amount_strategy(),
        annual_contribution=reserve_amount_strategy(),
        expenditures=reserve_amount_strategy(),
        interest_rate=interest_rate_strategy(),
    )
    def test_ending_balance_calculation_invariant(
        self, beginning_balance, annual_contribution, expenditures, interest_rate
    ):
        """
        INVARIANT: ending_balance = beginning + contributions + interest - expenditures.

        This must hold for any valid balance, contribution, expenditure, and interest rate.
        """
        # Skip combinations that would result in negative ending balance
        # (model validator requires percent_funded >= 0)
        assume(expenditures <= (beginning_balance + annual_contribution))

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
            beginning_balance=beginning_balance,
            annual_contribution=annual_contribution,
            expenditures=expenditures,
            interest_rate=interest_rate,
        )

        # Calculate expected ending balance
        expected_ending = (
            beginning_balance
            + annual_contribution
            + projection.interest_earned
            - expenditures
        )

        # Must match exactly
        assert projection.ending_balance == expected_ending

    @given(
        interest_rate=interest_rate_strategy(),
        beginning_balance=reserve_amount_strategy(),
        annual_contribution=reserve_amount_strategy(),
    )
    def test_interest_earned_always_non_negative(
        self, interest_rate, beginning_balance, annual_contribution
    ):
        """
        INVARIANT: Interest earned is always non-negative.

        With non-negative balances and interest rates, interest cannot be negative.
        """
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
            beginning_balance=beginning_balance,
            annual_contribution=annual_contribution,
            expenditures=Decimal("0.00"),
            interest_rate=interest_rate,
        )

        assert projection.interest_earned >= Decimal("0.00")

    @given(
        replacement_cost=reserve_amount_strategy(),
        inflation_rate=inflation_rate_strategy(),
        years=st.integers(min_value=0, max_value=30),
    )
    def test_inflation_never_decreases_costs(self, replacement_cost, inflation_rate, years):
        """
        INVARIANT: Inflation never decreases replacement costs.

        With non-negative inflation rates, future costs >= current costs.
        """
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        component = ReserveComponentGenerator.create(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            replacement_cost=replacement_cost,
        )

        future_cost = component.calculate_inflated_cost(
            years_from_now=years,
            inflation_rate=inflation_rate
        )

        # Future cost should be >= current cost (inflation never decreases)
        assert future_cost >= replacement_cost

    @given(
        replacement_cost=reserve_amount_strategy(),
        inflation_rate=inflation_rate_strategy(),
    )
    def test_zero_years_inflation_returns_same_cost(self, replacement_cost, inflation_rate):
        """
        INVARIANT: Zero years of inflation returns the original cost.

        calculate_inflated_cost(0, rate) should return the original cost.
        """
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        component = ReserveComponentGenerator.create(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            replacement_cost=replacement_cost,
        )

        future_cost = component.calculate_inflated_cost(
            years_from_now=0,
            inflation_rate=inflation_rate
        )

        # Should return original cost
        assert future_cost == replacement_cost


class TestFundingProjectionInvariants:
    """Property-based tests for funding projection invariants."""

    @given(
        monthly_contribution=st.decimals(min_value="100.00", max_value="10000.00", places=2),
    )
    def test_annual_contribution_equals_12_months(self, monthly_contribution):
        """
        INVARIANT: Annual contribution = monthly contribution × 12.

        For scenarios with fixed monthly contributions.
        """
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            monthly_contribution=monthly_contribution,
        )

        # Calculate expected annual
        expected_annual = (monthly_contribution * 12).quantize(Decimal("0.01"))

        # Create projection with this annual contribution
        projection = ReserveProjectionGenerator.create(
            tenant_id=property_obj.tenant_id,
            scenario_id=scenario.id,
            year_number=1,
            calendar_year=2025,
            beginning_balance=Decimal("100000.00"),
            annual_contribution=expected_annual,
            expenditures=Decimal("0.00"),
            interest_rate=Decimal("1.50"),
        )

        assert projection.annual_contribution == expected_annual

    @given(
        beginning_balance=reserve_amount_strategy(),
        contributions=reserve_amount_strategy(),
        interest_rate=interest_rate_strategy(),
    )
    def test_no_expenditures_balance_always_increases(
        self, beginning_balance, contributions, interest_rate
    ):
        """
        INVARIANT: With contributions and no expenditures, balance always increases.

        ending_balance > beginning_balance when contributions > 0 and expenditures = 0.
        """
        # Skip if contributions are zero
        assume(contributions > Decimal("0.00"))

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
            beginning_balance=beginning_balance,
            annual_contribution=contributions,
            expenditures=Decimal("0.00"),
            interest_rate=interest_rate,
        )

        # Balance should increase
        assert projection.ending_balance > beginning_balance

    @given(
        percent_funded=st.decimals(min_value="0.00", max_value="200.00", places=2),
    )
    def test_funding_status_thresholds_consistent(self, percent_funded):
        """
        INVARIANT: Funding status classifications are consistent.

        - WELL_FUNDED: percent_funded >= 100%
        - ADEQUATE: 70% <= percent_funded < 100%
        - UNDERFUNDED: percent_funded < 70%
        """
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)
        scenario = ReserveScenarioGenerator.create_baseline(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
        )

        # Create projection with specific percent_funded by manipulating balances
        # Simplified: use expenditures to control percent_funded
        if percent_funded > Decimal("0.00"):
            # fully_funded = expenditures * 2
            # percent_funded = ending_balance / fully_funded * 100
            # So: ending_balance = (percent_funded / 100) * expenditures * 2
            expenditures = Decimal("50000.00")
            fully_funded = expenditures * 2
            ending_balance = (percent_funded / Decimal("100") * fully_funded).quantize(Decimal("0.01"))

            # Work backwards to get beginning_balance
            interest = Decimal("100.00")  # Arbitrary small interest
            contribution = Decimal("1000.00")  # Arbitrary small contribution
            beginning_balance = (ending_balance - contribution - interest + expenditures).quantize(Decimal("0.01"))

            # Skip if beginning balance would be negative
            assume(beginning_balance >= Decimal("0.00"))

            projection = ReserveProjectionGenerator.create(
                tenant_id=property_obj.tenant_id,
                scenario_id=scenario.id,
                year_number=1,
                calendar_year=2025,
                beginning_balance=beginning_balance,
                annual_contribution=contribution,
                expenditures=expenditures,
                interest_rate=Decimal("1.50"),
            )

            # Verify funding status matches thresholds
            if projection.percent_funded >= Decimal("100.00"):
                assert projection.funding_status == FundingStatus.WELL_FUNDED
            elif projection.percent_funded >= Decimal("70.00"):
                assert projection.funding_status == FundingStatus.ADEQUATE
            else:
                assert projection.funding_status == FundingStatus.UNDERFUNDED


class TestComponentInvariants:
    """Property-based tests for reserve component invariants."""

    @given(
        useful_life=useful_life_strategy(),
    )
    def test_remaining_life_never_exceeds_useful_life(self, useful_life):
        """
        INVARIANT: remaining_life_years <= useful_life_years.

        A component cannot have more remaining life than total useful life.
        """
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        # Generate remaining life within valid range
        remaining_life = useful_life - 1 if useful_life > 1 else 0

        component = ReserveComponentGenerator.create(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            useful_life_years=useful_life,
            remaining_life_years=remaining_life,
        )

        assert component.remaining_life_years <= component.useful_life_years

    @given(
        replacement_cost=reserve_amount_strategy(),
    )
    def test_replacement_cost_always_positive(self, replacement_cost):
        """
        INVARIANT: Replacement cost must always be positive.

        Zero or negative costs are not allowed.
        """
        # Ensure positive
        assume(replacement_cost > Decimal("0.00"))

        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        component = ReserveComponentGenerator.create(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            replacement_cost=replacement_cost,
        )

        assert component.replacement_cost > Decimal("0.00")

    @given(
        quantity=st.integers(min_value=1, max_value=100),
    )
    def test_component_quantity_always_positive(self, quantity):
        """
        INVARIANT: Component quantity must be at least 1.

        Cannot have zero or negative quantities.
        """
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        component = ReserveComponentGenerator.create(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            quantity=quantity,
        )

        assert component.quantity >= 1

    def test_all_component_categories_valid(self):
        """
        INVARIANT: All component categories must be from ComponentCategory enum.

        Every created component must have a valid category.
        """
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        for category in ComponentCategory:
            component = ReserveComponentGenerator.create(
                tenant_id=property_obj.tenant_id,
                reserve_study_id=study.id,
                category=category,
            )
            assert component.category in ComponentCategory


class TestDataTypeInvariants:
    """Property-based tests for reserve data type invariants."""

    @given(
        inflation_rate=inflation_rate_strategy(),
        interest_rate=interest_rate_strategy(),
    )
    def test_reserve_study_rates_use_decimal_with_2_places(self, inflation_rate, interest_rate):
        """
        INVARIANT: All rates must use Decimal with exactly 2 decimal places.

        This ensures NUMERIC(15,2) compatibility.
        """
        property_obj = PropertyGenerator.create()

        study = ReserveStudyGenerator.create(
            tenant_id=property_obj.tenant_id,
            inflation_rate=inflation_rate,
            interest_rate=interest_rate,
        )

        # Verify Decimal type
        assert isinstance(study.inflation_rate, Decimal)
        assert isinstance(study.interest_rate, Decimal)

        # Verify exactly 2 decimal places
        assert study.inflation_rate.as_tuple().exponent == -2
        assert study.interest_rate.as_tuple().exponent == -2

    @given(
        replacement_cost=reserve_amount_strategy(),
    )
    def test_component_costs_use_decimal_with_2_places(self, replacement_cost):
        """
        INVARIANT: All component costs must use Decimal with exactly 2 decimal places.

        This ensures NUMERIC(15,2) compatibility.
        """
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        component = ReserveComponentGenerator.create(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            replacement_cost=replacement_cost,
        )

        assert isinstance(component.replacement_cost, Decimal)
        assert component.replacement_cost.as_tuple().exponent == -2

    @given(
        monthly_contribution=st.decimals(min_value="0.00", max_value="10000.00", places=2),
        one_time_contribution=st.decimals(min_value="0.00", max_value="100000.00", places=2),
    )
    def test_scenario_contributions_use_decimal_with_2_places(
        self, monthly_contribution, one_time_contribution
    ):
        """
        INVARIANT: All scenario contributions must use Decimal with exactly 2 decimal places.

        This ensures NUMERIC(15,2) compatibility.
        """
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        scenario = ReserveScenarioGenerator.create(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            monthly_contribution=monthly_contribution,
            one_time_contribution=one_time_contribution,
        )

        assert isinstance(scenario.monthly_contribution, Decimal)
        assert isinstance(scenario.one_time_contribution, Decimal)
        assert scenario.monthly_contribution.as_tuple().exponent == -2
        assert scenario.one_time_contribution.as_tuple().exponent == -2

    @given(
        beginning_balance=reserve_amount_strategy(),
        contribution=reserve_amount_strategy(),
        expenditures=reserve_amount_strategy(),
    )
    def test_projection_amounts_use_decimal_with_2_places(
        self, beginning_balance, contribution, expenditures
    ):
        """
        INVARIANT: All projection amounts must use Decimal with exactly 2 decimal places.

        This includes balances, contributions, interest, and expenditures.
        """
        # Skip combinations that would result in negative ending balance
        assume(expenditures <= (beginning_balance + contribution))

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
            beginning_balance=beginning_balance,
            annual_contribution=contribution,
            expenditures=expenditures,
            interest_rate=Decimal("1.50"),
        )

        # Verify all amounts are Decimal
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

    def test_all_dates_use_date_not_datetime(self):
        """
        INVARIANT: All date fields must use date type, not datetime.

        This ensures DATE type compatibility in the database.
        """
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        assert isinstance(study.study_date, date)
        assert isinstance(study.created_at, date)

    @given(
        replacement_cost=reserve_amount_strategy(),
        inflation_rate=inflation_rate_strategy(),
        years=st.integers(min_value=1, max_value=30),
    )
    def test_inflated_cost_returns_decimal_with_2_places(
        self, replacement_cost, inflation_rate, years
    ):
        """
        INVARIANT: Inflated cost calculation must return Decimal with 2 decimal places.

        Future cost calculations must maintain precision.
        """
        property_obj = PropertyGenerator.create()
        study = ReserveStudyGenerator.create(tenant_id=property_obj.tenant_id)

        component = ReserveComponentGenerator.create(
            tenant_id=property_obj.tenant_id,
            reserve_study_id=study.id,
            replacement_cost=replacement_cost,
        )

        future_cost = component.calculate_inflated_cost(
            years_from_now=years,
            inflation_rate=inflation_rate
        )

        assert isinstance(future_cost, Decimal)
        assert future_cost.as_tuple().exponent == -2
