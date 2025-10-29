"""
Pytest fixtures for integration tests.

These fixtures set up and tear down test database schemas for each test.
"""

import os
from uuid import uuid4

import pytest


@pytest.fixture(scope="function")
def tenant_id():
    """Generate a unique tenant ID for each test."""
    return uuid4()


@pytest.fixture(scope="function")
def test_schema(tenant_id):
    """
    Create and clean up test schema for each test.

    This fixture:
    1. Creates a schema for the tenant
    2. Yields the schema name
    3. Drops the schema after the test
    """
    # Import database utilities only when needed
    from qa_testing.database import create_test_schema, drop_test_schema

    # Skip if no PostgreSQL available
    if not os.getenv("TEST_DATABASE_URL") and not _postgres_available():
        pytest.skip("PostgreSQL not available for integration tests")

    # Create schema
    schema_name = create_test_schema(tenant_id)

    yield schema_name

    # Cleanup
    drop_test_schema(tenant_id)


@pytest.fixture(scope="function")
def test_data(tenant_id, test_schema):
    """
    Seed test database with realistic HOA data.

    Returns dictionary with:
    - properties: List of Property instances
    - units: List of Unit instances
    - members: List of Member instances
    - funds: List of Fund instances
    """
    # Import database utilities only when needed
    from qa_testing.database import seed_test_data

    return seed_test_data(
        tenant_id,
        num_properties=1,
        num_units_per_property=10,
    )


@pytest.fixture(scope="function")
def test_db():
    """Get test database connection."""
    # Import database utilities only when needed
    from qa_testing.database import TestDatabase

    return TestDatabase()


def _postgres_available() -> bool:
    """Check if PostgreSQL is available."""
    try:
        # Import database utilities only when needed
        from qa_testing.database import TestDatabase

        test_db = TestDatabase()
        with test_db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return True
    except Exception:
        return False
