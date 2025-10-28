"""Property and Unit models for HOA accounting system."""

from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base import AccountingDate, BaseTestModel, MoneyAmount


class PropertyType(str, Enum):
    """Types of properties."""

    CONDO = "condo"  # Condominium
    HOA = "hoa"  # Homeowners association
    TOWNHOME = "townhome"  # Townhome community
    APARTMENT = "apartment"  # Apartment complex


class FeeStructure(str, Enum):
    """Fee structure types."""

    FLAT = "flat"  # Same fee for all units
    TIERED = "tiered"  # Different fees by unit size/type
    SQUARE_FOOTAGE = "square_footage"  # Based on unit square footage
    PERCENTAGE = "percentage"  # Percentage of property value


class Property(BaseTestModel):
    """
    Property model representing an HOA or Condo community.

    This model is used for generating test data to validate:
    - Fee structures and assessments
    - Multi-unit financial tracking
    - Reserve fund allocations
    - Property-level reporting
    """

    # Multi-tenant isolation
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenant isolation")

    # Property information
    name: str = Field(..., min_length=1, max_length=200)
    address: str = Field(..., min_length=1, max_length=500)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)  # US state code
    zip_code: str = Field(..., min_length=5, max_length=10)

    # Property type and structure
    property_type: PropertyType = Field(
        default=PropertyType.CONDO,
        description="Type of property"
    )
    total_units: int = Field(..., ge=1, description="Total number of units")
    occupied_units: int = Field(..., ge=0, description="Number of occupied units")

    # Financial structure
    fee_structure: FeeStructure = Field(
        default=FeeStructure.FLAT,
        description="How fees are calculated"
    )
    monthly_fee_base: MoneyAmount = Field(
        ...,
        description="Base monthly fee (varies by fee_structure)"
    )

    # Fiscal year
    fiscal_year_start_month: int = Field(
        default=1,
        ge=1,
        le=12,
        description="Fiscal year start month (1=Jan, 12=Dec)"
    )

    # Management
    management_company: Optional[str] = Field(
        None,
        max_length=200,
        description="Property management company name"
    )

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} ({self.property_type.value}, {self.total_units} units)"


class Unit(BaseTestModel):
    """
    Unit model representing an individual unit within a property.

    This model is used for generating test data to validate:
    - Unit-level fee calculations
    - Individual member balances
    - Payment allocations
    """

    # Unit information
    unit_number: str = Field(..., min_length=1, max_length=50)
    building: Optional[str] = Field(None, max_length=50)
    floor: Optional[int] = Field(None, ge=0)

    # Unit details
    square_footage: Optional[int] = Field(None, ge=0)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[Decimal] = Field(None, ge=0)

    # Financial
    monthly_fee: MoneyAmount = Field(
        ...,
        description="Monthly HOA/condo fee for this unit"
    )
    special_assessment: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Current special assessment amount"
    )

    # Status
    is_occupied: bool = Field(default=True, description="Whether unit is occupied")
    is_delinquent: bool = Field(
        default=False,
        description="Whether unit has unpaid fees"
    )

    # Relationships
    property_id: UUID = Field(..., description="Associated property ID")
    current_member_id: Optional[UUID] = Field(
        None,
        description="Current member occupying this unit"
    )

    def __str__(self) -> str:
        """String representation."""
        building_str = f" Building {self.building}" if self.building else ""
        return f"Unit {self.unit_number}{building_str}"
