"""Reserve planning data generator for realistic HOA reserve study test data."""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from faker import Faker

from qa_testing.models import (
    ComponentCategory,
    FundingStatus,
    ReserveComponent,
    ReserveProjection,
    ReserveScenario,
    ReserveStudy,
)

fake = Faker()


class ReserveStudyGenerator:
    """
    Generator for creating realistic ReserveStudy test data.

    Usage:
        # Create a single reserve study
        study = ReserveStudyGenerator.create(tenant_id=tenant.id)

        # Create with components
        study, components = ReserveStudyGenerator.create_with_components(
            tenant_id=tenant.id,
            num_components=10
        )

        # Create complete study with scenarios
        study, components, scenarios = ReserveStudyGenerator.create_complete_study(
            tenant_id=tenant.id
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        name: Optional[str] = None,
        study_date: Optional[date] = None,
        horizon_years: Optional[int] = None,
        inflation_rate: Optional[Decimal] = None,
        interest_rate: Optional[Decimal] = None,
        current_reserve_balance: Optional[Decimal] = None,
        notes: Optional[str] = None,
        prepared_by: Optional[str] = None,
    ) -> ReserveStudy:
        """
        Create a single ReserveStudy with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            name: Study name (generates if not provided)
            study_date: Study date (defaults to today)
            horizon_years: Projection horizon (defaults to 20 years)
            inflation_rate: Annual inflation rate percentage (defaults to 2.5-4.0%)
            interest_rate: Annual interest rate percentage (defaults to 0.5-2.0%)
            current_reserve_balance: Current reserve balance (generates if not provided)
            notes: Study notes (generates if not provided)
            prepared_by: Preparer name (generates if not provided)

        Returns:
            ReserveStudy instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Default study date
        if study_date is None:
            study_date = date.today()

        # Default horizon (15-30 years)
        if horizon_years is None:
            horizon_years = fake.random.randint(15, 30)

        # Default inflation rate (2.5-4.0%)
        if inflation_rate is None:
            inflation_rate = Decimal(str(fake.random.uniform(2.5, 4.0))).quantize(Decimal("0.01"))

        # Default interest rate (0.5-2.0%)
        if interest_rate is None:
            interest_rate = Decimal(str(fake.random.uniform(0.5, 2.0))).quantize(Decimal("0.01"))

        # Default current balance ($50K-$500K)
        if current_reserve_balance is None:
            dollars = fake.random.randint(50000, 500000)
            cents = fake.random.randint(0, 99)
            current_reserve_balance = Decimal(f"{dollars}.{cents:02d}")

        # Generate name
        if name is None:
            name = f"{fake.company()} Reserve Study {study_date.year}"

        # Generate notes
        if notes is None:
            notes = ReserveStudyGenerator._generate_notes(horizon_years)

        # Generate preparer
        if prepared_by is None:
            prepared_by = f"{fake.company()} Reserve Specialists"

        return ReserveStudy(
            tenant_id=tenant_id,
            name=name,
            study_date=study_date,
            horizon_years=horizon_years,
            inflation_rate=inflation_rate,
            interest_rate=interest_rate,
            current_reserve_balance=current_reserve_balance,
            notes=notes,
            prepared_by=prepared_by,
        )

    @staticmethod
    def _generate_notes(horizon_years: int) -> str:
        """Generate realistic reserve study notes."""
        templates = [
            f"Full reserve study with {horizon_years}-year projection. "
            "Physical inspection conducted on all major components. "
            "Costs based on contractor quotes and industry standards.",

            f"{horizon_years}-year reserve analysis using component method. "
            "Study follows Community Associations Institute (CAI) guidelines. "
            "Inflation and interest rates based on historical averages.",

            f"Comprehensive {horizon_years}-year reserve study. "
            "All components inspected and photographed. "
            "Funding recommendations based on baseline scenario with 70% funded threshold.",
        ]
        return fake.random.choice(templates)


class ReserveComponentGenerator:
    """
    Generator for creating realistic ReserveComponent test data.

    Usage:
        # Create a roofing component
        component = ReserveComponentGenerator.create_roofing(
            study_id=study.id,
            tenant_id=tenant.id
        )

        # Create any random component
        component = ReserveComponentGenerator.create(
            study_id=study.id,
            tenant_id=tenant.id
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        reserve_study_id: UUID,
        name: Optional[str] = None,
        category: Optional[ComponentCategory] = None,
        quantity: Optional[int] = None,
        useful_life_years: Optional[int] = None,
        remaining_life_years: Optional[int] = None,
        replacement_cost: Optional[Decimal] = None,
        notes: Optional[str] = None,
    ) -> ReserveComponent:
        """
        Create a reserve component with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            reserve_study_id: Reserve study ID (required)
            name: Component name (generates based on category if not provided)
            category: Component category (random if not provided)
            quantity: Number of units (defaults to 1)
            useful_life_years: Total useful life (generates based on category)
            remaining_life_years: Remaining life (generates based on useful life)
            replacement_cost: Current replacement cost (generates based on category)
            notes: Component notes (generates if not provided)

        Returns:
            ReserveComponent instance
        """
        tenant_id = tenant_id or uuid4()

        # Select random category if not provided
        if category is None:
            category = fake.random.choice(list(ComponentCategory))

        # Generate name based on category
        if name is None:
            name = ReserveComponentGenerator._generate_name(category)

        # Default quantity
        if quantity is None:
            quantity = fake.random.randint(1, 5)

        # Generate useful life based on category
        if useful_life_years is None:
            useful_life_years = ReserveComponentGenerator._get_useful_life(category)

        # Generate remaining life (0 to useful_life_years)
        if remaining_life_years is None:
            remaining_life_years = fake.random.randint(0, useful_life_years)

        # Generate replacement cost based on category
        if replacement_cost is None:
            replacement_cost = ReserveComponentGenerator._get_replacement_cost(category, quantity)

        # Generate notes
        if notes is None:
            notes = f"{name} - Category: {category.value}. Quantity: {quantity}."

        return ReserveComponent(
            tenant_id=tenant_id,
            reserve_study_id=reserve_study_id,
            name=name,
            category=category,
            quantity=quantity,
            useful_life_years=useful_life_years,
            remaining_life_years=remaining_life_years,
            replacement_cost=replacement_cost,
            notes=notes,
        )

    @staticmethod
    def create_roofing(
        *,
        tenant_id: Optional[UUID] = None,
        reserve_study_id: UUID,
        name: Optional[str] = None,
    ) -> ReserveComponent:
        """Create a roofing component."""
        return ReserveComponentGenerator.create(
            tenant_id=tenant_id,
            reserve_study_id=reserve_study_id,
            name=name or "Main Building Roof",
            category=ComponentCategory.ROOFING,
            useful_life_years=25,
            remaining_life_years=fake.random.randint(0, 25),
            replacement_cost=Decimal(str(fake.random.randint(50000, 150000))).quantize(Decimal("0.01")),
        )

    @staticmethod
    def create_paving(
        *,
        tenant_id: Optional[UUID] = None,
        reserve_study_id: UUID,
        name: Optional[str] = None,
    ) -> ReserveComponent:
        """Create a paving component."""
        return ReserveComponentGenerator.create(
            tenant_id=tenant_id,
            reserve_study_id=reserve_study_id,
            name=name or "Parking Lot Asphalt",
            category=ComponentCategory.PAVING,
            useful_life_years=20,
            remaining_life_years=fake.random.randint(0, 20),
            replacement_cost=Decimal(str(fake.random.randint(75000, 200000))).quantize(Decimal("0.01")),
        )

    @staticmethod
    def create_painting(
        *,
        tenant_id: Optional[UUID] = None,
        reserve_study_id: UUID,
        name: Optional[str] = None,
    ) -> ReserveComponent:
        """Create a painting component."""
        return ReserveComponentGenerator.create(
            tenant_id=tenant_id,
            reserve_study_id=reserve_study_id,
            name=name or "Exterior Building Painting",
            category=ComponentCategory.PAINTING,
            useful_life_years=7,
            remaining_life_years=fake.random.randint(0, 7),
            replacement_cost=Decimal(str(fake.random.randint(15000, 50000))).quantize(Decimal("0.01")),
        )

    @staticmethod
    def create_pool(
        *,
        tenant_id: Optional[UUID] = None,
        reserve_study_id: UUID,
        name: Optional[str] = None,
    ) -> ReserveComponent:
        """Create a pool equipment component."""
        return ReserveComponentGenerator.create(
            tenant_id=tenant_id,
            reserve_study_id=reserve_study_id,
            name=name or "Pool Equipment and Resurfacing",
            category=ComponentCategory.POOL,
            useful_life_years=15,
            remaining_life_years=fake.random.randint(0, 15),
            replacement_cost=Decimal(str(fake.random.randint(30000, 100000))).quantize(Decimal("0.01")),
        )

    @staticmethod
    def _generate_name(category: ComponentCategory) -> str:
        """Generate realistic component name based on category."""
        names = {
            ComponentCategory.ROOFING: [
                "Main Building Roof",
                "Clubhouse Roof",
                "Garage Roof",
                "Building A Roof",
            ],
            ComponentCategory.PAVING: [
                "Parking Lot Asphalt",
                "Main Driveway",
                "Service Road Paving",
                "Walking Paths",
            ],
            ComponentCategory.PAINTING: [
                "Exterior Building Painting",
                "Fence Painting",
                "Trim and Fascia Painting",
                "Common Area Painting",
            ],
            ComponentCategory.STRUCTURAL: [
                "Building Foundation",
                "Retaining Walls",
                "Deck Structures",
                "Balcony Repairs",
            ],
            ComponentCategory.HVAC: [
                "Clubhouse HVAC System",
                "Common Area HVAC",
                "Office HVAC Units",
            ],
            ComponentCategory.PLUMBING: [
                "Main Water Lines",
                "Sewer Lines",
                "Pool Plumbing",
                "Irrigation System",
            ],
            ComponentCategory.ELECTRICAL: [
                "Common Area Lighting",
                "Electrical Panels",
                "Parking Lot Lights",
                "Security Lighting",
            ],
            ComponentCategory.POOL: [
                "Pool Equipment and Resurfacing",
                "Pool Heater",
                "Pool Pump and Filter",
                "Pool Deck",
            ],
            ComponentCategory.LANDSCAPE: [
                "Landscaping Renovation",
                "Tree Removal/Replacement",
                "Irrigation System",
                "Hardscaping",
            ],
            ComponentCategory.OTHER: [
                "Playground Equipment",
                "Signage",
                "Mailbox Kiosks",
                "Gate Systems",
            ],
        }
        return fake.random.choice(names.get(category, ["Miscellaneous Component"]))

    @staticmethod
    def _get_useful_life(category: ComponentCategory) -> int:
        """Get typical useful life for component category."""
        lifespans = {
            ComponentCategory.ROOFING: (20, 30),
            ComponentCategory.PAVING: (15, 25),
            ComponentCategory.PAINTING: (5, 10),
            ComponentCategory.STRUCTURAL: (40, 60),
            ComponentCategory.HVAC: (12, 20),
            ComponentCategory.PLUMBING: (25, 40),
            ComponentCategory.ELECTRICAL: (20, 35),
            ComponentCategory.POOL: (12, 20),
            ComponentCategory.LANDSCAPE: (10, 20),
            ComponentCategory.OTHER: (10, 25),
        }
        min_life, max_life = lifespans.get(category, (10, 20))
        return fake.random.randint(min_life, max_life)

    @staticmethod
    def _get_replacement_cost(category: ComponentCategory, quantity: int) -> Decimal:
        """Get realistic replacement cost for component category."""
        # Base costs per unit
        base_costs = {
            ComponentCategory.ROOFING: (50000, 150000),
            ComponentCategory.PAVING: (75000, 200000),
            ComponentCategory.PAINTING: (15000, 50000),
            ComponentCategory.STRUCTURAL: (100000, 300000),
            ComponentCategory.HVAC: (20000, 60000),
            ComponentCategory.PLUMBING: (30000, 100000),
            ComponentCategory.ELECTRICAL: (15000, 50000),
            ComponentCategory.POOL: (30000, 100000),
            ComponentCategory.LANDSCAPE: (20000, 80000),
            ComponentCategory.OTHER: (5000, 30000),
        }
        min_cost, max_cost = base_costs.get(category, (10000, 50000))
        base_cost = fake.random.randint(min_cost, max_cost)

        # Multiply by quantity (with diminishing returns for bulk)
        if quantity > 1:
            total_cost = base_cost * (1 + (quantity - 1) * 0.8)
        else:
            total_cost = base_cost

        return Decimal(str(int(total_cost))).quantize(Decimal("0.01"))


class ReserveScenarioGenerator:
    """
    Generator for creating realistic ReserveScenario test data.

    Usage:
        # Create baseline scenario
        scenario = ReserveScenarioGenerator.create_baseline(
            study_id=study.id,
            tenant_id=tenant.id
        )

        # Create aggressive funding scenario
        scenario = ReserveScenarioGenerator.create_aggressive(
            study_id=study.id,
            tenant_id=tenant.id
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        reserve_study_id: UUID,
        name: Optional[str] = None,
        monthly_contribution: Optional[Decimal] = None,
        one_time_contribution: Optional[Decimal] = None,
        contribution_increase_rate: Optional[Decimal] = None,
        is_baseline: bool = False,
        notes: Optional[str] = None,
    ) -> ReserveScenario:
        """
        Create a reserve funding scenario.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            reserve_study_id: Reserve study ID (required)
            name: Scenario name (generates if not provided)
            monthly_contribution: Monthly contribution amount (generates if not provided)
            one_time_contribution: One-time special assessment (defaults to 0)
            contribution_increase_rate: Annual increase rate (defaults to 0)
            is_baseline: Whether this is baseline scenario
            notes: Scenario notes (generates if not provided)

        Returns:
            ReserveScenario instance
        """
        tenant_id = tenant_id or uuid4()

        # Generate monthly contribution ($500-$10,000)
        if monthly_contribution is None:
            dollars = fake.random.randint(500, 10000)
            cents = fake.random.randint(0, 99)
            monthly_contribution = Decimal(f"{dollars}.{cents:02d}")

        # Default one-time contribution
        if one_time_contribution is None:
            one_time_contribution = Decimal("0.00")

        # Default contribution increase rate
        if contribution_increase_rate is None:
            contribution_increase_rate = Decimal("0.00")

        # Generate name
        if name is None:
            if is_baseline:
                name = "Baseline Funding"
            else:
                name = fake.random.choice([
                    "Aggressive Funding",
                    "Increased Contributions",
                    "Minimal Funding",
                    "Reduced Contributions",
                ])

        # Generate notes
        if notes is None:
            notes = f"Monthly contribution: ${monthly_contribution}. "
            if one_time_contribution > Decimal("0.00"):
                notes += f"One-time contribution: ${one_time_contribution}. "
            if contribution_increase_rate > Decimal("0.00"):
                notes += f"Annual increase: {contribution_increase_rate}%. "

        return ReserveScenario(
            tenant_id=tenant_id,
            reserve_study_id=reserve_study_id,
            name=name,
            monthly_contribution=monthly_contribution,
            one_time_contribution=one_time_contribution,
            contribution_increase_rate=contribution_increase_rate,
            is_baseline=is_baseline,
            notes=notes,
        )

    @staticmethod
    def create_baseline(
        *,
        tenant_id: Optional[UUID] = None,
        reserve_study_id: UUID,
        monthly_contribution: Optional[Decimal] = None,
    ) -> ReserveScenario:
        """Create a baseline (current) funding scenario."""
        return ReserveScenarioGenerator.create(
            tenant_id=tenant_id,
            reserve_study_id=reserve_study_id,
            name="Baseline Funding",
            monthly_contribution=monthly_contribution,
            is_baseline=True,
        )

    @staticmethod
    def create_aggressive(
        *,
        tenant_id: Optional[UUID] = None,
        reserve_study_id: UUID,
        monthly_contribution: Optional[Decimal] = None,
    ) -> ReserveScenario:
        """Create an aggressive funding scenario (higher contributions)."""
        if monthly_contribution is None:
            dollars = fake.random.randint(7000, 15000)
            cents = fake.random.randint(0, 99)
            monthly_contribution = Decimal(f"{dollars}.{cents:02d}")

        return ReserveScenarioGenerator.create(
            tenant_id=tenant_id,
            reserve_study_id=reserve_study_id,
            name="Aggressive Funding",
            monthly_contribution=monthly_contribution,
            contribution_increase_rate=Decimal("3.00"),
            is_baseline=False,
            notes="Increased monthly contributions with 3% annual increase to achieve full funding.",
        )

    @staticmethod
    def create_minimal(
        *,
        tenant_id: Optional[UUID] = None,
        reserve_study_id: UUID,
        monthly_contribution: Optional[Decimal] = None,
    ) -> ReserveScenario:
        """Create a minimal funding scenario (lower contributions)."""
        if monthly_contribution is None:
            dollars = fake.random.randint(500, 3000)
            cents = fake.random.randint(0, 99)
            monthly_contribution = Decimal(f"{dollars}.{cents:02d}")

        return ReserveScenarioGenerator.create(
            tenant_id=tenant_id,
            reserve_study_id=reserve_study_id,
            name="Minimal Funding",
            monthly_contribution=monthly_contribution,
            is_baseline=False,
            notes="Reduced monthly contributions. May require special assessments in future.",
        )


class ReserveProjectionGenerator:
    """
    Generator for creating realistic ReserveProjection test data.

    Usage:
        # Create a single year projection
        projection = ReserveProjectionGenerator.create(
            scenario_id=scenario.id,
            tenant_id=tenant.id,
            year_number=1,
            beginning_balance=Decimal("100000.00")
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        scenario_id: UUID,
        year_number: int,
        calendar_year: int,
        beginning_balance: Decimal,
        annual_contribution: Decimal,
        expenditures: Decimal,
        interest_rate: Decimal,
    ) -> ReserveProjection:
        """
        Create a reserve projection for a single year.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            scenario_id: Scenario ID (required)
            year_number: Year number (1, 2, 3, etc.)
            calendar_year: Calendar year
            beginning_balance: Starting balance
            annual_contribution: Total contributions for year
            expenditures: Total expenditures for year
            interest_rate: Annual interest rate as percentage

        Returns:
            ReserveProjection instance with calculated values
        """
        tenant_id = tenant_id or uuid4()

        # Calculate interest earned (simple interest on average balance)
        average_balance = beginning_balance + (annual_contribution / Decimal("2"))
        interest_earned = (average_balance * interest_rate / Decimal("100")).quantize(Decimal("0.01"))

        # Calculate ending balance
        ending_balance = (
            beginning_balance
            + annual_contribution
            + interest_earned
            - expenditures
        ).quantize(Decimal("0.01"))

        # Calculate percent funded (simplified: assume fully funded = 2x annual expenditures)
        fully_funded_balance = expenditures * Decimal("2")
        if fully_funded_balance > Decimal("0.00"):
            percent_funded = (ending_balance / fully_funded_balance * Decimal("100")).quantize(Decimal("0.01"))
        else:
            percent_funded = Decimal("100.00")

        # Determine funding status
        if percent_funded >= Decimal("100.00"):
            funding_status = FundingStatus.WELL_FUNDED
        elif percent_funded >= Decimal("70.00"):
            funding_status = FundingStatus.ADEQUATE
        else:
            funding_status = FundingStatus.UNDERFUNDED

        return ReserveProjection(
            tenant_id=tenant_id,
            scenario_id=scenario_id,
            year_number=year_number,
            calendar_year=calendar_year,
            beginning_balance=beginning_balance,
            annual_contribution=annual_contribution,
            interest_earned=interest_earned,
            expenditures=expenditures,
            ending_balance=ending_balance,
            percent_funded=percent_funded,
            funding_status=funding_status,
        )
