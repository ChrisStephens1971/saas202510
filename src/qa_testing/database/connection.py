"""
Database connection utilities for testing.

This module provides utilities for connecting to the test PostgreSQL database
with schema-per-tenant isolation.
"""

import os
from contextlib import contextmanager
from typing import Optional
from uuid import UUID

import psycopg
from psycopg import Connection


class TestDatabase:
    """
    Test database connection manager with schema-per-tenant support.

    This matches the architecture of saas202509 where each tenant
    gets an isolated schema in PostgreSQL.
    """

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize test database connection.

        Args:
            connection_string: PostgreSQL connection string
                              (defaults to environment variable TEST_DATABASE_URL)
        """
        self.connection_string = connection_string or os.getenv(
            "TEST_DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5410/qa_testing"
        )

    @contextmanager
    def connect(self):
        """
        Connect to database with context manager.

        Usage:
            with test_db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
        """
        conn = psycopg.connect(self.connection_string)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_schema(self, tenant_id: UUID) -> str:
        """
        Create a schema for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Schema name (tenant_{uuid})
        """
        schema_name = f"tenant_{tenant_id.hex}"

        with self.connect() as conn:
            cursor = conn.cursor()

            # Create schema
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")

            # Create tables in schema
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.members (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    phone VARCHAR(20),
                    member_type VARCHAR(50) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    current_balance NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
                    total_paid NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
                    total_owed NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
                    payment_history VARCHAR(50),
                    move_in_date DATE NOT NULL,
                    move_out_date DATE,
                    unit_id UUID NOT NULL,
                    property_id UUID NOT NULL,
                    created_at DATE NOT NULL DEFAULT CURRENT_DATE
                );

                CREATE TABLE IF NOT EXISTS {schema_name}.properties (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    address VARCHAR(500) NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    state VARCHAR(2) NOT NULL,
                    zip_code VARCHAR(10) NOT NULL,
                    property_type VARCHAR(50) NOT NULL,
                    total_units INTEGER NOT NULL,
                    occupied_units INTEGER NOT NULL,
                    fee_structure VARCHAR(50) NOT NULL,
                    monthly_fee_base NUMERIC(15, 2) NOT NULL,
                    fiscal_year_start_month INTEGER NOT NULL DEFAULT 1,
                    management_company VARCHAR(200),
                    created_at DATE NOT NULL DEFAULT CURRENT_DATE
                );

                CREATE TABLE IF NOT EXISTS {schema_name}.units (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    property_id UUID NOT NULL,
                    unit_number VARCHAR(50) NOT NULL,
                    building VARCHAR(50),
                    floor INTEGER,
                    square_footage INTEGER,
                    bedrooms INTEGER,
                    bathrooms NUMERIC(3, 1),
                    monthly_fee NUMERIC(15, 2) NOT NULL,
                    special_assessment NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
                    is_occupied BOOLEAN DEFAULT TRUE,
                    is_delinquent BOOLEAN DEFAULT FALSE,
                    current_member_id UUID,
                    created_at DATE NOT NULL DEFAULT CURRENT_DATE
                );

                CREATE TABLE IF NOT EXISTS {schema_name}.funds (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    property_id UUID NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    fund_type VARCHAR(50) NOT NULL,
                    current_balance NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
                    target_balance NUMERIC(15, 2),
                    minimum_balance NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
                    allow_negative_balance BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at DATE NOT NULL DEFAULT CURRENT_DATE
                );

                CREATE TABLE IF NOT EXISTS {schema_name}.transactions (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    property_id UUID NOT NULL,
                    transaction_type VARCHAR(50) NOT NULL,
                    description VARCHAR(500) NOT NULL,
                    transaction_date DATE NOT NULL,
                    posted_date DATE,
                    amount NUMERIC(15, 2) NOT NULL,
                    is_posted BOOLEAN DEFAULT FALSE,
                    is_void BOOLEAN DEFAULT FALSE,
                    member_id UUID,
                    unit_id UUID,
                    fund_id UUID,
                    check_number VARCHAR(50),
                    bank_reference VARCHAR(100),
                    plaid_transaction_id VARCHAR(100),
                    notes TEXT,
                    created_at DATE NOT NULL DEFAULT CURRENT_DATE
                );

                CREATE TABLE IF NOT EXISTS {schema_name}.ledger_entries (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    property_id UUID NOT NULL,
                    transaction_id UUID NOT NULL,
                    fund_id UUID NOT NULL,
                    entry_date DATE NOT NULL,
                    description VARCHAR(500) NOT NULL,
                    amount NUMERIC(15, 2) NOT NULL,
                    is_debit BOOLEAN NOT NULL,
                    account_code VARCHAR(50) NOT NULL,
                    account_name VARCHAR(200) NOT NULL,
                    is_reversing BOOLEAN DEFAULT FALSE,
                    reverses_entry_id UUID,
                    created_at DATE NOT NULL DEFAULT CURRENT_DATE
                );

                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_{schema_name}_members_tenant ON {schema_name}.members(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_{schema_name}_members_property ON {schema_name}.members(property_id);
                CREATE INDEX IF NOT EXISTS idx_{schema_name}_transactions_tenant ON {schema_name}.transactions(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_{schema_name}_transactions_property ON {schema_name}.transactions(property_id);
                CREATE INDEX IF NOT EXISTS idx_{schema_name}_transactions_member ON {schema_name}.transactions(member_id);
                CREATE INDEX IF NOT EXISTS idx_{schema_name}_ledger_tenant ON {schema_name}.ledger_entries(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_{schema_name}_ledger_transaction ON {schema_name}.ledger_entries(transaction_id);
                CREATE INDEX IF NOT EXISTS idx_{schema_name}_ledger_fund ON {schema_name}.ledger_entries(fund_id);
            """)

        return schema_name

    def drop_schema(self, tenant_id: UUID) -> None:
        """
        Drop a tenant schema (for cleanup).

        Args:
            tenant_id: Tenant UUID
        """
        schema_name = f"tenant_{tenant_id.hex}"

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")

    def schema_exists(self, tenant_id: UUID) -> bool:
        """
        Check if a tenant schema exists.

        Args:
            tenant_id: Tenant UUID

        Returns:
            True if schema exists
        """
        schema_name = f"tenant_{tenant_id.hex}"

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname = %s)",
                (schema_name,)
            )
            return cursor.fetchone()[0]
