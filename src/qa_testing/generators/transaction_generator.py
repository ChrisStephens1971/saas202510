"""Transaction and LedgerEntry generators for realistic transaction flows."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from faker import Faker

from qa_testing.models import LedgerEntry, Transaction, TransactionType

fake = Faker()


class TransactionGenerator:
    """
    Generator for creating realistic Transaction test data.

    Usage:
        # Create a single transaction
        transaction = TransactionGenerator.create(property_id=property.id)

        # Create a payment transaction
        payment = TransactionGenerator.create_payment(
            member_id=member.id,
            amount=Decimal("300.00")
        )
    """

    @staticmethod
    def create(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        transaction_type: Optional[TransactionType] = None,
        amount: Optional[Decimal] = None,
        member_id: Optional[UUID] = None,
        unit_id: Optional[UUID] = None,
        fund_id: Optional[UUID] = None,
        transaction_date: Optional[date] = None,
        is_posted: bool = False,
    ) -> Transaction:
        """
        Create a single Transaction with realistic data.

        Args:
            tenant_id: Tenant ID (generates one if not provided)
            property_id: Associated property ID (required)
            transaction_type: Type of transaction (random if not provided)
            amount: Transaction amount (random based on type if not provided)
            member_id: Associated member ID (optional)
            unit_id: Associated unit ID (optional)
            fund_id: Associated fund ID (optional)
            transaction_date: Date of transaction (random if not provided)
            is_posted: Whether transaction is posted to ledger

        Returns:
            Transaction instance with realistic data
        """
        tenant_id = tenant_id or uuid4()

        # Randomize transaction type if not provided
        if transaction_type is None:
            # Distribution: 60% income, 30% expense, 10% adjustment
            rand = fake.random.random()
            if rand < 0.60:
                transaction_type = fake.random.choice([
                    TransactionType.DUES_PAYMENT,
                    TransactionType.ASSESSMENT_PAYMENT,
                    TransactionType.LATE_FEE,
                ])
            elif rand < 0.90:
                transaction_type = fake.random.choice([
                    TransactionType.VENDOR_PAYMENT,
                    TransactionType.UTILITY,
                    TransactionType.MAINTENANCE,
                ])
            else:
                transaction_type = fake.random.choice([
                    TransactionType.REFUND,
                    TransactionType.ADJUSTMENT,
                ])

        # Generate amount based on transaction type if not provided
        if amount is None:
            amount = TransactionGenerator._generate_amount(transaction_type)

        # Generate transaction date (random within last 90 days)
        if transaction_date is None:
            days_ago = fake.random_int(min=0, max=90)
            transaction_date = date.today() - timedelta(days=days_ago)

        # Generate description
        description = TransactionGenerator._generate_description(transaction_type)

        # Posted date (if posted, typically same day or next day)
        posted_date = None
        if is_posted:
            posted_date = transaction_date + timedelta(days=fake.random_int(min=0, max=1))

        return Transaction(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_type=transaction_type,
            description=description,
            transaction_date=transaction_date,
            posted_date=posted_date,
            amount=amount,
            is_posted=is_posted,
            is_void=False,
            member_id=member_id,
            unit_id=unit_id,
            fund_id=fund_id,
            check_number=str(fake.random_int(min=1000, max=9999)) if transaction_type == TransactionType.VENDOR_PAYMENT and fake.random.random() < 0.5 else None,
            bank_reference=fake.uuid4() if is_posted and fake.random.random() < 0.3 else None,
            plaid_transaction_id=fake.uuid4() if is_posted and fake.random.random() < 0.2 else None,
        )

    @staticmethod
    def _generate_amount(transaction_type: TransactionType) -> Decimal:
        """Generate realistic amount based on transaction type with exactly 2 decimal places."""
        if transaction_type in [TransactionType.DUES_PAYMENT, TransactionType.ASSESSMENT_PAYMENT]:
            # Monthly dues: $200-$600
            return Decimal(str(fake.random_int(min=200, max=600, step=25))).quantize(Decimal("0.01"))

        elif transaction_type == TransactionType.LATE_FEE:
            # Late fees: $25-$100
            return Decimal(str(fake.random_int(min=25, max=100, step=5))).quantize(Decimal("0.01"))

        elif transaction_type == TransactionType.TRANSFER_FEE:
            # Transfer fees: $100-$500
            return Decimal(str(fake.random_int(min=100, max=500, step=50))).quantize(Decimal("0.01"))

        elif transaction_type in [TransactionType.VENDOR_PAYMENT, TransactionType.MAINTENANCE]:
            # Vendor/maintenance: $500-$5000
            return Decimal(str(fake.random_int(min=500, max=5000, step=100))).quantize(Decimal("0.01"))

        elif transaction_type == TransactionType.UTILITY:
            # Utilities: $200-$2000
            return Decimal(str(fake.random_int(min=200, max=2000, step=50))).quantize(Decimal("0.01"))

        elif transaction_type == TransactionType.INSURANCE:
            # Insurance: $1000-$10000
            return Decimal(str(fake.random_int(min=1000, max=10000, step=500))).quantize(Decimal("0.01"))

        elif transaction_type == TransactionType.MANAGEMENT_FEE:
            # Management fees: $500-$3000
            return Decimal(str(fake.random_int(min=500, max=3000, step=100))).quantize(Decimal("0.01"))

        elif transaction_type == TransactionType.REFUND:
            # Refunds: $50-$500
            return Decimal(str(fake.random_int(min=50, max=500, step=25))).quantize(Decimal("0.01"))

        elif transaction_type == TransactionType.ADJUSTMENT:
            # Adjustments: $10-$1000
            return Decimal(str(fake.random_int(min=10, max=1000, step=10))).quantize(Decimal("0.01"))

        elif transaction_type == TransactionType.BANK_FEE:
            # Bank fees: $5-$50
            return Decimal(str(fake.random_int(min=5, max=50, step=5))).quantize(Decimal("0.01"))

        else:
            # Default: $100-$1000
            return Decimal(str(fake.random_int(min=100, max=1000, step=50))).quantize(Decimal("0.01"))

    @staticmethod
    def _generate_description(transaction_type: TransactionType) -> str:
        """Generate realistic description based on transaction type."""
        descriptions = {
            TransactionType.DUES_PAYMENT: "Monthly HOA dues payment",
            TransactionType.ASSESSMENT_PAYMENT: f"Special assessment payment - {fake.word().capitalize()}",
            TransactionType.LATE_FEE: "Late payment fee",
            TransactionType.TRANSFER_FEE: "Unit transfer fee",
            TransactionType.OTHER_INCOME: "Other income",
            TransactionType.VENDOR_PAYMENT: f"Payment to {fake.company()}",
            TransactionType.UTILITY: f"{fake.random_element(['Electric', 'Water', 'Gas', 'Internet'])} utility payment",
            TransactionType.MAINTENANCE: f"Maintenance - {fake.random_element(['Landscaping', 'HVAC', 'Plumbing', 'Elevator', 'Pool'])}",
            TransactionType.INSURANCE: "Property insurance payment",
            TransactionType.MANAGEMENT_FEE: "Property management fee",
            TransactionType.OTHER_EXPENSE: "Other expense",
            TransactionType.REFUND: "Member refund",
            TransactionType.ADJUSTMENT: "Account adjustment",
            TransactionType.FUND_TRANSFER: "Transfer between funds",
            TransactionType.BANK_FEE: "Bank service fee",
        }
        return descriptions.get(transaction_type, "Transaction")

    @staticmethod
    def create_payment(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        member_id: UUID,
        unit_id: Optional[UUID] = None,
        fund_id: Optional[UUID] = None,
        amount: Decimal,
        transaction_date: Optional[date] = None,
        is_posted: bool = True,
    ) -> Transaction:
        """
        Create a payment transaction (dues or assessment).

        Args:
            tenant_id: Tenant ID
            property_id: Property ID
            member_id: Member making payment
            unit_id: Unit associated with payment
            fund_id: Fund receiving payment
            amount: Payment amount
            transaction_date: Date of payment
            is_posted: Whether payment is posted

        Returns:
            Transaction for payment
        """
        return TransactionGenerator.create(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_type=TransactionType.DUES_PAYMENT,
            amount=amount,
            member_id=member_id,
            unit_id=unit_id,
            fund_id=fund_id,
            transaction_date=transaction_date,
            is_posted=is_posted,
        )

    @staticmethod
    def create_refund(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        member_id: UUID,
        unit_id: Optional[UUID] = None,
        fund_id: Optional[UUID] = None,
        amount: Decimal,
        transaction_date: Optional[date] = None,
        is_posted: bool = True,
    ) -> Transaction:
        """
        Create a refund transaction.

        Args:
            tenant_id: Tenant ID
            property_id: Property ID
            member_id: Member receiving refund
            unit_id: Unit associated with refund
            fund_id: Fund source for refund
            amount: Refund amount
            transaction_date: Date of refund
            is_posted: Whether refund is posted

        Returns:
            Transaction for refund
        """
        return TransactionGenerator.create(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_type=TransactionType.REFUND,
            amount=amount,
            member_id=member_id,
            unit_id=unit_id,
            fund_id=fund_id,
            transaction_date=transaction_date,
            is_posted=is_posted,
        )

    @staticmethod
    def create_batch(
        count: int,
        *,
        property_id: UUID,
        tenant_id: Optional[UUID] = None,
        **kwargs
    ) -> list[Transaction]:
        """
        Create a batch of Transactions.

        Args:
            count: Number of transactions to create
            property_id: Property ID for all transactions
            tenant_id: Tenant ID for all transactions
            **kwargs: Additional arguments passed to create()

        Returns:
            List of Transaction instances
        """
        tenant_id = tenant_id or uuid4()

        return [
            TransactionGenerator.create(
                tenant_id=tenant_id,
                property_id=property_id,
                **kwargs
            )
            for _ in range(count)
        ]


class LedgerEntryGenerator:
    """
    Generator for creating balanced LedgerEntry pairs.

    CRITICAL: Ledger entries must always be created in balanced pairs
    where debits = credits. This is the foundation of double-entry bookkeeping.

    Usage:
        # Create a balanced pair of entries
        debit_entry, credit_entry = LedgerEntryGenerator.create_balanced_pair(
            transaction_id=transaction.id,
            amount=transaction.amount,
        )
    """

    @staticmethod
    def create_balanced_pair(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        transaction_id: UUID,
        fund_id: UUID,
        amount: Decimal,
        entry_date: Optional[date] = None,
        debit_account: Optional[tuple[str, str]] = None,
        credit_account: Optional[tuple[str, str]] = None,
        description: Optional[str] = None,
    ) -> tuple[LedgerEntry, LedgerEntry]:
        """
        Create a balanced pair of ledger entries (debit + credit).

        Args:
            tenant_id: Tenant ID
            property_id: Property ID
            transaction_id: Transaction ID
            fund_id: Fund ID
            amount: Amount for both entries
            entry_date: Date of entries
            debit_account: Tuple of (account_code, account_name) for debit
            credit_account: Tuple of (account_code, account_name) for credit
            description: Description for both entries

        Returns:
            Tuple of (debit_entry, credit_entry)
        """
        tenant_id = tenant_id or uuid4()
        entry_date = entry_date or date.today()
        description = description or "Ledger entry"

        # Default accounts if not provided
        if debit_account is None:
            debit_account = ("1000", "Cash")
        if credit_account is None:
            credit_account = ("4000", "Dues Income")

        debit_code, debit_name = debit_account
        credit_code, credit_name = credit_account

        debit_entry = LedgerEntry(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_id=transaction_id,
            fund_id=fund_id,
            entry_date=entry_date,
            description=description,
            amount=amount,
            is_debit=True,
            account_code=debit_code,
            account_name=debit_name,
        )

        credit_entry = LedgerEntry(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_id=transaction_id,
            fund_id=fund_id,
            entry_date=entry_date,
            description=description,
            amount=amount,
            is_debit=False,
            account_code=credit_code,
            account_name=credit_name,
        )

        return (debit_entry, credit_entry)

    @staticmethod
    def create_for_payment(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        transaction: Transaction,
        fund_id: UUID,
    ) -> tuple[LedgerEntry, LedgerEntry]:
        """
        Create balanced ledger entries for a payment transaction.

        Payment journal entry:
        DR Cash (1000)
        CR Dues Income (4000)

        Args:
            tenant_id: Tenant ID
            property_id: Property ID
            transaction: Payment transaction
            fund_id: Fund ID

        Returns:
            Tuple of (debit_entry, credit_entry)
        """
        return LedgerEntryGenerator.create_balanced_pair(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_id=transaction.id,
            fund_id=fund_id,
            amount=transaction.amount,
            entry_date=transaction.posted_date or transaction.transaction_date,
            debit_account=("1000", "Cash"),
            credit_account=("4000", "Dues Income"),
            description=f"Payment: {transaction.description}",
        )

    @staticmethod
    def create_for_expense(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        transaction: Transaction,
        fund_id: UUID,
        expense_account: tuple[str, str] = ("6000", "Operating Expenses"),
    ) -> tuple[LedgerEntry, LedgerEntry]:
        """
        Create balanced ledger entries for an expense transaction.

        Expense journal entry:
        DR Expense Account (6000)
        CR Cash (1000)

        Args:
            tenant_id: Tenant ID
            property_id: Property ID
            transaction: Expense transaction
            fund_id: Fund ID
            expense_account: Tuple of (account_code, account_name)

        Returns:
            Tuple of (debit_entry, credit_entry)
        """
        return LedgerEntryGenerator.create_balanced_pair(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_id=transaction.id,
            fund_id=fund_id,
            amount=transaction.amount,
            entry_date=transaction.posted_date or transaction.transaction_date,
            debit_account=expense_account,
            credit_account=("1000", "Cash"),
            description=f"Expense: {transaction.description}",
        )

    @staticmethod
    def create_for_refund(
        *,
        tenant_id: Optional[UUID] = None,
        property_id: UUID,
        transaction: Transaction,
        fund_id: UUID,
    ) -> tuple[LedgerEntry, LedgerEntry]:
        """
        Create balanced ledger entries for a refund transaction.

        Refund journal entry:
        DR Dues Income (4000) - reverses income
        CR Cash (1000) - reduces cash

        Args:
            tenant_id: Tenant ID
            property_id: Property ID
            transaction: Refund transaction
            fund_id: Fund ID

        Returns:
            Tuple of (debit_entry, credit_entry)
        """
        return LedgerEntryGenerator.create_balanced_pair(
            tenant_id=tenant_id,
            property_id=property_id,
            transaction_id=transaction.id,
            fund_id=fund_id,
            amount=transaction.amount,
            entry_date=transaction.posted_date or transaction.transaction_date,
            debit_account=("4000", "Dues Income"),
            credit_account=("1000", "Cash"),
            description=f"Refund: {transaction.description}",
        )
