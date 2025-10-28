"""Fund data generator for realistic HOA fund test data."""

from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from faker import Faker

from qa_testing.models import Fund, FundType

fake = Faker()


class FundGenerator:
    """
    Generator for creating realistic Fund test data.

    Usage:
        # Create a single fund
        fund = FundGenerator.create(property_id=property.id)

        # Create all standard funds for a property
        funds = FundGenerator.create_standard_funds(property.id)
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        fund_type: Optional[FundType] = None,
        name: Optional[str] = None,
        current_balance: Optional[Decimal] = None,
        target_balance: Optional[Decimal] = None,
        allow_negative_balance: bool = False,
    ) -> Fund:
        """
        Create a single Fund with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            property_id: Associated property ID (required)
            fund_type: Type of fund (random if not provided)
            name: Fund name (generates based on type if not provided)
            current_balance: Current balance (random based on type if not provided)
            target_balance: Target balance (calculated if not provided)
            allow_negative_balance: Whether fund can go negative

        Returns:
            Fund instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Randomize fund type if not provided
        if fund_type is None:
            fund_type = fake.random.choice(list(FundType))

        # Generate name based on fund type if not provided
        if name is None:
            name = FundGenerator._generate_fund_name(fund_type)

        # Generate realistic balances based on fund type
        if current_balance is None or target_balance is None:
            gen_current, gen_target = FundGenerator._generate_balances(fund_type)
            current_balance = current_balance or gen_current
            target_balance = target_balance or gen_target

        # Set minimum balance (usually 0, but operating fund might allow small negative)
        if fund_type == FundType.OPERATING and allow_negative_balance:
            minimum_balance = Decimal("-5000.00")  # Allow small temporary overdraft
        else:
            minimum_balance = Decimal("0.00")

        # Generate description
        description = FundGenerator._generate_description(fund_type)

        return Fund(
            tenant_id=tenant_id,
            property_id=property_id,
            name=name,
            description=description,
            fund_type=fund_type,
            current_balance=current_balance,
            target_balance=target_balance,
            minimum_balance=minimum_balance,
            allow_negative_balance=allow_negative_balance,
            is_active=True,
        )

    @staticmethod
    def _generate_fund_name(fund_type: FundType) -> str:
        """Generate a fund name based on type."""
        names = {
            FundType.OPERATING: "Operating Fund",
            FundType.RESERVE: "Reserve Fund",
            FundType.SPECIAL_ASSESSMENT: f"Special Assessment - {fake.word().capitalize()} {fake.word().capitalize()}",
            FundType.CAPITAL_IMPROVEMENT: "Capital Improvement Fund",
            FundType.CONTINGENCY: "Contingency Fund",
        }
        return names.get(fund_type, "General Fund")

    @staticmethod
    def _generate_description(fund_type: FundType) -> str:
        """Generate a fund description based on type."""
        descriptions = {
            FundType.OPERATING: "Day-to-day operating expenses including utilities, maintenance, and insurance",
            FundType.RESERVE: "Long-term reserve for capital improvements and major repairs",
            FundType.SPECIAL_ASSESSMENT: "Special assessment fund for specific projects or expenses",
            FundType.CAPITAL_IMPROVEMENT: "Fund for major capital improvements and infrastructure upgrades",
            FundType.CONTINGENCY: "Emergency contingency fund for unexpected expenses",
        }
        return descriptions.get(fund_type, "General purpose fund")

    @staticmethod
    def _generate_balances(fund_type: FundType) -> tuple[Decimal, Optional[Decimal]]:
        """
        Generate realistic balance and target based on fund type.

        Returns:
            Tuple of (current_balance, target_balance)
        """
        if fund_type == FundType.OPERATING:
            # Operating fund: typically 2-6 months of expenses
            # Current: $20K - $150K
            current = Decimal(str(fake.random_int(min=20000, max=150000, step=5000)))
            # Target: 3-6 months (assume $25K/month expenses)
            target = Decimal(str(fake.random_int(min=75000, max=150000, step=10000)))

        elif fund_type == FundType.RESERVE:
            # Reserve fund: typically building up to major goals
            # Current: $50K - $500K
            current = Decimal(str(fake.random_int(min=50000, max=500000, step=10000)))
            # Target: Usually much higher (e.g., roof replacement $300K+)
            target = Decimal(str(fake.random_int(min=300000, max=1000000, step=50000)))

        elif fund_type == FundType.SPECIAL_ASSESSMENT:
            # Special assessment: collecting for specific project
            # Current: $10K - $100K
            current = Decimal(str(fake.random_int(min=10000, max=100000, step=5000)))
            # Target: Project cost
            target = Decimal(str(fake.random_int(min=50000, max=200000, step=10000)))

        elif fund_type == FundType.CAPITAL_IMPROVEMENT:
            # Capital improvement: similar to reserve
            # Current: $30K - $250K
            current = Decimal(str(fake.random_int(min=30000, max=250000, step=10000)))
            # Target: Major improvement goals
            target = Decimal(str(fake.random_int(min=200000, max=800000, step=50000)))

        elif fund_type == FundType.CONTINGENCY:
            # Contingency: smaller emergency fund
            # Current: $10K - $50K
            current = Decimal(str(fake.random_int(min=10000, max=50000, step=5000)))
            # Target: 10-20% of annual budget
            target = Decimal(str(fake.random_int(min=25000, max=75000, step=5000)))

        else:
            # Default
            current = Decimal(str(fake.random_int(min=10000, max=100000, step=5000)))
            target = None

        # Randomly underfund some funds (60% of target on average)
        if target and fake.random.random() < 0.7:
            funding_percentage = fake.random.uniform(0.4, 0.9)
            current = (target * Decimal(str(funding_percentage))).quantize(Decimal("0.01"))

        return current, target

    @staticmethod
    def create_standard_funds(
        property_id: UUID,
        tenant_id: Optional[UUID] = None,
    ) -> list[Fund]:
        """
        Create the standard set of funds for an HOA property.

        Standard funds:
        - Operating Fund
        - Reserve Fund
        - Contingency Fund

        Args:
            property_id: Property ID
            tenant_id: Tenant ID (generates one if not provided)

        Returns:
            List of Fund instances
        """
        tenant_id = tenant_id or uuid4()

        return [
            FundGenerator.create(
                tenant_id=tenant_id,
                property_id=property_id,
                fund_type=FundType.OPERATING,
                allow_negative_balance=True,  # Operating fund can temporarily go negative
            ),
            FundGenerator.create(
                tenant_id=tenant_id,
                property_id=property_id,
                fund_type=FundType.RESERVE,
            ),
            FundGenerator.create(
                tenant_id=tenant_id,
                property_id=property_id,
                fund_type=FundType.CONTINGENCY,
            ),
        ]

    @staticmethod
    def create_batch(
        count: int,
        *,
        property_id: UUID,
        tenant_id: Optional[UUID] = None,
        **kwargs
    ) -> list[Fund]:
        """
        Create a batch of Funds.

        Args:
            count: Number of funds to create
            property_id: Property ID for all funds
            tenant_id: Tenant ID for all funds (generates one if not provided)
            **kwargs: Additional arguments passed to create()

        Returns:
            List of Fund instances
        """
        tenant_id = tenant_id or uuid4()

        return [
            FundGenerator.create(
                tenant_id=tenant_id,
                property_id=property_id,
                **kwargs
            )
            for _ in range(count)
        ]
