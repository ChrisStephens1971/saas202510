"""Property and Unit data generators for realistic HOA test data."""

from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from faker import Faker

from qa_testing.models import FeeStructure, Property, PropertyType, Unit

fake = Faker()


class PropertyGenerator:
    """
    Generator for creating realistic Property test data.

    Usage:
        # Create a property with default settings
        property = PropertyGenerator.create()

        # Create a condo with 50 units
        condo = PropertyGenerator.create(property_type=PropertyType.CONDO, total_units=50)
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        property_type: Optional[PropertyType] = None,
        total_units: Optional[int] = None,
        fee_structure: Optional[FeeStructure] = None,
        monthly_fee_base: Optional[Decimal] = None,
    ) -> Property:
        """
        Create a single Property with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            property_type: Type of property (random if not provided)
            total_units: Total number of units (random 10-200 if not provided)
            fee_structure: Fee structure (random if not provided)
            monthly_fee_base: Base monthly fee (random $200-$500 if not provided)

        Returns:
            Property instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Randomize property type if not provided
        if property_type is None:
            property_type = fake.random.choice(list(PropertyType))

        # Randomize total units if not provided
        if total_units is None:
            if property_type == PropertyType.CONDO:
                total_units = fake.random_int(min=20, max=200)
            elif property_type == PropertyType.HOA:
                total_units = fake.random_int(min=10, max=150)
            elif property_type == PropertyType.TOWNHOME:
                total_units = fake.random_int(min=15, max=100)
            else:  # APARTMENT
                total_units = fake.random_int(min=30, max=300)

        # Randomize occupied units (85-100% occupancy)
        occupancy_rate = fake.random.uniform(0.85, 1.0)
        occupied_units = int(total_units * occupancy_rate)

        # Randomize fee structure if not provided
        if fee_structure is None:
            # Distribution: 50% flat, 30% tiered, 15% square_footage, 5% percentage
            rand = fake.random.random()
            if rand < 0.50:
                fee_structure = FeeStructure.FLAT
            elif rand < 0.80:
                fee_structure = FeeStructure.TIERED
            elif rand < 0.95:
                fee_structure = FeeStructure.SQUARE_FOOTAGE
            else:
                fee_structure = FeeStructure.PERCENTAGE

        # Randomize monthly fee if not provided
        if monthly_fee_base is None:
            monthly_fee_base = Decimal(str(fake.random_int(min=200, max=500, step=25)))

        # Generate property name
        if property_type == PropertyType.CONDO:
            name = f"{fake.street_name()} Condominiums"
        elif property_type == PropertyType.HOA:
            name = f"{fake.street_name()} Homeowners Association"
        elif property_type == PropertyType.TOWNHOME:
            name = f"{fake.street_name()} Townhomes"
        else:  # APARTMENT
            name = f"{fake.street_name()} Apartments"

        return Property(
            tenant_id=tenant_id,
            name=name,
            address=fake.street_address(),
            city=fake.city(),
            state=fake.state_abbr(),
            zip_code=fake.zipcode(),
            property_type=property_type,
            total_units=total_units,
            occupied_units=occupied_units,
            fee_structure=fee_structure,
            monthly_fee_base=monthly_fee_base,
            fiscal_year_start_month=fake.random.choice([1, 7]),  # Jan or July
            management_company=fake.company() if fake.random.random() < 0.7 else None,
        )

    @staticmethod
    def create_batch(count: int, *, tenant_id: Optional[UUID] = None, **kwargs) -> list[Property]:
        """
        Create a batch of Properties.

        Args:
            count: Number of properties to create
            tenant_id: Tenant ID for all properties (generates one if not provided)
            **kwargs: Additional arguments passed to create()

        Returns:
            List of Property instances
        """
        tenant_id = tenant_id or uuid4()

        return [PropertyGenerator.create(tenant_id=tenant_id, **kwargs) for _ in range(count)]


class UnitGenerator:
    """
    Generator for creating realistic Unit test data.

    Usage:
        # Create a single unit
        unit = UnitGenerator.create(property_id=property.id)

        # Create units for a property
        units = UnitGenerator.create_for_property(property, num_units=50)
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        unit_number: Optional[str] = None,
        building: Optional[str] = None,
        monthly_fee: Optional[Decimal] = None,
        is_occupied: bool = True,
    ) -> Unit:
        """
        Create a single Unit with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            property_id: Associated property ID (required)
            unit_number: Unit number (generates one if not provided)
            building: Building identifier (optional)
            monthly_fee: Monthly fee (random $200-$600 if not provided)
            is_occupied: Whether unit is occupied

        Returns:
            Unit instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Generate unit number if not provided
        if unit_number is None:
            unit_number = str(fake.random_int(min=101, max=999))

        # Generate monthly fee if not provided
        if monthly_fee is None:
            monthly_fee = Decimal(str(fake.random_int(min=200, max=600, step=25)))

        # Generate unit details
        square_footage = fake.random_int(min=600, max=2500, step=50)
        bedrooms = fake.random.choice([1, 2, 2, 3, 3, 3, 4])  # More 2-3 bedrooms
        bathrooms = fake.random.choice([Decimal("1.0"), Decimal("1.5"), Decimal("2.0"), Decimal("2.5"), Decimal("3.0")])

        # Randomly assign special assessment (10% chance)
        special_assessment = Decimal("0.00")
        if fake.random.random() < 0.10:
            special_assessment = Decimal(str(fake.random_int(min=500, max=5000, step=100)))

        # Randomly mark as delinquent (5% chance)
        is_delinquent = fake.random.random() < 0.05

        return Unit(
            tenant_id=tenant_id,
            property_id=property_id,
            unit_number=unit_number,
            building=building,
            floor=fake.random_int(min=1, max=10) if fake.random.random() < 0.7 else None,
            square_footage=square_footage,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            monthly_fee=monthly_fee,
            special_assessment=special_assessment,
            is_occupied=is_occupied,
            is_delinquent=is_delinquent,
            current_member_id=uuid4() if is_occupied else None,
        )

    @staticmethod
    def create_for_property(
        property: Property,
        num_units: Optional[int] = None,
    ) -> list[Unit]:
        """
        Create units for a property with realistic numbering.

        Args:
            property: Property instance to create units for
            num_units: Number of units to create (uses property.total_units if not provided)

        Returns:
            List of Unit instances
        """
        num_units = num_units or property.total_units
        units = []

        # Determine numbering scheme based on property size
        if num_units <= 20:
            # Small property: sequential numbering (1-20)
            for i in range(1, num_units + 1):
                unit = UnitGenerator.create(
                    tenant_id=property.tenant_id,
                    property_id=property.id,
                    unit_number=str(i),
                    monthly_fee=property.monthly_fee_base,
                    is_occupied=i <= property.occupied_units,
                )
                units.append(unit)

        elif num_units <= 100:
            # Medium property: floor-based numbering (101-510)
            floors = (num_units // 10) + 1
            units_per_floor = 10
            unit_count = 0

            for floor in range(1, floors + 1):
                for unit_on_floor in range(1, units_per_floor + 1):
                    if unit_count >= num_units:
                        break

                    unit_number = f"{floor}{unit_on_floor:02d}"

                    # Vary monthly fee by floor (higher floors = higher fees)
                    floor_premium = Decimal(str((floor - 1) * 10))
                    monthly_fee = property.monthly_fee_base + floor_premium

                    unit = UnitGenerator.create(
                        tenant_id=property.tenant_id,
                        property_id=property.id,
                        unit_number=unit_number,
                        monthly_fee=monthly_fee,
                        is_occupied=unit_count < property.occupied_units,
                    )
                    units.append(unit)
                    unit_count += 1

                if unit_count >= num_units:
                    break

        else:
            # Large property: building + floor + unit numbering (A-101, B-205, etc.)
            buildings = ["A", "B", "C", "D", "E"]
            units_per_building = num_units // len(buildings)

            unit_count = 0
            for building in buildings:
                for floor in range(1, 11):  # Up to 10 floors per building
                    for unit_on_floor in range(1, 11):  # Up to 10 units per floor
                        if unit_count >= num_units:
                            break

                        unit_number = f"{floor}{unit_on_floor:02d}"

                        # Vary monthly fee by floor
                        floor_premium = Decimal(str((floor - 1) * 10))
                        monthly_fee = property.monthly_fee_base + floor_premium

                        unit = UnitGenerator.create(
                            tenant_id=property.tenant_id,
                            property_id=property.id,
                            unit_number=unit_number,
                            building=building,
                            monthly_fee=monthly_fee,
                            is_occupied=unit_count < property.occupied_units,
                        )
                        units.append(unit)
                        unit_count += 1

                    if unit_count >= num_units:
                        break

                if unit_count >= num_units:
                    break

        return units
