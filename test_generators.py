"""Quick test of generators."""

from decimal import Decimal

from qa_testing.generators import (
    FundGenerator,
    LedgerEntryGenerator,
    MemberGenerator,
    PropertyGenerator,
    TransactionGenerator,
    UnitGenerator,
)

# Test Member generator
print("=== Testing Member Generator ===")
member = MemberGenerator.create()
print(f"Created member: {member.full_name} ({member.member_type.value})")
print(f"Payment history: {member.payment_history.value}")
print(f"Current balance: ${member.current_balance}")

# Test Property generator
print("\n=== Testing Property Generator ===")
property = PropertyGenerator.create()
print(f"Created property: {property.name}")
print(f"Type: {property.property_type.value}")
print(f"Total units: {property.total_units}")
print(f"Occupied units: {property.occupied_units}")
print(f"Fee structure: {property.fee_structure.value}")
print(f"Monthly fee base: ${property.monthly_fee_base}")

# Test Unit generator
print("\n=== Testing Unit Generator ===")
units = UnitGenerator.create_for_property(property, num_units=5)
print(f"Created {len(units)} units for property")
for i, unit in enumerate(units[:3], 1):
    print(f"  Unit {i}: #{unit.unit_number}, ${unit.monthly_fee}/month, {unit.bedrooms}BR/{unit.bathrooms}BA")

# Test Fund generator
print("\n=== Testing Fund Generator ===")
funds = FundGenerator.create_standard_funds(property.id)
print(f"Created {len(funds)} standard funds for property")
for fund in funds:
    funding_pct = f"{fund.funding_percentage:.1f}%" if fund.funding_percentage else "N/A"
    print(f"  {fund.name}: ${fund.current_balance:,} / ${fund.target_balance:,} ({funding_pct})")

# Test Transaction generator
print("\n=== Testing Transaction Generator ===")
transaction = TransactionGenerator.create_payment(
    property_id=property.id,
    member_id=member.id,
    unit_id=units[0].id,
    fund_id=funds[0].id,
    amount=Decimal("300.00"),
)
print(f"Created transaction: {transaction.transaction_type.value}")
print(f"Amount: ${transaction.amount}")
print(f"Description: {transaction.description}")
print(f"Posted: {transaction.is_posted}")

# Test LedgerEntry generator
print("\n=== Testing LedgerEntry Generator ===")
debit, credit = LedgerEntryGenerator.create_for_payment(
    property_id=property.id,
    transaction=transaction,
    fund_id=funds[0].id,
)
print(f"Created balanced ledger entries:")
print(f"  Debit: {debit.account_name} (${debit.amount})")
print(f"  Credit: {credit.account_name} (${credit.amount})")
print(f"  Balanced: {debit.amount == credit.amount}")

print("\n[OK] All generator tests passed!")
