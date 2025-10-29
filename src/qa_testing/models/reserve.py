"""Reserve planning models for testing reserve study functionality."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from .base import AccountingDate, BaseTestModel, MoneyAmount


class ComponentCategory(str, Enum):
    """Reserve component categories."""

    ROOFING = "ROOFING"
    PAVING = "PAVING"
    PAINTING = "PAINTING"
    STRUCTURAL = "STRUCTURAL"
    HVAC = "HVAC"
    PLUMBING = "PLUMBING"
    ELECTRICAL = "ELECTRICAL"
    POOL = "POOL"
    LANDSCAPE = "LANDSCAPE"
    OTHER = "OTHER"


class FundingStatus(str, Enum):
    """Reserve funding adequacy status."""

    WELL_FUNDED = "WELL_FUNDED"  # >100% funded
    ADEQUATE = "ADEQUATE"  # 70-100% funded
    UNDERFUNDED = "UNDERFUNDED"  # <70% funded


class ReserveStudy(BaseTestModel):
    """
    Reserve study with multi-year capital expenditure forecasting.

    Tracks long-term planning for major repairs/replacements with:
    - 5-30 year projection horizon
    - Inflation adjustments
    - Interest earnings on reserve funds
    """

    name: str = Field(
        description="Study name (e.g., 'Oak Grove HOA 2025 Reserve Study')"
    )

    study_date: AccountingDate = Field(
        description="Date the reserve study was conducted"
    )

    horizon_years: int = Field(
        description="Projection horizon in years (typically 5-30 years)",
        ge=5,
        le=30,
    )

    inflation_rate: Decimal = Field(
        description="Annual inflation rate as percentage (e.g., 2.5 for 2.5%)"
    )

    interest_rate: Decimal = Field(
        description="Annual interest rate on reserves as percentage (e.g., 1.5 for 1.5%)"
    )

    current_reserve_balance: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Current reserve fund balance"
    )

    notes: str = Field(
        default="",
        description="Study methodology and assumptions"
    )

    prepared_by: Optional[str] = Field(
        default=None,
        description="Name of reserve specialist/company who prepared study"
    )

    @field_validator("horizon_years")
    @classmethod
    def validate_horizon_years(cls, v):
        """Ensure horizon is reasonable."""
        if v < 5 or v > 30:
            raise ValueError("horizon_years must be between 5 and 30")
        return v

    @field_validator("inflation_rate")
    @classmethod
    def validate_inflation_rate(cls, v):
        """Ensure inflation rate is reasonable."""
        # Convert to Decimal if needed and quantize
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        v = v.quantize(Decimal("0.01"))

        if v < Decimal("0.00") or v > Decimal("20.00"):
            raise ValueError("inflation_rate must be between 0 and 20 percent")
        return v

    @field_validator("interest_rate")
    @classmethod
    def validate_interest_rate(cls, v):
        """Ensure interest rate is reasonable."""
        # Convert to Decimal if needed and quantize
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        v = v.quantize(Decimal("0.01"))

        if v < Decimal("0.00") or v > Decimal("10.00"):
            raise ValueError("interest_rate must be between 0 and 10 percent")
        return v

    @field_validator("current_reserve_balance")
    @classmethod
    def validate_current_reserve_balance(cls, v):
        """Ensure current balance is non-negative."""
        if v < Decimal("0.00"):
            raise ValueError("current_reserve_balance cannot be negative")
        return v


class ReserveComponent(BaseTestModel):
    """
    Individual component tracked in reserve study.

    Examples: roof, pavement, pool equipment, painting, etc.
    """

    reserve_study_id: UUID = Field(
        description="Reserve study this component belongs to"
    )

    name: str = Field(
        description="Component name (e.g., 'Main Building Roof')"
    )

    category: ComponentCategory = Field(
        description="Component category"
    )

    quantity: int = Field(
        default=1,
        description="Number of units (e.g., 3 buildings, 5 roofs)",
        ge=1,
    )

    useful_life_years: int = Field(
        description="Total useful life in years",
        ge=1,
        le=100,
    )

    remaining_life_years: int = Field(
        description="Remaining useful life in years",
        ge=0,
        le=100,
    )

    replacement_cost: MoneyAmount = Field(
        description="Current replacement cost"
    )

    notes: str = Field(
        default="",
        description="Component details and assumptions"
    )

    @field_validator("remaining_life_years")
    @classmethod
    def validate_remaining_life(cls, v, info):
        """Ensure remaining life does not exceed useful life."""
        if "useful_life_years" in info.data:
            if v > info.data["useful_life_years"]:
                raise ValueError("remaining_life_years cannot exceed useful_life_years")
        return v

    @field_validator("replacement_cost")
    @classmethod
    def validate_replacement_cost(cls, v):
        """Ensure replacement cost is positive."""
        if v <= Decimal("0.00"):
            raise ValueError("replacement_cost must be positive")
        return v

    def calculate_inflated_cost(self, years_from_now: int, inflation_rate: Decimal) -> Decimal:
        """
        Calculate future replacement cost with inflation.

        Args:
            years_from_now: Number of years in the future
            inflation_rate: Annual inflation rate as percentage (e.g., 2.5 for 2.5%)

        Returns:
            Future cost adjusted for inflation
        """
        # Convert percentage to decimal (2.5% -> 0.025)
        rate = inflation_rate / Decimal("100")
        # FV = PV * (1 + r)^n
        multiplier = (Decimal("1.00") + rate) ** years_from_now
        future_cost = self.replacement_cost * multiplier
        return future_cost.quantize(Decimal("0.01"))


class ReserveScenario(BaseTestModel):
    """
    Funding scenario for reserve study.

    Different scenarios show impact of various funding strategies:
    - Baseline: Current funding level
    - Aggressive: Increased contributions
    - Minimal: Reduced contributions
    """

    reserve_study_id: UUID = Field(
        description="Reserve study this scenario belongs to"
    )

    name: str = Field(
        description="Scenario name (e.g., 'Baseline Funding', 'Increased Contributions')"
    )

    monthly_contribution: MoneyAmount = Field(
        description="Monthly contribution to reserve fund"
    )

    one_time_contribution: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="One-time special assessment or contribution"
    )

    contribution_increase_rate: Decimal = Field(
        default=Decimal("0.00"),
        description="Annual increase in contributions as percentage (e.g., 2.0 for 2.0%)"
    )

    is_baseline: bool = Field(
        default=False,
        description="Whether this is the baseline (current) scenario"
    )

    notes: str = Field(
        default="",
        description="Scenario assumptions and rationale"
    )

    @field_validator("monthly_contribution")
    @classmethod
    def validate_monthly_contribution(cls, v):
        """Ensure monthly contribution is non-negative."""
        if v < Decimal("0.00"):
            raise ValueError("monthly_contribution cannot be negative")
        return v

    @field_validator("one_time_contribution")
    @classmethod
    def validate_one_time_contribution(cls, v):
        """Ensure one-time contribution is non-negative."""
        if v < Decimal("0.00"):
            raise ValueError("one_time_contribution cannot be negative")
        return v

    @field_validator("contribution_increase_rate")
    @classmethod
    def validate_contribution_increase_rate(cls, v):
        """Ensure contribution increase rate is reasonable."""
        # Convert to Decimal if needed and quantize
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        v = v.quantize(Decimal("0.01"))

        if v < Decimal("0.00") or v > Decimal("20.00"):
            raise ValueError("contribution_increase_rate must be between 0 and 20 percent")
        return v


class ReserveProjection(BaseTestModel):
    """
    Single year projection in a reserve study scenario.

    Shows funding adequacy for a specific year.
    """

    scenario_id: UUID = Field(
        description="Scenario this projection belongs to"
    )

    year_number: int = Field(
        description="Year number (1 = first year, 2 = second year, etc.)",
        ge=1,
    )

    calendar_year: int = Field(
        description="Calendar year for this projection"
    )

    beginning_balance: MoneyAmount = Field(
        description="Reserve balance at start of year"
    )

    annual_contribution: MoneyAmount = Field(
        description="Total contributions for the year"
    )

    interest_earned: MoneyAmount = Field(
        description="Interest earned on reserves"
    )

    expenditures: MoneyAmount = Field(
        description="Total expenditures for the year"
    )

    ending_balance: MoneyAmount = Field(
        description="Reserve balance at end of year"
    )

    percent_funded: Decimal = Field(
        description="Percent funded ratio (actual / fully funded)"
    )

    funding_status: FundingStatus = Field(
        description="Funding adequacy status"
    )

    @field_validator("percent_funded")
    @classmethod
    def validate_percent_funded(cls, v):
        """Ensure percent funded is non-negative."""
        # Convert to Decimal if needed and quantize
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        v = v.quantize(Decimal("0.01"))

        if v < Decimal("0.00"):
            raise ValueError("percent_funded cannot be negative")
        return v

    @field_validator("ending_balance")
    @classmethod
    def validate_ending_balance_calculation(cls, v, info):
        """Verify ending balance calculation is correct."""
        data = info.data
        if all(k in data for k in ["beginning_balance", "annual_contribution", "interest_earned", "expenditures"]):
            expected = (
                data["beginning_balance"]
                + data["annual_contribution"]
                + data["interest_earned"]
                - data["expenditures"]
            )
            # Allow small rounding differences
            if abs(v - expected) > Decimal("0.01"):
                raise ValueError(
                    f"ending_balance {v} does not match calculated value {expected}"
                )
        return v

    def is_well_funded(self) -> bool:
        """Check if reserves are well funded (>100%)."""
        return self.funding_status == FundingStatus.WELL_FUNDED

    def is_underfunded(self) -> bool:
        """Check if reserves are underfunded (<70%)."""
        return self.funding_status == FundingStatus.UNDERFUNDED
