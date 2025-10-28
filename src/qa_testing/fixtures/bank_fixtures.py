"""
Bank reconciliation test fixtures.

Provides fixtures for testing bank account sync, transaction matching,
and reconciliation workflows.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from qa_testing.models import Transaction, TransactionType
from qa_testing.mocks import PlaidAccount, PlaidTransaction, create_mock_checking_account


class SyncStatus(str, Enum):
    """Bank sync status."""

    PENDING = "pending"  # Not yet synced
    IN_PROGRESS = "in_progress"  # Sync in progress
    COMPLETED = "completed"  # Sync completed successfully
    FAILED = "failed"  # Sync failed with error


class MatchStatus(str, Enum):
    """Transaction match status."""

    UNMATCHED = "unmatched"  # No match found
    MATCHED = "matched"  # Matched to HOA transaction
    DUPLICATE = "duplicate"  # Duplicate of existing
    MANUAL_REVIEW = "manual_review"  # Requires manual review


@dataclass
class BankAccountFixture:
    """
    Test fixture for bank accounts.

    Represents a bank account being reconciled with Plaid.
    """

    id: UUID
    property_id: UUID
    tenant_id: UUID
    plaid_account_id: str
    plaid_item_id: str
    account_name: str
    account_type: str
    mask: str
    current_balance: Decimal
    last_sync_date: Optional[datetime]
    sync_cursor: Optional[str]
    sync_status: SyncStatus
    created_at: datetime

    @staticmethod
    def create(
        *,
        property_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        plaid_account: Optional[PlaidAccount] = None,
        last_sync_date: Optional[datetime] = None,
        sync_status: SyncStatus = SyncStatus.PENDING,
    ) -> "BankAccountFixture":
        """Create a bank account fixture."""
        if plaid_account is None:
            plaid_account = create_mock_checking_account()

        return BankAccountFixture(
            id=uuid4(),
            property_id=property_id or uuid4(),
            tenant_id=tenant_id or uuid4(),
            plaid_account_id=plaid_account.account_id,
            plaid_item_id=f"item_{uuid4().hex[:16]}",
            account_name=plaid_account.name,
            account_type=plaid_account.subtype.value,
            mask=plaid_account.mask,
            current_balance=plaid_account.current_balance,
            last_sync_date=last_sync_date,
            sync_cursor=None,
            sync_status=sync_status,
            created_at=datetime.now(),
        )


@dataclass
class BankTransactionMatch:
    """
    Test fixture for transaction matching.

    Represents a match between a Plaid transaction and an HOA transaction.
    """

    id: UUID
    bank_account_id: UUID
    plaid_transaction_id: str
    hoa_transaction_id: Optional[UUID]
    match_status: MatchStatus
    match_confidence: float  # 0.0 - 1.0
    match_reason: str
    matched_at: Optional[datetime]
    reviewed_by: Optional[str]

    @staticmethod
    def create(
        *,
        bank_account_id: UUID,
        plaid_transaction: PlaidTransaction,
        hoa_transaction: Optional[Transaction] = None,
        match_status: MatchStatus = MatchStatus.UNMATCHED,
        match_confidence: float = 0.0,
        match_reason: str = "No match found",
    ) -> "BankTransactionMatch":
        """Create a transaction match fixture."""
        return BankTransactionMatch(
            id=uuid4(),
            bank_account_id=bank_account_id,
            plaid_transaction_id=plaid_transaction.transaction_id,
            hoa_transaction_id=hoa_transaction.id if hoa_transaction else None,
            match_status=match_status,
            match_confidence=match_confidence,
            match_reason=match_reason,
            matched_at=datetime.now() if match_status == MatchStatus.MATCHED else None,
            reviewed_by=None,
        )


@dataclass
class BankSyncState:
    """
    Test fixture for bank sync state.

    Tracks the state of a bank sync operation.
    """

    bank_account_id: UUID
    sync_started_at: datetime
    sync_completed_at: Optional[datetime]
    sync_status: SyncStatus
    transactions_fetched: int
    transactions_matched: int
    transactions_unmatched: int
    duplicates_detected: int
    errors: list[str] = field(default_factory=list)

    @staticmethod
    def create(
        *,
        bank_account_id: UUID,
        sync_status: SyncStatus = SyncStatus.IN_PROGRESS,
        transactions_fetched: int = 0,
        transactions_matched: int = 0,
        transactions_unmatched: int = 0,
        duplicates_detected: int = 0,
    ) -> "BankSyncState":
        """Create a bank sync state fixture."""
        return BankSyncState(
            bank_account_id=bank_account_id,
            sync_started_at=datetime.now(),
            sync_completed_at=None if sync_status == SyncStatus.IN_PROGRESS else datetime.now(),
            sync_status=sync_status,
            transactions_fetched=transactions_fetched,
            transactions_matched=transactions_matched,
            transactions_unmatched=transactions_unmatched,
            duplicates_detected=duplicates_detected,
        )


# Scenario builders


def create_bank_sync_scenario(
    *,
    num_transactions: int = 10,
    duplicate_probability: float = 0.1,
    match_probability: float = 0.7,
) -> dict:
    """
    Create a complete bank sync test scenario.

    Returns a dictionary with:
    - bank_account: BankAccountFixture
    - plaid_transactions: list[PlaidTransaction]
    - hoa_transactions: list[Transaction] (for matching)
    - expected_matches: int
    - expected_duplicates: int

    Args:
        num_transactions: Number of transactions to generate
        duplicate_probability: Probability of generating duplicates (0.0 - 1.0)
        match_probability: Probability of transaction matching HOA transaction (0.0 - 1.0)
    """
    from random import random

    from qa_testing.generators import PropertyGenerator, TransactionGenerator
    from qa_testing.mocks import create_mock_payment_transaction

    # Create property and bank account
    property = PropertyGenerator.create()
    bank_account = BankAccountFixture.create(
        property_id=property.id,
        tenant_id=property.id,  # Using property ID as tenant
    )

    # Create Plaid transactions
    plaid_transactions = []
    hoa_transactions = []
    expected_matches = 0
    expected_duplicates = 0

    base_date = date.today() - timedelta(days=30)

    for i in range(num_transactions):
        transaction_date = base_date + timedelta(days=i)
        amount = Decimal("300.00") + (Decimal(i) * Decimal("10.00"))

        # Create Plaid transaction
        plaid_txn = create_mock_payment_transaction(
            account_id=bank_account.plaid_account_id,
            amount=amount,
            transaction_date=transaction_date,
            name=f"HOA Payment #{i+1}",
        )
        plaid_transactions.append(plaid_txn)

        # Decide if this should match an HOA transaction
        if random() < match_probability:
            # Create matching HOA transaction
            hoa_txn = TransactionGenerator.create_payment(
                property_id=property.id,
                member_id=property.id,  # Mock
                amount=amount,
                transaction_date=transaction_date,
                is_posted=True,
            )
            hoa_transactions.append(hoa_txn)
            expected_matches += 1

        # Decide if we should create a duplicate
        if random() < duplicate_probability:
            # Create duplicate Plaid transaction (same amount, date)
            duplicate_txn = create_mock_payment_transaction(
                account_id=bank_account.plaid_account_id,
                amount=amount,
                transaction_date=transaction_date,
                name=f"HOA Payment #{i+1}",  # Same name
            )
            plaid_transactions.append(duplicate_txn)
            expected_duplicates += 1

    return {
        "bank_account": bank_account,
        "plaid_transactions": plaid_transactions,
        "hoa_transactions": hoa_transactions,
        "expected_matches": expected_matches,
        "expected_duplicates": expected_duplicates,
        "expected_unmatched": len(plaid_transactions) - expected_matches - expected_duplicates,
    }


def create_duplicate_detection_scenario() -> dict:
    """
    Create a scenario specifically for testing duplicate detection.

    Returns:
    - bank_account: BankAccountFixture
    - original_transactions: list[PlaidTransaction]
    - duplicate_transactions: list[PlaidTransaction]
    """
    from qa_testing.generators import PropertyGenerator
    from qa_testing.mocks import create_mock_payment_transaction

    property = PropertyGenerator.create()
    bank_account = BankAccountFixture.create(
        property_id=property.id,
        tenant_id=property.id,
    )

    # Create 5 original transactions
    original_transactions = []
    for i in range(5):
        txn = create_mock_payment_transaction(
            account_id=bank_account.plaid_account_id,
            amount=Decimal("300.00"),
            transaction_date=date.today() - timedelta(days=i),
            name=f"Payment #{i+1}",
        )
        original_transactions.append(txn)

    # Create duplicates (same transaction_id, amount, date)
    duplicate_transactions = []
    for orig in original_transactions:
        duplicate = create_mock_payment_transaction(
            account_id=bank_account.plaid_account_id,
            amount=orig.amount,
            transaction_date=orig.date,
            name=orig.name,
        )
        # Force same transaction ID to simulate exact duplicate
        duplicate.transaction_id = orig.transaction_id
        duplicate_transactions.append(duplicate)

    return {
        "bank_account": bank_account,
        "original_transactions": original_transactions,
        "duplicate_transactions": duplicate_transactions,
    }


def create_webhook_scenario(
    webhook_type: str = "SYNC_UPDATES_AVAILABLE",
) -> dict:
    """
    Create a scenario for testing webhook handling.

    Returns:
    - bank_account: BankAccountFixture
    - webhook: PlaidWebhook
    - new_transactions: list[PlaidTransaction] (if applicable)
    """
    from qa_testing.generators import PropertyGenerator
    from qa_testing.mocks import PlaidMock, PlaidWebhookType, create_mock_payment_transaction

    property = PropertyGenerator.create()
    bank_account = BankAccountFixture.create(
        property_id=property.id,
        tenant_id=property.id,
    )

    plaid_mock = PlaidMock()

    # Create new transactions
    new_transactions = []
    if webhook_type == "SYNC_UPDATES_AVAILABLE":
        for i in range(3):
            txn = create_mock_payment_transaction(
                account_id=bank_account.plaid_account_id,
                amount=Decimal("300.00"),
                transaction_date=date.today() - timedelta(days=i),
                name=f"New Payment #{i+1}",
            )
            new_transactions.append(txn)
            plaid_mock.add_transaction(txn)

    # Create webhook
    webhook = plaid_mock.create_webhook(
        webhook_code=PlaidWebhookType[webhook_type],
        item_id=bank_account.plaid_item_id,
        new_transactions=len(new_transactions),
    )

    return {
        "bank_account": bank_account,
        "webhook": webhook,
        "new_transactions": new_transactions,
        "plaid_mock": plaid_mock,
    }
