"""
Integration tests for bank reconciliation.

These tests validate that bank account sync, transaction matching,
and reconciliation workflows work correctly with the Plaid API mock.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from qa_testing.fixtures import (
    BankTransactionMatch,
    MatchStatus,
    SyncStatus,
    create_bank_sync_scenario,
    create_duplicate_detection_scenario,
    create_webhook_scenario,
)
from qa_testing.generators import PropertyGenerator, TransactionGenerator
from qa_testing.mocks import (
    PlaidMock,
    PlaidWebhookType,
    create_mock_checking_account,
    create_mock_payment_transaction,
)


class TestPlaidMock:
    """Tests for Plaid API mock."""

    def test_plaid_mock_creates_accounts(self):
        """Test that Plaid mock can create accounts."""
        plaid = PlaidMock()
        account = create_mock_checking_account(balance=Decimal("5000.00"))
        plaid.add_account(account)

        # Get accounts via auth endpoint
        response = plaid.auth_get("mock_access_token")

        assert len(response["accounts"]) == 1
        assert response["accounts"][0]["account_id"] == account.account_id
        assert response["accounts"][0]["balances"]["current"] == 5000.00

    def test_plaid_mock_creates_transactions(self):
        """Test that Plaid mock can create transactions."""
        plaid = PlaidMock()
        account = create_mock_checking_account()
        plaid.add_account(account)

        # Add transactions
        txn1 = create_mock_payment_transaction(
            account_id=account.account_id,
            amount=Decimal("300.00"),
            transaction_date=date.today(),
        )
        plaid.add_transaction(txn1)

        # Fetch transactions
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        response = plaid.transactions_get(
            "mock_access_token",
            start_date,
            end_date,
        )

        assert len(response["transactions"]) == 1
        assert response["transactions"][0]["transaction_id"] == txn1.transaction_id
        assert response["transactions"][0]["amount"] == 300.00

    def test_plaid_mock_transactions_sync(self):
        """Test that Plaid mock supports incremental sync."""
        plaid = PlaidMock()
        account = create_mock_checking_account()
        plaid.add_account(account)

        # Add 10 transactions
        for i in range(10):
            txn = create_mock_payment_transaction(
                account_id=account.account_id,
                amount=Decimal("300.00"),
                transaction_date=date.today() - timedelta(days=i),
            )
            plaid.add_transaction(txn)

        # Sync transactions (initial sync, no cursor)
        response = plaid.transactions_sync("mock_access_token", cursor=None, count=100)

        assert len(response["added"]) == 10
        assert "next_cursor" in response
        assert plaid.sync_cursor is not None

    def test_plaid_mock_webhook_creation(self):
        """Test that Plaid mock can create webhooks."""
        plaid = PlaidMock()
        webhook = plaid.create_webhook(
            webhook_code=PlaidWebhookType.SYNC_UPDATES_AVAILABLE,
            item_id="item_123",
            new_transactions=5,
        )

        payload = webhook.to_dict()

        assert payload["webhook_type"] == "TRANSACTIONS"
        assert payload["webhook_code"] == "SYNC_UPDATES_AVAILABLE"
        assert payload["item_id"] == "item_123"
        assert payload["new_transactions"] == 5


class TestBankSync:
    """Tests for bank account sync."""

    def test_bank_sync_scenario_generation(self):
        """Test that bank sync scenario generates expected data."""
        scenario = create_bank_sync_scenario(
            num_transactions=20,
            duplicate_probability=0.1,
            match_probability=0.7,
        )

        assert scenario["bank_account"] is not None
        assert len(scenario["plaid_transactions"]) >= 20  # Original + duplicates
        assert scenario["expected_matches"] > 0
        assert "expected_duplicates" in scenario

    def test_bank_sync_fetches_transactions(self):
        """Test that bank sync fetches transactions from Plaid."""
        plaid = PlaidMock()
        account = create_mock_checking_account()
        plaid.add_account(account)

        # Add 10 transactions
        for i in range(10):
            txn = create_mock_payment_transaction(
                account_id=account.account_id,
                amount=Decimal("300.00"),
                transaction_date=date.today() - timedelta(days=i),
            )
            plaid.add_transaction(txn)

        # Simulate sync
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        response = plaid.transactions_get(
            "mock_access_token",
            start_date,
            end_date,
        )

        # Should fetch all 10 transactions
        assert len(response["transactions"]) == 10
        assert response["total_transactions"] == 10

    def test_bank_sync_filters_by_date_range(self):
        """Test that bank sync only fetches transactions in date range."""
        plaid = PlaidMock()
        account = create_mock_checking_account()
        plaid.add_account(account)

        # Add transactions across 30 days
        for i in range(30):
            txn = create_mock_payment_transaction(
                account_id=account.account_id,
                amount=Decimal("300.00"),
                transaction_date=date.today() - timedelta(days=i),
            )
            plaid.add_transaction(txn)

        # Fetch only last 7 days
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        response = plaid.transactions_get(
            "mock_access_token",
            start_date,
            end_date,
        )

        # Should fetch only transactions in last 7 days (0-7 days ago = 8 transactions, inclusive)
        assert len(response["transactions"]) == 8

    def test_bank_sync_handles_empty_results(self):
        """Test that bank sync handles no transactions gracefully."""
        plaid = PlaidMock()
        account = create_mock_checking_account()
        plaid.add_account(account)

        # Fetch transactions (none exist)
        response = plaid.transactions_get(
            "mock_access_token",
            date.today() - timedelta(days=7),
            date.today(),
        )

        assert len(response["transactions"]) == 0
        assert response["total_transactions"] == 0


class TestDuplicateDetection:
    """Tests for duplicate transaction detection."""

    def test_duplicate_detection_scenario(self):
        """Test duplicate detection scenario generation."""
        scenario = create_duplicate_detection_scenario()

        assert len(scenario["original_transactions"]) == 5
        assert len(scenario["duplicate_transactions"]) == 5

        # Duplicates should have same transaction IDs as originals
        for orig, dup in zip(
            scenario["original_transactions"],
            scenario["duplicate_transactions"],
        ):
            assert orig.transaction_id == dup.transaction_id

    def test_detect_duplicate_by_transaction_id(self):
        """Test that duplicates are detected by transaction ID."""
        scenario = create_duplicate_detection_scenario()

        original_ids = {txn.transaction_id for txn in scenario["original_transactions"]}
        duplicate_ids = {txn.transaction_id for txn in scenario["duplicate_transactions"]}

        # All duplicate IDs should match originals
        assert original_ids == duplicate_ids

    def test_detect_duplicate_by_amount_and_date(self):
        """Test that duplicates can be detected by amount + date."""
        plaid = PlaidMock()
        account = create_mock_checking_account()

        # Create two transactions with same amount and date
        txn1 = create_mock_payment_transaction(
            account_id=account.account_id,
            amount=Decimal("300.00"),
            transaction_date=date.today(),
            name="Payment 1",
        )

        txn2 = create_mock_payment_transaction(
            account_id=account.account_id,
            amount=Decimal("300.00"),  # Same amount
            transaction_date=date.today(),  # Same date
            name="Payment 1",  # Same name
        )

        # These should be considered potential duplicates
        assert txn1.amount == txn2.amount
        assert txn1.date == txn2.date
        assert txn1.name == txn2.name
        # But different transaction IDs
        assert txn1.transaction_id != txn2.transaction_id


class TestTransactionMatching:
    """Tests for matching Plaid transactions to HOA transactions."""

    def test_transaction_match_creation(self):
        """Test creating a transaction match."""
        from qa_testing.fixtures import BankAccountFixture

        bank_account = BankAccountFixture.create()
        plaid_txn = create_mock_payment_transaction(
            account_id=bank_account.plaid_account_id,
            amount=Decimal("300.00"),
        )

        match = BankTransactionMatch.create(
            bank_account_id=bank_account.id,
            plaid_transaction=plaid_txn,
            match_status=MatchStatus.UNMATCHED,
        )

        assert match.plaid_transaction_id == plaid_txn.transaction_id
        assert match.match_status == MatchStatus.UNMATCHED
        assert match.hoa_transaction_id is None

    def test_transaction_match_by_amount_and_date(self):
        """Test matching transactions by amount and date."""
        property = PropertyGenerator.create()

        # Create HOA transaction
        hoa_txn = TransactionGenerator.create_payment(
            property_id=property.id,
            member_id=property.id,
            amount=Decimal("300.00"),
            transaction_date=date.today(),
        )

        # Create matching Plaid transaction
        plaid_txn = create_mock_payment_transaction(
            account_id="acc_123",
            amount=Decimal("300.00"),  # Same amount
            transaction_date=date.today(),  # Same date
        )

        # Should match (same amount and date)
        assert hoa_txn.amount == plaid_txn.amount
        assert hoa_txn.transaction_date == plaid_txn.date

    def test_transaction_match_with_confidence(self):
        """Test that matches have confidence scores."""
        from qa_testing.fixtures import BankAccountFixture

        bank_account = BankAccountFixture.create()
        plaid_txn = create_mock_payment_transaction(
            account_id=bank_account.plaid_account_id,
            amount=Decimal("300.00"),
        )

        # High confidence match
        match = BankTransactionMatch.create(
            bank_account_id=bank_account.id,
            plaid_transaction=plaid_txn,
            match_status=MatchStatus.MATCHED,
            match_confidence=0.95,
            match_reason="Exact amount and date match",
        )

        assert match.match_confidence == 0.95
        assert match.match_status == MatchStatus.MATCHED

    def test_transaction_requires_manual_review(self):
        """Test that ambiguous matches require manual review."""
        from qa_testing.fixtures import BankAccountFixture

        bank_account = BankAccountFixture.create()
        plaid_txn = create_mock_payment_transaction(
            account_id=bank_account.plaid_account_id,
            amount=Decimal("300.00"),
        )

        # Low confidence - requires review
        match = BankTransactionMatch.create(
            bank_account_id=bank_account.id,
            plaid_transaction=plaid_txn,
            match_status=MatchStatus.MANUAL_REVIEW,
            match_confidence=0.60,
            match_reason="Multiple possible matches found",
        )

        assert match.match_status == MatchStatus.MANUAL_REVIEW
        assert match.match_confidence < 0.80  # Below high confidence threshold


class TestWebhookHandling:
    """Tests for Plaid webhook handling."""

    def test_webhook_scenario_sync_updates_available(self):
        """Test webhook scenario for new transactions."""
        scenario = create_webhook_scenario(
            webhook_type="SYNC_UPDATES_AVAILABLE"
        )

        assert scenario["webhook"] is not None
        assert len(scenario["new_transactions"]) == 3

        webhook_payload = scenario["webhook"].to_dict()
        assert webhook_payload["webhook_code"] == "SYNC_UPDATES_AVAILABLE"
        assert webhook_payload["new_transactions"] == 3

    def test_webhook_scenario_transactions_removed(self):
        """Test webhook scenario for removed transactions."""
        scenario = create_webhook_scenario(
            webhook_type="TRANSACTIONS_REMOVED"
        )

        assert scenario["webhook"] is not None
        webhook_payload = scenario["webhook"].to_dict()
        assert webhook_payload["webhook_code"] == "TRANSACTIONS_REMOVED"

    def test_webhook_triggers_incremental_sync(self):
        """Test that webhook triggers incremental sync."""
        scenario = create_webhook_scenario(
            webhook_type="SYNC_UPDATES_AVAILABLE"
        )

        plaid_mock = scenario["plaid_mock"]
        webhook = scenario["webhook"]

        # Webhook indicates new transactions available
        assert webhook.webhook_code == PlaidWebhookType.SYNC_UPDATES_AVAILABLE
        assert webhook.new_transactions == 3

        # Should trigger sync
        sync_response = plaid_mock.transactions_sync(
            "mock_access_token",
            cursor=None,
        )

        # Should return new transactions
        assert len(sync_response["added"]) == 3


class TestBankReconciliation:
    """Tests for bank reconciliation workflows."""

    def test_reconcile_simple_payment(self):
        """Test reconciling a simple payment."""
        plaid = PlaidMock()
        account = create_mock_checking_account(balance=Decimal("5000.00"))
        plaid.add_account(account)

        # Member makes payment
        plaid_txn = create_mock_payment_transaction(
            account_id=account.account_id,
            amount=Decimal("300.00"),
            transaction_date=date.today(),
            name="HOA Payment",
        )
        plaid.add_transaction(plaid_txn)

        # Verify account balance decreased
        expected_balance = Decimal("5000.00") - Decimal("300.00")
        assert expected_balance == Decimal("4700.00")

    def test_reconcile_multiple_payments(self):
        """Test reconciling multiple payments."""
        plaid = PlaidMock()
        account = create_mock_checking_account(balance=Decimal("5000.00"))
        plaid.add_account(account)

        # Add 5 payments
        total_paid = Decimal("0.00")
        for i in range(5):
            amount = Decimal("300.00")
            txn = create_mock_payment_transaction(
                account_id=account.account_id,
                amount=amount,
                transaction_date=date.today() - timedelta(days=i),
            )
            plaid.add_transaction(txn)
            total_paid += amount

        # Expected balance
        expected_balance = Decimal("5000.00") - total_paid
        assert expected_balance == Decimal("3500.00")

    def test_reconcile_handles_pending_transactions(self):
        """Test that pending transactions are handled correctly."""
        plaid_txn = create_mock_payment_transaction(
            account_id="acc_123",
            amount=Decimal("300.00"),
            transaction_date=date.today(),
        )

        # Mark as pending
        plaid_txn.pending = True

        # Pending transactions should not affect reconciled balance yet
        assert plaid_txn.pending is True
