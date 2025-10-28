"""
Database fixtures for testing.

These fixtures populate the test database with realistic HOA data
for integration testing.
"""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from qa_testing.database.connection import TestDatabase
from qa_testing.generators import (
    FundGenerator,
    LedgerEntryGenerator,
    MemberGenerator,
    PropertyGenerator,
    TransactionGenerator,
    UnitGenerator,
)
from qa_testing.models import Fund, LedgerEntry, Member, Property, Transaction, Unit


def create_test_schema(tenant_id: UUID) -> str:
    """
    Create test schema for a tenant.

    Args:
        tenant_id: Tenant UUID

    Returns:
        Schema name
    """
    test_db = TestDatabase()
    return test_db.create_schema(tenant_id)


def drop_test_schema(tenant_id: UUID) -> None:
    """
    Drop test schema for cleanup.

    Args:
        tenant_id: Tenant UUID
    """
    test_db = TestDatabase()
    test_db.drop_schema(tenant_id)


def seed_test_data(
    tenant_id: UUID,
    *,
    num_properties: int = 1,
    num_units_per_property: int = 10,
    num_members: Optional[int] = None,
) -> dict:
    """
    Seed test database with realistic HOA data.

    Args:
        tenant_id: Tenant UUID
        num_properties: Number of properties to create
        num_units_per_property: Units per property
        num_members: Number of members (defaults to num_units)

    Returns:
        Dictionary with created entities:
        {
            'properties': [Property, ...],
            'units': [Unit, ...],
            'members': [Member, ...],
            'funds': [Fund, ...],
        }
    """
    num_members = num_members or num_units_per_property

    # Generate test data
    properties = PropertyGenerator.create_batch(
        num_properties,
        tenant_id=tenant_id,
    )

    all_units = []
    all_members = []
    all_funds = []

    for property in properties:
        # Create units for property
        units = UnitGenerator.create_for_property(
            property,
            num_units=num_units_per_property,
        )
        all_units.extend(units)

        # Create members for units
        for unit in units[:num_members]:
            member = MemberGenerator.create(
                tenant_id=tenant_id,
                property_id=property.id,
                unit_id=unit.id,
            )
            all_members.append(member)

        # Create standard funds for property
        funds = FundGenerator.create_standard_funds(
            property.id,
            tenant_id=tenant_id,
        )
        all_funds.extend(funds)

    # Insert into database
    test_db = TestDatabase()
    schema_name = f"tenant_{tenant_id.hex}"

    with test_db.connect() as conn:
        cursor = conn.cursor()

        # Insert properties
        for property in properties:
            cursor.execute(f"""
                INSERT INTO {schema_name}.properties (
                    id, tenant_id, name, address, city, state, zip_code,
                    property_type, total_units, occupied_units, fee_structure,
                    monthly_fee_base, fiscal_year_start_month, management_company
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                property.id, property.tenant_id, property.name, property.address,
                property.city, property.state, property.zip_code, property.property_type.value,
                property.total_units, property.occupied_units, property.fee_structure.value,
                property.monthly_fee_base, property.fiscal_year_start_month,
                property.management_company
            ))

        # Insert units
        for unit in all_units:
            cursor.execute(f"""
                INSERT INTO {schema_name}.units (
                    id, tenant_id, property_id, unit_number, building, floor,
                    square_footage, bedrooms, bathrooms, monthly_fee,
                    special_assessment, is_occupied, is_delinquent, current_member_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                unit.id, unit.tenant_id, unit.property_id, unit.unit_number,
                unit.building, unit.floor, unit.square_footage, unit.bedrooms,
                unit.bathrooms, unit.monthly_fee, unit.special_assessment,
                unit.is_occupied, unit.is_delinquent, unit.current_member_id
            ))

        # Insert members
        for member in all_members:
            cursor.execute(f"""
                INSERT INTO {schema_name}.members (
                    id, tenant_id, first_name, last_name, email, phone,
                    member_type, is_active, current_balance, total_paid,
                    total_owed, payment_history, move_in_date, move_out_date,
                    unit_id, property_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                member.id, member.tenant_id, member.first_name, member.last_name,
                member.email, member.phone, member.member_type.value, member.is_active,
                member.current_balance, member.total_paid, member.total_owed,
                member.payment_history.value, member.move_in_date, member.move_out_date,
                member.unit_id, member.property_id
            ))

        # Insert funds
        for fund in all_funds:
            cursor.execute(f"""
                INSERT INTO {schema_name}.funds (
                    id, tenant_id, property_id, name, description, fund_type,
                    current_balance, target_balance, minimum_balance,
                    allow_negative_balance, is_active
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                fund.id, fund.tenant_id, fund.property_id, fund.name,
                fund.description, fund.fund_type.value, fund.current_balance,
                fund.target_balance, fund.minimum_balance,
                fund.allow_negative_balance, fund.is_active
            ))

    return {
        'properties': properties,
        'units': all_units,
        'members': all_members,
        'funds': all_funds,
    }


def insert_transaction(
    tenant_id: UUID,
    transaction: Transaction,
) -> None:
    """
    Insert a transaction into the database.

    Args:
        tenant_id: Tenant UUID
        transaction: Transaction to insert
    """
    test_db = TestDatabase()
    schema_name = f"tenant_{tenant_id.hex}"

    with test_db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {schema_name}.transactions (
                id, tenant_id, property_id, transaction_type, description,
                transaction_date, posted_date, amount, is_posted, is_void,
                member_id, unit_id, fund_id, check_number, bank_reference,
                plaid_transaction_id, notes
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            transaction.id, transaction.tenant_id, transaction.property_id,
            transaction.transaction_type.value, transaction.description,
            transaction.transaction_date, transaction.posted_date, transaction.amount,
            transaction.is_posted, transaction.is_void, transaction.member_id,
            transaction.unit_id, transaction.fund_id, transaction.check_number,
            transaction.bank_reference, transaction.plaid_transaction_id, transaction.notes
        ))


def insert_ledger_entry(
    tenant_id: UUID,
    entry: LedgerEntry,
) -> None:
    """
    Insert a ledger entry into the database.

    Args:
        tenant_id: Tenant UUID
        entry: Ledger entry to insert
    """
    test_db = TestDatabase()
    schema_name = f"tenant_{tenant_id.hex}"

    with test_db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {schema_name}.ledger_entries (
                id, tenant_id, property_id, transaction_id, fund_id,
                entry_date, description, amount, is_debit, account_code,
                account_name, is_reversing, reverses_entry_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            entry.id, entry.tenant_id, entry.property_id, entry.transaction_id,
            entry.fund_id, entry.entry_date, entry.description, entry.amount,
            entry.is_debit, entry.account_code, entry.account_name,
            entry.is_reversing, entry.reverses_entry_id
        ))


def get_member_balance(tenant_id: UUID, member_id: UUID) -> Decimal:
    """
    Get current balance for a member from database.

    Args:
        tenant_id: Tenant UUID
        member_id: Member UUID

    Returns:
        Current balance
    """
    test_db = TestDatabase()
    schema_name = f"tenant_{tenant_id.hex}"

    with test_db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT current_balance FROM {schema_name}.members WHERE id = %s",
            (member_id,)
        )
        result = cursor.fetchone()
        return result[0] if result else Decimal("0.00")


def update_member_balance(tenant_id: UUID, member_id: UUID, new_balance: Decimal) -> None:
    """
    Update member balance in database.

    Args:
        tenant_id: Tenant UUID
        member_id: Member UUID
        new_balance: New balance
    """
    test_db = TestDatabase()
    schema_name = f"tenant_{tenant_id.hex}"

    with test_db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE {schema_name}.members SET current_balance = %s WHERE id = %s",
            (new_balance, member_id)
        )
