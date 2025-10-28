# QA/Testing Infrastructure for HOA Accounting System

This directory contains the test data generators, property-based tests, and financial validators for the Multi-Tenant HOA Accounting System (saas202509).

## Project Structure

```
src/
├── qa_testing/           # Main testing module
│   ├── models/          # Test data models (Pydantic)
│   ├── generators/      # Test data generators (Faker + Hypothesis)
│   ├── validators/      # Financial validators (accounting rules)
│   └── utils/           # Testing utilities
tests/
├── property/            # Property-based tests (Hypothesis)
├── integration/         # Integration tests
└── fixtures/            # Test fixtures and sample data
```

## Setup

### Prerequisites

- Python 3.11+ (Python 3.14 currently installed)
- PostgreSQL 15+ (for integration tests)

### Installation

1. Create and activate virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux
```

2. Install dependencies:
```bash
pip install -e ".[dev]"
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=src --cov-report=html
```

### Run specific test types
```bash
# Property-based tests only
pytest -m property

# Integration tests only
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Run tests in parallel
```bash
pytest -n auto  # Auto-detect CPU count
```

## Development Tools

### Code Formatting
```bash
black src tests
```

### Linting
```bash
ruff check src tests
```

### Type Checking
```bash
mypy src
```

## Data Types

**CRITICAL: Financial data must use exact types:**

- **Money amounts:** `NUMERIC(15, 2)` - NEVER float or arbitrary-precision Decimal
- **Dates:** `DATE` - Not datetime for accounting dates
- **Amounts:** Always 2 decimal places for USD
- **IDs:** UUID for tenant isolation

Example:
```python
from decimal import Decimal

# Correct
amount = Decimal("123.45")  # Exactly 2 decimal places

# Incorrect
amount = 123.45  # Float - DO NOT USE for money!
amount = Decimal("123.456")  # 3 decimals - wrong precision
```

## Test Data Generators

Test data generators create realistic HOA scenarios:

```python
from qa_testing.generators import MemberGenerator, PropertyGenerator

# Generate a member
member = MemberGenerator.create(payment_history="on_time")

# Generate a property with units
property = PropertyGenerator.create(num_units=50, fee_structure="tiered")
```

## Property-Based Testing

Property-based tests validate accounting invariants:

```python
from hypothesis import given
from qa_testing.generators import transaction_strategy

@given(transaction_strategy())
def test_debits_equal_credits(transaction):
    """For ANY transaction, debits must equal credits."""
    assert sum(transaction.debits) == sum(transaction.credits)
```

## Integration with saas202509

This testing infrastructure validates the accounting system in `C:\devop\saas202509`.

**Key files to reference:**
- `C:\devop\saas202509\ACCOUNTING-PROJECT-QUICKSTART.md` - What we're testing
- `C:\devop\saas202509\product\HOA-PAIN-POINTS-AND-REQUIREMENTS.md` - Requirements
- `C:\devop\saas202509\technical\architecture\MULTI-TENANT-ACCOUNTING-ARCHITECTURE.md` - Architecture

## Contributing

1. All tests must use correct data types (NUMERIC for money, DATE for dates)
2. Property-based tests should generate 100+ examples
3. Integration tests must use schema-per-tenant architecture
4. Maintain 100% accuracy for financial calculations (zero tolerance for errors)

## Resources

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Faker Documentation](https://faker.readthedocs.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
