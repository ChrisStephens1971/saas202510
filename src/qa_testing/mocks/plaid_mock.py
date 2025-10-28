"""
Mock Plaid API for testing bank reconciliation.

This mock simulates Plaid API responses for testing purposes.
It supports:
- Account information (/auth/get)
- Transaction listing (/transactions/get)
- Incremental sync (/transactions/sync)
- Webhooks (TRANSACTIONS_REMOVED, SYNC_UPDATES_AVAILABLE)

Based on Plaid API v2020-09-14
https://plaid.com/docs/api/
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from qa_testing.models.base import money_amount


class PlaidAccountType(str, Enum):
    """Plaid account types."""

    DEPOSITORY = "depository"  # Checking, savings
    CREDIT = "credit"  # Credit cards
    LOAN = "loan"  # Mortgages, student loans
    INVESTMENT = "investment"  # Brokerage, 401k


class PlaidAccountSubtype(str, Enum):
    """Plaid account subtypes."""

    CHECKING = "checking"
    SAVINGS = "savings"
    MONEY_MARKET = "money market"
    CREDIT_CARD = "credit card"


class PlaidTransactionType(str, Enum):
    """Plaid transaction types."""

    DIGITAL = "digital"  # Online, mobile
    PLACE = "place"  # Physical location
    SPECIAL = "special"  # Adjustment, fee
    UNRESOLVED = "unresolved"  # Unknown


class PlaidWebhookType(str, Enum):
    """Plaid webhook types."""

    TRANSACTIONS_REMOVED = "TRANSACTIONS_REMOVED"
    SYNC_UPDATES_AVAILABLE = "SYNC_UPDATES_AVAILABLE"
    DEFAULT_UPDATE = "DEFAULT_UPDATE"
    HISTORICAL_UPDATE = "HISTORICAL_UPDATE"


@dataclass
class PlaidAccount:
    """
    Mock Plaid account.

    Represents a bank account from Plaid API.
    """

    account_id: str
    name: str
    official_name: str
    type: PlaidAccountType
    subtype: PlaidAccountSubtype
    mask: str  # Last 4 digits
    current_balance: Decimal
    available_balance: Decimal
    routing_number: Optional[str] = None
    account_number: Optional[str] = None

    @staticmethod
    def create(
        *,
        account_id: Optional[str] = None,
        name: str = "Checking Account",
        official_name: str = "Premier Checking",
        account_type: PlaidAccountType = PlaidAccountType.DEPOSITORY,
        subtype: PlaidAccountSubtype = PlaidAccountSubtype.CHECKING,
        mask: str = "1234",
        current_balance: Decimal = Decimal("5000.00"),
        available_balance: Decimal = Decimal("5000.00"),
        routing_number: str = "011401533",
        account_number: str = "1111222233331234",
    ) -> "PlaidAccount":
        """Create a mock Plaid account with defaults."""
        return PlaidAccount(
            account_id=account_id or f"acc_{uuid4().hex[:16]}",
            name=name,
            official_name=official_name,
            type=account_type,
            subtype=subtype,
            mask=mask,
            current_balance=money_amount(current_balance),
            available_balance=money_amount(available_balance),
            routing_number=routing_number,
            account_number=account_number,
        )

    def to_dict(self) -> dict:
        """Convert to Plaid API response format."""
        return {
            "account_id": self.account_id,
            "balances": {
                "current": float(self.current_balance),
                "available": float(self.available_balance),
                "iso_currency_code": "USD",
            },
            "mask": self.mask,
            "name": self.name,
            "official_name": self.official_name,
            "type": self.type.value,
            "subtype": self.subtype.value,
        }


@dataclass
class PlaidTransaction:
    """
    Mock Plaid transaction.

    Represents a transaction from Plaid API.
    """

    transaction_id: str
    account_id: str
    amount: Decimal  # Positive = money out, Negative = money in
    date: date
    name: str
    merchant_name: Optional[str]
    category: list[str]
    pending: bool
    transaction_type: PlaidTransactionType
    payment_channel: str  # "online", "in store", "other"
    iso_currency_code: str = "USD"

    @staticmethod
    def create(
        *,
        transaction_id: Optional[str] = None,
        account_id: str,
        amount: Decimal,
        transaction_date: Optional[date] = None,
        name: str = "Payment",
        merchant_name: Optional[str] = None,
        category: Optional[list[str]] = None,
        pending: bool = False,
        transaction_type: PlaidTransactionType = PlaidTransactionType.PLACE,
        payment_channel: str = "in store",
    ) -> "PlaidTransaction":
        """Create a mock Plaid transaction."""
        return PlaidTransaction(
            transaction_id=transaction_id or f"txn_{uuid4().hex[:16]}",
            account_id=account_id,
            amount=money_amount(amount),
            date=transaction_date or date.today(),
            name=name,
            merchant_name=merchant_name,
            category=category or ["Payment"],
            pending=pending,
            transaction_type=transaction_type,
            payment_channel=payment_channel,
        )

    def to_dict(self) -> dict:
        """Convert to Plaid API response format."""
        return {
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "amount": float(self.amount),
            "date": self.date.isoformat(),
            "name": self.name,
            "merchant_name": self.merchant_name,
            "category": self.category,
            "pending": self.pending,
            "transaction_type": self.transaction_type.value,
            "payment_channel": self.payment_channel,
            "iso_currency_code": self.iso_currency_code,
        }


@dataclass
class PlaidWebhook:
    """
    Mock Plaid webhook.

    Represents a webhook event from Plaid.
    """

    webhook_type: str  # "TRANSACTIONS"
    webhook_code: PlaidWebhookType
    item_id: str
    new_transactions: int = 0
    removed_transactions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to Plaid webhook payload format."""
        payload = {
            "webhook_type": self.webhook_type,
            "webhook_code": self.webhook_code.value,
            "item_id": self.item_id,
        }

        if self.webhook_code == PlaidWebhookType.SYNC_UPDATES_AVAILABLE:
            payload["new_transactions"] = self.new_transactions

        if self.webhook_code == PlaidWebhookType.TRANSACTIONS_REMOVED:
            payload["removed_transactions"] = self.removed_transactions

        return payload


class PlaidMock:
    """
    Mock Plaid API server for testing.

    This class simulates Plaid API responses without making actual API calls.
    """

    def __init__(self):
        """Initialize mock Plaid API."""
        self.accounts: dict[str, PlaidAccount] = {}
        self.transactions: dict[str, PlaidTransaction] = {}
        self.sync_cursor: Optional[str] = None
        self.request_count = 0

    def add_account(self, account: PlaidAccount) -> None:
        """Add an account to the mock."""
        self.accounts[account.account_id] = account

    def add_transaction(self, transaction: PlaidTransaction) -> None:
        """Add a transaction to the mock."""
        self.transactions[transaction.transaction_id] = transaction

    def auth_get(self, access_token: str) -> dict:
        """
        Mock /auth/get endpoint.

        Returns account and routing numbers.
        """
        self.request_count += 1

        return {
            "accounts": [
                {
                    **account.to_dict(),
                    "routing_numbers": [account.routing_number] if account.routing_number else [],
                    "account_number": account.account_number,
                }
                for account in self.accounts.values()
            ],
            "numbers": {
                "ach": [
                    {
                        "account": account.account_number,
                        "account_id": account.account_id,
                        "routing": account.routing_number,
                    }
                    for account in self.accounts.values()
                    if account.routing_number
                ]
            },
            "request_id": f"req_{uuid4().hex[:16]}",
        }

    def transactions_get(
        self,
        access_token: str,
        start_date: date,
        end_date: date,
        account_ids: Optional[list[str]] = None,
    ) -> dict:
        """
        Mock /transactions/get endpoint.

        Returns transactions within date range.
        """
        self.request_count += 1

        # Filter transactions by date range
        filtered_transactions = [
            txn
            for txn in self.transactions.values()
            if start_date <= txn.date <= end_date
        ]

        # Filter by account IDs if specified
        if account_ids:
            filtered_transactions = [
                txn for txn in filtered_transactions if txn.account_id in account_ids
            ]

        return {
            "accounts": [account.to_dict() for account in self.accounts.values()],
            "transactions": [txn.to_dict() for txn in filtered_transactions],
            "total_transactions": len(filtered_transactions),
            "request_id": f"req_{uuid4().hex[:16]}",
        }

    def transactions_sync(
        self,
        access_token: str,
        cursor: Optional[str] = None,
        count: int = 100,
    ) -> dict:
        """
        Mock /transactions/sync endpoint.

        Returns incremental transaction updates with cursor.
        """
        self.request_count += 1

        # If no cursor, return all transactions
        if cursor is None:
            transactions = list(self.transactions.values())
        else:
            # Simulate incremental sync (return empty for now)
            transactions = []

        # Generate new cursor
        new_cursor = f"cursor_{uuid4().hex[:16]}"
        self.sync_cursor = new_cursor

        return {
            "added": [txn.to_dict() for txn in transactions[:count]],
            "modified": [],
            "removed": [],
            "next_cursor": new_cursor,
            "has_more": len(transactions) > count,
            "request_id": f"req_{uuid4().hex[:16]}",
        }

    def create_webhook(
        self,
        webhook_code: PlaidWebhookType,
        item_id: str,
        new_transactions: int = 0,
        removed_transactions: Optional[list[str]] = None,
    ) -> PlaidWebhook:
        """
        Create a mock webhook event.

        This simulates Plaid sending a webhook to your server.
        """
        return PlaidWebhook(
            webhook_type="TRANSACTIONS",
            webhook_code=webhook_code,
            item_id=item_id,
            new_transactions=new_transactions,
            removed_transactions=removed_transactions or [],
        )

    def reset(self) -> None:
        """Reset mock state (for testing)."""
        self.accounts.clear()
        self.transactions.clear()
        self.sync_cursor = None
        self.request_count = 0


# Convenience functions for testing


def create_mock_checking_account(
    account_id: Optional[str] = None,
    balance: Decimal = Decimal("5000.00"),
) -> PlaidAccount:
    """Create a mock checking account with defaults."""
    return PlaidAccount.create(
        account_id=account_id,
        name="Checking Account",
        official_name="Premier Checking",
        account_type=PlaidAccountType.DEPOSITORY,
        subtype=PlaidAccountSubtype.CHECKING,
        current_balance=balance,
        available_balance=balance,
    )


def create_mock_savings_account(
    account_id: Optional[str] = None,
    balance: Decimal = Decimal("10000.00"),
) -> PlaidAccount:
    """Create a mock savings account with defaults."""
    return PlaidAccount.create(
        account_id=account_id,
        name="Savings Account",
        official_name="High Yield Savings",
        account_type=PlaidAccountType.DEPOSITORY,
        subtype=PlaidAccountSubtype.SAVINGS,
        current_balance=balance,
        available_balance=balance,
    )


def create_mock_payment_transaction(
    account_id: str,
    amount: Decimal,
    transaction_date: Optional[date] = None,
    name: str = "HOA Payment",
    merchant_name: str = "HOA Association",
) -> PlaidTransaction:
    """Create a mock payment transaction (money out)."""
    return PlaidTransaction.create(
        account_id=account_id,
        amount=amount,  # Positive = money out
        transaction_date=transaction_date,
        name=name,
        merchant_name=merchant_name,
        category=["Payment", "Transfer"],
        payment_channel="online",
    )


def create_mock_deposit_transaction(
    account_id: str,
    amount: Decimal,
    transaction_date: Optional[date] = None,
    name: str = "Deposit",
    merchant_name: Optional[str] = None,
) -> PlaidTransaction:
    """Create a mock deposit transaction (money in)."""
    return PlaidTransaction.create(
        account_id=account_id,
        amount=-amount,  # Negative = money in
        transaction_date=transaction_date,
        name=name,
        merchant_name=merchant_name,
        category=["Transfer", "Deposit"],
        payment_channel="other",
    )
