# PostgreSQL Test Database Setup Guide

**Purpose:** Configure a PostgreSQL database for running integration tests that require database connectivity.

**Date:** 2025-10-29
**Status:** Ready for implementation

---

## Overview

This guide explains how to set up a PostgreSQL test database for the QA/Testing Infrastructure project. The test database uses the same multi-tenant schema-per-tenant architecture as the production system (saas202509).

### Current State

- **10 tests currently skipped** due to missing PostgreSQL connection
- Tests located in:
  - `tests/integration/test_payment_flows.py` (5 tests)
  - `tests/integration/test_refund_flows.py` (5 tests)

---

## Prerequisites

### Software Required

1. **PostgreSQL 15+** installed and running
   - Download: https://www.postgresql.org/download/
   - Port: 5410 (to avoid conflict with saas202509 on port 5432)

2. **Python packages** (already installed):
   - `psycopg[binary]>=3.1.0`
   - `pytest>=8.0.0`
   - `python-dotenv>=1.0.0`

---

## Setup Steps

### 1. Install PostgreSQL

**Windows:**
```powershell
# Download PostgreSQL installer
# Install to C:\Program Files\PostgreSQL\15
# Set password for postgres user
# Configure to run on port 5410
```

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Linux:**
```bash
sudo apt-get install postgresql-15
sudo systemctl start postgresql
```

### 2. Create Test Database

```bash
# Connect to PostgreSQL
psql -U postgres -p 5410

# Create test database
CREATE DATABASE qa_testing_db;

# Create test user
CREATE USER qa_test_user WITH ENCRYPTED PASSWORD 'test_password_123';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE qa_testing_db TO qa_test_user;

# Connect to test database
\c qa_testing_db

# Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

# Grant schema privileges
GRANT ALL ON SCHEMA public TO qa_test_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO qa_test_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO qa_test_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO qa_test_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO qa_test_user;

\q
```

### 3. Create Environment File

Create `.env.test` in project root:

```bash
# PostgreSQL Test Database Configuration
DATABASE_URL=postgresql://qa_test_user:test_password_123@localhost:5410/qa_testing_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5410
POSTGRES_DB=qa_testing_db
POSTGRES_USER=qa_test_user
POSTGRES_PASSWORD=test_password_123

# Test Configuration
TEST_ENV=true
DEBUG=true
```

**Security Note:** Add `.env.test` to `.gitignore` to avoid committing credentials.

### 4. Create Database Schema

Create schema initialization script `scripts/init_test_db.sql`:

```sql
-- Multi-Tenant Schema Structure
-- Each tenant gets their own schema

-- Create tenant schemas function
CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_id UUID)
RETURNS VOID AS $$
BEGIN
    -- Create schema for tenant
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS tenant_%s', replace(tenant_id::text, '-', '_'));

    -- Set search path
    EXECUTE format('SET search_path TO tenant_%s, public', replace(tenant_id::text, '-', '_'));

    -- Create tables in tenant schema
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS tenant_%s.members (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL,
            name VARCHAR(200) NOT NULL,
            email VARCHAR(200) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )', replace(tenant_id::text, '-', '_'));

    EXECUTE format('
        CREATE TABLE IF NOT EXISTS tenant_%s.properties (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL,
            name VARCHAR(200) NOT NULL,
            address TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )', replace(tenant_id::text, '-', '_'));

    EXECUTE format('
        CREATE TABLE IF NOT EXISTS tenant_%s.transactions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL,
            property_id UUID NOT NULL,
            member_id UUID,
            transaction_type VARCHAR(50) NOT NULL,
            amount NUMERIC(15,2) NOT NULL,
            transaction_date DATE NOT NULL,
            posted_date DATE,
            description TEXT,
            is_posted BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (property_id) REFERENCES tenant_%s.properties(id),
            FOREIGN KEY (member_id) REFERENCES tenant_%s.members(id)
        )',
        replace(tenant_id::text, '-', '_'),
        replace(tenant_id::text, '-', '_'),
        replace(tenant_id::text, '-', '_'));

    EXECUTE format('
        CREATE TABLE IF NOT EXISTS tenant_%s.ledger_entries (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL,
            transaction_id UUID NOT NULL,
            amount NUMERIC(15,2) NOT NULL,
            is_debit BOOLEAN NOT NULL,
            account_code VARCHAR(20) NOT NULL,
            account_name VARCHAR(200) NOT NULL,
            entry_date DATE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (transaction_id) REFERENCES tenant_%s.transactions(id)
        )',
        replace(tenant_id::text, '-', '_'),
        replace(tenant_id::text, '-', '_'));
END;
$$ LANGUAGE plpgsql;

-- Create test tenants
DO $$
DECLARE
    tenant1_id UUID := 'a0000000-0000-0000-0000-000000000001';
    tenant2_id UUID := 'a0000000-0000-0000-0000-000000000002';
BEGIN
    PERFORM create_tenant_schema(tenant1_id);
    PERFORM create_tenant_schema(tenant2_id);
END $$;
```

Run the initialization script:

```bash
psql -U qa_test_user -d qa_testing_db -p 5410 -f scripts/init_test_db.sql
```

### 5. Configure pytest Fixtures

Update `tests/conftest.py` to include database fixtures:

```python
import pytest
import psycopg
from dotenv import load_dotenv
import os

# Load test environment
load_dotenv('.env.test')

@pytest.fixture(scope="session")
def db_connection():
    """Create database connection for test session."""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        pytest.skip("PostgreSQL not configured for integration tests")

    conn = psycopg.connect(database_url)
    yield conn
    conn.close()

@pytest.fixture(scope="function")
def db_cursor(db_connection):
    """Create database cursor for each test."""
    cursor = db_connection.cursor()
    yield cursor
    db_connection.rollback()  # Rollback after each test
    cursor.close()

@pytest.fixture
def tenant_schema(db_cursor):
    """Create and clean up tenant schema for test."""
    import uuid
    tenant_id = uuid.uuid4()
    schema_name = f"tenant_{str(tenant_id).replace('-', '_')}"

    # Create schema
    db_cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
    db_cursor.execute(f"SET search_path TO {schema_name}, public")

    yield tenant_id, schema_name

    # Cleanup
    db_cursor.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
```

### 6. Update Test Skip Conditions

Modify skipped tests to use the new fixtures:

```python
# Before
@pytest.mark.skip(reason="PostgreSQL not available for integration tests")
def test_complete_payment_flow(self):
    pass

# After
def test_complete_payment_flow(self, db_cursor, tenant_schema):
    tenant_id, schema_name = tenant_schema
    # Test implementation with database
    pass
```

---

## Running Tests with Database

### Run All Tests (including database tests)
```bash
pytest tests/ -v
```

### Run Only Database-Dependent Tests
```bash
pytest tests/integration/test_payment_flows.py -v
pytest tests/integration/test_refund_flows.py -v
```

### Run Tests Without Database
```bash
pytest tests/ -v -m "not database"
```

---

## Database Maintenance

### Reset Test Database

```bash
# Connect to PostgreSQL
psql -U postgres -p 5410

# Drop and recreate
DROP DATABASE qa_testing_db;
CREATE DATABASE qa_testing_db;
GRANT ALL PRIVILEGES ON DATABASE qa_testing_db TO qa_test_user;

\c qa_testing_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\q

# Reinitialize schema
psql -U qa_test_user -d qa_testing_db -p 5410 -f scripts/init_test_db.sql
```

### View Test Data

```bash
# Connect to test database
psql -U qa_test_user -d qa_testing_db -p 5410

# List schemas
\dn

# Switch to tenant schema
SET search_path TO tenant_a0000000_0000_0000_0000_000000000001, public;

# View tables
\dt

# Query data
SELECT * FROM members LIMIT 10;
SELECT * FROM transactions LIMIT 10;
```

### Backup Test Data

```bash
# Backup entire database
pg_dump -U qa_test_user -p 5410 qa_testing_db > test_db_backup.sql

# Backup specific schema
pg_dump -U qa_test_user -p 5410 -n tenant_a0000000_0000_0000_0000_000000000001 qa_testing_db > tenant_backup.sql

# Restore backup
psql -U qa_test_user -p 5410 qa_testing_db < test_db_backup.sql
```

---

## CI/CD Integration

### GitHub Actions

Add PostgreSQL service to `.github/workflows/test.yml`:

```yaml
jobs:
  test-with-db:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: qa_test_user
          POSTGRES_PASSWORD: test_password_123
          POSTGRES_DB: qa_testing_db
        ports:
          - 5410:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Initialize database
        env:
          DATABASE_URL: postgresql://qa_test_user:test_password_123@localhost:5410/qa_testing_db
        run: |
          psql $DATABASE_URL -f scripts/init_test_db.sql

      - name: Run tests with database
        env:
          DATABASE_URL: postgresql://qa_test_user:test_password_123@localhost:5410/qa_testing_db
        run: |
          pytest tests/ -v
```

---

## Troubleshooting

### Connection Refused

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5410

# Check PostgreSQL logs
# Windows: C:\Program Files\PostgreSQL\15\data\log\
# macOS/Linux: /usr/local/var/postgres/

# Restart PostgreSQL
# Windows: Services -> PostgreSQL -> Restart
# macOS: brew services restart postgresql@15
# Linux: sudo systemctl restart postgresql
```

### Authentication Failed

```bash
# Check pg_hba.conf
# Add line: host all all 127.0.0.1/32 md5

# Reload PostgreSQL configuration
# Windows: Services -> PostgreSQL -> Restart
# macOS/Linux: pg_ctl reload
```

### Schema Not Found

```bash
# Reinitialize database schema
psql -U qa_test_user -d qa_testing_db -p 5410 -f scripts/init_test_db.sql

# Verify schemas exist
psql -U qa_test_user -d qa_testing_db -p 5410 -c "\dn"
```

### Tests Still Skipping

```bash
# Verify .env.test file exists and is loaded
cat .env.test

# Check DATABASE_URL is set
python -c "from dotenv import load_dotenv; import os; load_dotenv('.env.test'); print(os.getenv('DATABASE_URL'))"

# Run with verbose output
pytest tests/integration/test_payment_flows.py -v -s
```

---

## Security Best Practices

1. **Never commit `.env.test`** - Add to `.gitignore`
2. **Use strong passwords** for production-like environments
3. **Isolate test database** - Run on different port (5410 vs 5432)
4. **Regular backups** of test data if needed for debugging
5. **Reset database** between test runs for consistency
6. **Use fixtures** to ensure test isolation
7. **Grant minimal permissions** - test user shouldn't have SUPERUSER

---

## Expected Results

After setup:
- **10 previously skipped tests** will run
- **Total passing tests**: 696+ (up from 686)
- **Test coverage** increases to ~99%
- **CI/CD pipeline** includes database tests

---

## References

- PostgreSQL Documentation: https://www.postgresql.org/docs/
- psycopg3 Documentation: https://www.psycopg.org/psycopg3/
- pytest-postgresql: https://github.com/ClearcodeHQ/pytest-postgresql
- Multi-tenant Architecture: saas202509/technical/architecture/MULTI-TENANT-ACCOUNTING-ARCHITECTURE.md

---

**Status:** ✅ Complete - Ready for PostgreSQL setup
**Next Step:** Install PostgreSQL and run initialization scripts
**Estimated Setup Time:** 30 minutes

