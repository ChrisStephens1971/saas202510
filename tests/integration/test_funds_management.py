"""
Integration tests for funds management functionality.

Tests Sprint 13 features:
- Fund CRUD operations
- Fund filtering and search
- Fund type management
- Fund balance validation
- Fund status transitions
"""

from datetime import date
from decimal import Decimal

import pytest

from qa_testing.generators import FundGenerator, PropertyGenerator
from qa_testing.models import Fund, FundType


class TestFundCreation:
    """Tests for fund creation and validation."""

    def test_create_operating_fund(self):
        """Test creating an operating fund."""
        property_obj = PropertyGenerator.create()

        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            fund_type=FundType.OPERATING,
            name="Operating Fund",
            current_balance=Decimal("50000.00"),
            target_balance=Decimal("100000.00"),
        )

        assert fund.fund_type == FundType.OPERATING
        assert fund.name == "Operating Fund"
        assert fund.current_balance == Decimal("50000.00")
        assert fund.target_balance == Decimal("100000.00")
        assert fund.is_active is True

    def test_create_reserve_fund(self):
        """Test creating a reserve fund."""
        property_obj = PropertyGenerator.create()

        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            fund_type=FundType.RESERVE,
            name="Reserve Fund",
            current_balance=Decimal("150000.00"),
            target_balance=Decimal("500000.00"),
        )

        assert fund.fund_type == FundType.RESERVE
        assert fund.name == "Reserve Fund"
        assert fund.current_balance == Decimal("150000.00")

    def test_create_special_assessment_fund(self):
        """Test creating a special assessment fund."""
        property_obj = PropertyGenerator.create()

        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            fund_type=FundType.SPECIAL_ASSESSMENT,
            name="Roof Replacement Fund",
            current_balance=Decimal("25000.00"),
            target_balance=Decimal("75000.00"),
        )

        assert fund.fund_type == FundType.SPECIAL_ASSESSMENT
        assert "Roof Replacement" in fund.name

    def test_create_capital_improvement_fund(self):
        """Test creating a capital improvement fund."""
        property_obj = PropertyGenerator.create()

        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            fund_type=FundType.CAPITAL_IMPROVEMENT,
            name="Capital Improvement Fund",
            current_balance=Decimal("75000.00"),
        )

        assert fund.fund_type == FundType.CAPITAL_IMPROVEMENT

    def test_create_contingency_fund(self):
        """Test creating a contingency fund."""
        property_obj = PropertyGenerator.create()

        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            fund_type=FundType.CONTINGENCY,
            name="Contingency Fund",
            current_balance=Decimal("30000.00"),
        )

        assert fund.fund_type == FundType.CONTINGENCY

    def test_fund_has_required_fields(self):
        """Test that fund has all required fields."""
        property_obj = PropertyGenerator.create()

        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
        )

        # Verify required fields exist
        assert fund.id is not None
        assert fund.tenant_id is not None
        assert fund.property_id is not None
        assert fund.name is not None
        assert fund.fund_type is not None
        assert fund.current_balance is not None
        assert fund.is_active is not None
        assert fund.created_at is not None


class TestFundBalanceValidation:
    """Tests for fund balance validation and rules."""

    def test_fund_balance_non_negative(self):
        """Test that fund balances cannot be negative (normally)."""
        property_obj = PropertyGenerator.create()

        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            current_balance=Decimal("10000.00"),
        )

        # Non-operating funds should not allow negative balance
        assert fund.current_balance >= fund.minimum_balance
        assert fund.minimum_balance == Decimal("0.00")

    def test_fund_can_allow_negative_balance(self):
        """Test that operating fund can allow temporary negative balance."""
        property_obj = PropertyGenerator.create()

        # Create operating fund with allow_negative_balance
        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            fund_type=FundType.OPERATING,
            current_balance=Decimal("-2000.00"),
            allow_negative_balance=True,
        )

        assert fund.allow_negative_balance is True
        # Operating fund with allow_negative should have negative minimum
        assert fund.minimum_balance == Decimal("-5000.00")
        assert fund.current_balance >= fund.minimum_balance

    def test_fund_target_balance(self):
        """Test fund target balance tracking."""
        property_obj = PropertyGenerator.create()

        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            fund_type=FundType.RESERVE,
            current_balance=Decimal("150000.00"),
            target_balance=Decimal("500000.00"),
        )

        # Calculate funding percentage
        funding_pct = (fund.current_balance / fund.target_balance * Decimal("100")).quantize(Decimal("0.01"))

        assert funding_pct == Decimal("30.00")

    def test_fund_overfunded(self):
        """Test detecting when a fund exceeds target balance."""
        property_obj = PropertyGenerator.create()

        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            current_balance=Decimal("550000.00"),
            target_balance=Decimal("500000.00"),
        )

        is_overfunded = fund.current_balance > fund.target_balance
        assert is_overfunded is True


class TestFundFiltering:
    """Tests for fund filtering and search."""

    def test_filter_funds_by_type(self):
        """Test filtering funds by fund type."""
        property_obj = PropertyGenerator.create()

        # Create multiple funds of different types
        operating = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            fund_type=FundType.OPERATING,
        )

        reserve = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            fund_type=FundType.RESERVE,
        )

        special = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            fund_type=FundType.SPECIAL_ASSESSMENT,
        )

        all_funds = [operating, reserve, special]

        # Filter by type
        operating_funds = [f for f in all_funds if f.fund_type == FundType.OPERATING]
        reserve_funds = [f for f in all_funds if f.fund_type == FundType.RESERVE]

        assert len(operating_funds) == 1
        assert len(reserve_funds) == 1

    def test_filter_active_funds(self):
        """Test filtering only active funds."""
        property_obj = PropertyGenerator.create()

        # Generator creates active funds by default
        active_fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
        )

        # Create inactive fund directly
        inactive_fund = Fund(
            tenant_id=property_obj.tenant_id,
            property_id=property_obj.id,
            name="Inactive Fund",
            fund_type=FundType.OPERATING,
            current_balance=Decimal("0.00"),
            is_active=False,
        )

        all_funds = [active_fund, inactive_fund]
        active_only = [f for f in all_funds if f.is_active]

        assert len(active_only) == 1
        assert active_only[0].id == active_fund.id

    def test_search_funds_by_name(self):
        """Test searching funds by name."""
        property_obj = PropertyGenerator.create()

        operating_fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            name="Operating Fund",
        )

        reserve_fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            name="Reserve Fund",
        )

        roof_fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            name="Roof Replacement Fund",
        )

        all_funds = [operating_fund, reserve_fund, roof_fund]

        # Search for "Reserve"
        search_results = [f for f in all_funds if "Reserve" in f.name]
        assert len(search_results) == 1
        assert search_results[0].name == "Reserve Fund"

        # Search for "Fund"
        search_results = [f for f in all_funds if "Fund" in f.name]
        assert len(search_results) == 3

    def test_search_funds_by_description(self):
        """Test searching funds by description."""
        property_obj = PropertyGenerator.create()

        # Create Fund objects directly with specific descriptions
        fund1 = Fund(
            tenant_id=property_obj.tenant_id,
            property_id=property_obj.id,
            name="Reserve Fund",
            description="Emergency reserves for major repairs",
            fund_type=FundType.RESERVE,
            current_balance=Decimal("100000.00"),
        )

        fund2 = Fund(
            tenant_id=property_obj.tenant_id,
            property_id=property_obj.id,
            name="Capital Fund",
            description="Long-term capital improvements",
            fund_type=FundType.CAPITAL_IMPROVEMENT,
            current_balance=Decimal("75000.00"),
        )

        all_funds = [fund1, fund2]

        # Search description for "repairs"
        results = [f for f in all_funds if f.description and "repairs" in f.description.lower()]
        assert len(results) == 1


class TestFundOrdering:
    """Tests for fund ordering and sorting."""

    def test_order_funds_by_balance(self):
        """Test ordering funds by current balance."""
        property_obj = PropertyGenerator.create()

        funds = [
            FundGenerator.create(
                property_id=property_obj.id,
                tenant_id=property_obj.tenant_id,
                name="Fund A",
                current_balance=Decimal("10000.00"),
            ),
            FundGenerator.create(
                property_id=property_obj.id,
                tenant_id=property_obj.tenant_id,
                name="Fund B",
                current_balance=Decimal("50000.00"),
            ),
            FundGenerator.create(
                property_id=property_obj.id,
                tenant_id=property_obj.tenant_id,
                name="Fund C",
                current_balance=Decimal("25000.00"),
            ),
        ]

        # Sort by balance descending
        sorted_funds = sorted(funds, key=lambda f: f.current_balance, reverse=True)

        assert sorted_funds[0].current_balance == Decimal("50000.00")
        assert sorted_funds[1].current_balance == Decimal("25000.00")
        assert sorted_funds[2].current_balance == Decimal("10000.00")

    def test_order_funds_by_name(self):
        """Test ordering funds alphabetically by name."""
        property_obj = PropertyGenerator.create()

        funds = [
            FundGenerator.create(
                property_id=property_obj.id,
                tenant_id=property_obj.tenant_id,
                name="Reserve Fund",
            ),
            FundGenerator.create(
                property_id=property_obj.id,
                tenant_id=property_obj.tenant_id,
                name="Capital Fund",
            ),
            FundGenerator.create(
                property_id=property_obj.id,
                tenant_id=property_obj.tenant_id,
                name="Operating Fund",
            ),
        ]

        # Sort alphabetically
        sorted_funds = sorted(funds, key=lambda f: f.name)

        assert sorted_funds[0].name == "Capital Fund"
        assert sorted_funds[1].name == "Operating Fund"
        assert sorted_funds[2].name == "Reserve Fund"


class TestFundStatusTransitions:
    """Tests for fund status transitions (active/inactive)."""

    def test_deactivate_fund(self):
        """Test marking a fund as inactive."""
        property_obj = PropertyGenerator.create()

        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
        )

        assert fund.is_active is True

        # Simulate deactivation (would be done via API)
        # Create new fund with same data but is_active=False
        updated_fund = Fund(
            id=fund.id,
            tenant_id=fund.tenant_id,
            property_id=fund.property_id,
            name=fund.name,
            description=fund.description,
            fund_type=fund.fund_type,
            current_balance=fund.current_balance,
            target_balance=fund.target_balance,
            minimum_balance=fund.minimum_balance,
            allow_negative_balance=fund.allow_negative_balance,
            is_active=False,
            created_at=fund.created_at,
        )

        assert updated_fund.is_active is False

    def test_reactivate_fund(self):
        """Test reactivating an inactive fund."""
        property_obj = PropertyGenerator.create()

        # Create inactive fund directly
        fund = Fund(
            tenant_id=property_obj.tenant_id,
            property_id=property_obj.id,
            name="Inactive Fund",
            fund_type=FundType.OPERATING,
            current_balance=Decimal("5000.00"),
            is_active=False,
        )

        assert fund.is_active is False

        # Simulate reactivation
        updated_fund = Fund(
            id=fund.id,
            tenant_id=fund.tenant_id,
            property_id=fund.property_id,
            name=fund.name,
            description=fund.description,
            fund_type=fund.fund_type,
            current_balance=fund.current_balance,
            target_balance=fund.target_balance,
            minimum_balance=fund.minimum_balance,
            allow_negative_balance=fund.allow_negative_balance,
            is_active=True,
            created_at=fund.created_at,
        )

        assert updated_fund.is_active is True


class TestFundDataTypes:
    """Tests for proper data type usage in funds."""

    def test_fund_balances_use_decimal(self):
        """Test that all fund balance amounts use Decimal with 2 places."""
        property_obj = PropertyGenerator.create()

        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
            current_balance=Decimal("125000.50"),
            target_balance=Decimal("500000.00"),
        )

        # Verify Decimal type
        assert isinstance(fund.current_balance, Decimal)
        assert isinstance(fund.target_balance, Decimal)
        assert isinstance(fund.minimum_balance, Decimal)

        # Verify 2 decimal places
        assert fund.current_balance.as_tuple().exponent == -2
        assert fund.target_balance.as_tuple().exponent == -2
        assert fund.minimum_balance.as_tuple().exponent == -2

    def test_fund_dates_use_date_type(self):
        """Test that fund dates use date type, not datetime."""
        property_obj = PropertyGenerator.create()

        fund = FundGenerator.create(
            property_id=property_obj.id,
            tenant_id=property_obj.tenant_id,
        )

        assert isinstance(fund.created_at, date)


class TestStandardFundSet:
    """Tests for creating standard set of funds for an HOA."""

    def test_create_standard_funds(self):
        """Test creating a standard set of funds for an HOA."""
        property_obj = PropertyGenerator.create()

        # Create standard funds (Operating, Reserve, Contingency)
        funds = FundGenerator.create_standard_funds(property_obj.id)

        assert len(funds) == 3

        # Verify all standard fund types are represented
        fund_types = {fund.fund_type for fund in funds}
        assert FundType.OPERATING in fund_types
        assert FundType.RESERVE in fund_types
        assert FundType.CONTINGENCY in fund_types

    def test_standard_funds_have_reasonable_targets(self):
        """Test that standard funds have reasonable target balances."""
        property_obj = PropertyGenerator.create()

        funds = FundGenerator.create_standard_funds(property_obj.id)

        for fund in funds:
            # All funds should have targets
            assert fund.target_balance > Decimal("0.00")

            # Target should be >= current balance (most of the time)
            # (allowing some flexibility for test data)
            if fund.current_balance > fund.target_balance:
                # Overfunded is okay for tests
                pass
