"""
Hypothesis strategies for generating test data.

These strategies are used for property-based testing to generate
realistic and diverse test cases automatically.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from hypothesis import strategies as st

from qa_testing.models import (
    FeeStructure,
    Fund,
    FundType,
    LedgerEntry,
    Member,
    MemberType,
    PaymentHistory,
    Property,
    PropertyType,
    Transaction,
    TransactionType,
    Unit,
)


# Basic strategies
@st.composite
def uuid_strategy(draw):
    """Generate UUIDs."""
    return uuid4()


@st.composite
def money_amount_strategy(draw, min_value=0, max_value=10000):
    """
    Generate money amounts with exactly 2 decimal places.

    Args:
        min_value: Minimum amount (default 0)
        max_value: Maximum amount (default 10000)
    """
    # Generate as integer cents, then convert to dollars
    cents = draw(st.integers(min_value=int(min_value * 100), max_value=int(max_value * 100)))
    return Decimal(str(cents / 100)).quantize(Decimal("0.01"))


@st.composite
def accounting_date_strategy(draw, start_date=None, end_date=None):
    """
    Generate accounting dates.

    Args:
        start_date: Start date (default: 5 years ago)
        end_date: End date (default: today)
    """
    if start_date is None:
        start_date = date.today() - timedelta(days=1825)  # 5 years ago
    if end_date is None:
        end_date = date.today()

    days_between = (end_date - start_date).days
    random_days = draw(st.integers(min_value=0, max_value=days_between))
    return start_date + timedelta(days=random_days)


# Model strategies
@st.composite
def member_strategy(draw, tenant_id=None, unit_id=None, property_id=None):
    """Generate Member instances."""
    return Member(
        tenant_id=tenant_id or draw(uuid_strategy()),
        unit_id=unit_id or draw(uuid_strategy()),
        property_id=property_id or draw(uuid_strategy()),
        first_name=draw(st.text(min_size=1, max_size=50)),
        last_name=draw(st.text(min_size=1, max_size=50)),
        email=draw(st.emails()),
        phone=draw(st.text(min_size=10, max_size=20)) if draw(st.booleans()) else None,
        member_type=draw(st.sampled_from(MemberType)),
        is_active=draw(st.booleans()),
        current_balance=draw(money_amount_strategy(min_value=-10000, max_value=10000)),
        total_paid=draw(money_amount_strategy(min_value=0, max_value=100000)),
        total_owed=draw(money_amount_strategy(min_value=0, max_value=100000)),
        payment_history=draw(st.sampled_from(PaymentHistory)),
        move_in_date=draw(accounting_date_strategy()),
        move_out_date=draw(accounting_date_strategy()) if draw(st.booleans()) else None,
    )


@st.composite
def property_strategy(draw, tenant_id=None):
    """Generate Property instances."""
    total_units = draw(st.integers(min_value=10, max_value=200))
    occupied_units = draw(st.integers(min_value=0, max_value=total_units))

    return Property(
        tenant_id=tenant_id or draw(uuid_strategy()),
        name=draw(st.text(min_size=5, max_size=200)),
        address=draw(st.text(min_size=10, max_size=500)),
        city=draw(st.text(min_size=2, max_size=100)),
        state=draw(st.text(min_size=2, max_size=2)),
        zip_code=draw(st.text(min_size=5, max_size=10)),
        property_type=draw(st.sampled_from(PropertyType)),
        total_units=total_units,
        occupied_units=occupied_units,
        fee_structure=draw(st.sampled_from(FeeStructure)),
        monthly_fee_base=draw(money_amount_strategy(min_value=100, max_value=1000)),
        fiscal_year_start_month=draw(st.integers(min_value=1, max_value=12)),
        management_company=draw(st.text(max_size=200)) if draw(st.booleans()) else None,
    )


@st.composite
def unit_strategy(draw, tenant_id=None, property_id=None):
    """Generate Unit instances."""
    return Unit(
        tenant_id=tenant_id or draw(uuid_strategy()),
        property_id=property_id or draw(uuid_strategy()),
        unit_number=draw(st.text(min_size=1, max_size=50)),
        building=draw(st.text(max_size=50)) if draw(st.booleans()) else None,
        floor=draw(st.integers(min_value=0, max_value=30)) if draw(st.booleans()) else None,
        square_footage=draw(st.integers(min_value=400, max_value=5000)) if draw(st.booleans()) else None,
        bedrooms=draw(st.integers(min_value=0, max_value=6)) if draw(st.booleans()) else None,
        bathrooms=draw(money_amount_strategy(min_value=1, max_value=5)) if draw(st.booleans()) else None,
        monthly_fee=draw(money_amount_strategy(min_value=100, max_value=2000)),
        special_assessment=draw(money_amount_strategy(min_value=0, max_value=10000)),
        is_occupied=draw(st.booleans()),
        is_delinquent=draw(st.booleans()),
        current_member_id=draw(uuid_strategy()) if draw(st.booleans()) else None,
    )


@st.composite
def fund_strategy(draw, tenant_id=None, property_id=None):
    """Generate Fund instances."""
    current_balance = draw(money_amount_strategy(min_value=0, max_value=1000000))
    target_balance = draw(money_amount_strategy(min_value=10000, max_value=2000000)) if draw(st.booleans()) else None

    return Fund(
        tenant_id=tenant_id or draw(uuid_strategy()),
        property_id=property_id or draw(uuid_strategy()),
        name=draw(st.text(min_size=1, max_size=200)),
        description=draw(st.text(max_size=1000)) if draw(st.booleans()) else None,
        fund_type=draw(st.sampled_from(FundType)),
        current_balance=current_balance,
        target_balance=target_balance,
        minimum_balance=draw(money_amount_strategy(min_value=-10000, max_value=0)),
        allow_negative_balance=draw(st.booleans()),
        is_active=draw(st.booleans()),
    )


@st.composite
def transaction_strategy(draw, tenant_id=None, property_id=None):
    """Generate Transaction instances."""
    transaction_date = draw(accounting_date_strategy())

    return Transaction(
        tenant_id=tenant_id or draw(uuid_strategy()),
        property_id=property_id or draw(uuid_strategy()),
        transaction_type=draw(st.sampled_from(TransactionType)),
        description=draw(st.text(min_size=1, max_size=500)),
        transaction_date=transaction_date,
        posted_date=draw(accounting_date_strategy(start_date=transaction_date)) if draw(st.booleans()) else None,
        amount=draw(money_amount_strategy(min_value=1, max_value=50000)),
        is_posted=draw(st.booleans()),
        is_void=draw(st.booleans()),
        member_id=draw(uuid_strategy()) if draw(st.booleans()) else None,
        unit_id=draw(uuid_strategy()) if draw(st.booleans()) else None,
        fund_id=draw(uuid_strategy()) if draw(st.booleans()) else None,
        check_number=draw(st.text(max_size=50)) if draw(st.booleans()) else None,
        bank_reference=draw(st.text(max_size=100)) if draw(st.booleans()) else None,
        plaid_transaction_id=draw(st.text(max_size=100)) if draw(st.booleans()) else None,
        notes=draw(st.text(max_size=2000)) if draw(st.booleans()) else None,
    )


@st.composite
def ledger_entry_strategy(draw, tenant_id=None, property_id=None, transaction_id=None, fund_id=None):
    """Generate LedgerEntry instances."""
    return LedgerEntry(
        tenant_id=tenant_id or draw(uuid_strategy()),
        property_id=property_id or draw(uuid_strategy()),
        transaction_id=transaction_id or draw(uuid_strategy()),
        fund_id=fund_id or draw(uuid_strategy()),
        entry_date=draw(accounting_date_strategy()),
        description=draw(st.text(min_size=1, max_size=500)),
        amount=draw(money_amount_strategy(min_value=1, max_value=50000)),
        is_debit=draw(st.booleans()),
        account_code=draw(st.text(min_size=1, max_size=50)),
        account_name=draw(st.text(min_size=1, max_size=200)),
        is_reversing=draw(st.booleans()),
        reverses_entry_id=draw(uuid_strategy()) if draw(st.booleans()) else None,
    )


@st.composite
def ledger_entry_pair_strategy(draw, tenant_id=None, property_id=None):
    """
    Generate a balanced pair of ledger entries (debit + credit).

    This is critical for testing the accounting equation: debits = credits.
    """
    shared_tenant_id = tenant_id or draw(uuid_strategy())
    shared_property_id = property_id or draw(uuid_strategy())
    shared_transaction_id = draw(uuid_strategy())
    shared_fund_id = draw(uuid_strategy())
    shared_amount = draw(money_amount_strategy(min_value=1, max_value=50000))
    shared_date = draw(accounting_date_strategy())

    debit_entry = LedgerEntry(
        tenant_id=shared_tenant_id,
        property_id=shared_property_id,
        transaction_id=shared_transaction_id,
        fund_id=shared_fund_id,
        entry_date=shared_date,
        description=draw(st.text(min_size=1, max_size=500)),
        amount=shared_amount,
        is_debit=True,
        account_code=draw(st.text(min_size=1, max_size=50)),
        account_name=draw(st.text(min_size=1, max_size=200)),
        is_reversing=False,
        reverses_entry_id=None,
    )

    credit_entry = LedgerEntry(
        tenant_id=shared_tenant_id,
        property_id=shared_property_id,
        transaction_id=shared_transaction_id,
        fund_id=shared_fund_id,
        entry_date=shared_date,
        description=draw(st.text(min_size=1, max_size=500)),
        amount=shared_amount,
        is_debit=False,
        account_code=draw(st.text(min_size=1, max_size=50)),
        account_name=draw(st.text(min_size=1, max_size=200)),
        is_reversing=False,
        reverses_entry_id=None,
    )

    return (debit_entry, credit_entry)
