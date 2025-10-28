"""
Integration tests for AR (Accounts Receivable) and Collections workflows.

These tests validate delinquency scenarios, late fee calculation,
aging reports, payment plans, and collections workflows.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from qa_testing.generators import (
    ARCollectionsGenerator,
    DelinquencyStatus,
    MemberGenerator,
    PaymentPlanStatus,
    PropertyGenerator,
)


class TestDelinquencyStatus:
    """Tests for delinquency status calculation."""

    def test_current_status_under_30_days(self):
        """Test that accounts under 30 days are current."""
        status = ARCollectionsGenerator.calculate_delinquency_status(15)
        assert status == DelinquencyStatus.CURRENT

    def test_late_30_status_30_to_59_days(self):
        """Test that accounts 30-59 days past due are late_30."""
        status = ARCollectionsGenerator.calculate_delinquency_status(45)
        assert status == DelinquencyStatus.LATE_30

    def test_late_60_status_60_to_89_days(self):
        """Test that accounts 60-89 days past due are late_60."""
        status = ARCollectionsGenerator.calculate_delinquency_status(75)
        assert status == DelinquencyStatus.LATE_60

    def test_late_90_status_90_to_119_days(self):
        """Test that accounts 90-119 days past due are late_90."""
        status = ARCollectionsGenerator.calculate_delinquency_status(105)
        assert status == DelinquencyStatus.LATE_90

    def test_collections_status_120_to_179_days(self):
        """Test that accounts 120+ days go to collections."""
        status = ARCollectionsGenerator.calculate_delinquency_status(150)
        assert status == DelinquencyStatus.COLLECTIONS

    def test_legal_status_180_plus_days(self):
        """Test that accounts 180+ days may involve legal action."""
        status = ARCollectionsGenerator.calculate_delinquency_status(200)
        assert status == DelinquencyStatus.LEGAL

    @pytest.mark.property
    @given(st.integers(min_value=0, max_value=29))
    def test_all_under_30_days_are_current(self, days):
        """Property: All accounts under 30 days past due are current."""
        status = ARCollectionsGenerator.calculate_delinquency_status(days)
        assert status == DelinquencyStatus.CURRENT


class TestLateFees:
    """Tests for late fee calculation."""

    def test_no_late_fee_within_grace_period(self):
        """Test that no late fee applies within grace period."""
        late_fee = ARCollectionsGenerator.calculate_late_fees(
            balance=Decimal("300.00"),
            days_past_due=5,
            grace_period=10,
        )

        assert late_fee == Decimal("0.00")

    def test_flat_late_fee_after_grace_period(self):
        """Test that flat late fee applies after grace period."""
        late_fee = ARCollectionsGenerator.calculate_late_fees(
            balance=Decimal("300.00"),
            days_past_due=15,
            grace_period=10,
            flat_fee=Decimal("25.00"),
        )

        assert late_fee == Decimal("25.00")

    def test_monthly_penalty_accumulates(self):
        """Test that monthly penalty accumulates over time."""
        # 45 days past due = 1 month late (after 10-day grace)
        late_fee = ARCollectionsGenerator.calculate_late_fees(
            balance=Decimal("300.00"),
            days_past_due=45,
            grace_period=10,
            flat_fee=Decimal("25.00"),
            monthly_rate=Decimal("0.05"),  # 5% per month
        )

        # Flat fee + 1 month penalty
        expected = Decimal("25.00") + (Decimal("300.00") * Decimal("0.05"))
        assert late_fee == expected  # $25 + $15 = $40

    def test_multiple_months_penalty(self):
        """Test that penalty compounds over multiple months."""
        # 75 days past due = 2 months late (after 10-day grace)
        late_fee = ARCollectionsGenerator.calculate_late_fees(
            balance=Decimal("300.00"),
            days_past_due=75,
            grace_period=10,
            flat_fee=Decimal("25.00"),
            monthly_rate=Decimal("0.05"),  # 5% per month
        )

        # Flat fee + 2 months penalty
        expected = Decimal("25.00") + (Decimal("300.00") * Decimal("0.05") * Decimal("2"))
        assert late_fee == expected  # $25 + $30 = $55


class TestDelinquentScenarios:
    """Tests for delinquent member scenarios."""

    def test_create_delinquent_scenario(self):
        """Test creating a delinquent scenario."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        scenario = ARCollectionsGenerator.create_delinquent_scenario(
            property_id=property.id,
            member_id=member.id,
            days_past_due=45,
            original_balance=Decimal("300.00"),
        )

        assert scenario["status"] == DelinquencyStatus.LATE_30
        assert scenario["days_past_due"] == 45
        assert scenario["original_balance"] == Decimal("300.00")
        assert scenario["late_fees"] > Decimal("0.00")
        assert scenario["balance_owed"] > scenario["original_balance"]
        assert len(scenario["transactions"]) >= 2  # Original + late fee

    def test_delinquent_scenario_creates_transactions(self):
        """Test that delinquent scenario creates appropriate transactions."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        scenario = ARCollectionsGenerator.create_delinquent_scenario(
            property_id=property.id,
            member_id=member.id,
            days_past_due=60,
            original_balance=Decimal("300.00"),
        )

        transactions = scenario["transactions"]

        # Should have original transaction + late fee transaction
        assert len(transactions) == 2

        # Original transaction should be dated 60 days ago
        original_txn = transactions[0]
        expected_date = date.today() - timedelta(days=60)
        assert original_txn.transaction_date == expected_date

        # Late fee transaction should be today
        late_fee_txn = transactions[1]
        assert late_fee_txn.transaction_date == date.today()

    def test_90_plus_days_delinquent(self):
        """Test severely delinquent scenario (90+ days)."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        scenario = ARCollectionsGenerator.create_delinquent_scenario(
            property_id=property.id,
            member_id=member.id,
            days_past_due=105,
            original_balance=Decimal("300.00"),
        )

        assert scenario["status"] == DelinquencyStatus.LATE_90
        # Should have significant late fees
        assert scenario["late_fees"] >= Decimal("50.00")


class TestAgingBuckets:
    """Tests for AR aging reports."""

    def test_create_aging_bucket(self):
        """Test creating an aging bucket."""
        bucket = ARCollectionsGenerator.create_aging_bucket(
            current=Decimal("1000.00"),
            days_30=Decimal("500.00"),
            days_60=Decimal("300.00"),
            days_90_plus=Decimal("200.00"),
        )

        assert bucket.current == Decimal("1000.00")
        assert bucket.days_30 == Decimal("500.00")
        assert bucket.days_60 == Decimal("300.00")
        assert bucket.days_90_plus == Decimal("200.00")
        assert bucket.total == Decimal("2000.00")

    def test_empty_aging_bucket(self):
        """Test that empty aging bucket has zero total."""
        bucket = ARCollectionsGenerator.create_aging_bucket()

        assert bucket.current == Decimal("0.00")
        assert bucket.days_30 == Decimal("0.00")
        assert bucket.days_60 == Decimal("0.00")
        assert bucket.days_90_plus == Decimal("0.00")
        assert bucket.total == Decimal("0.00")

    def test_allocate_partial_payment_oldest_first(self):
        """Test that partial payments are allocated to oldest balances first."""
        bucket = ARCollectionsGenerator.create_aging_bucket(
            current=Decimal("300.00"),
            days_30=Decimal("300.00"),
            days_60=Decimal("300.00"),
            days_90_plus=Decimal("300.00"),
        )

        # Pay $500 - should pay off 90+ and part of 60
        new_bucket = ARCollectionsGenerator.allocate_partial_payment(
            bucket,
            Decimal("500.00"),
        )

        assert new_bucket.days_90_plus == Decimal("0.00")  # Paid off
        assert new_bucket.days_60 == Decimal("100.00")  # $300 - $200 remaining
        assert new_bucket.days_30 == Decimal("300.00")  # Unchanged
        assert new_bucket.current == Decimal("300.00")  # Unchanged

    def test_allocate_full_payment(self):
        """Test that full payment clears all aging buckets."""
        bucket = ARCollectionsGenerator.create_aging_bucket(
            current=Decimal("300.00"),
            days_30=Decimal("200.00"),
            days_60=Decimal("100.00"),
        )

        # Pay total amount
        new_bucket = ARCollectionsGenerator.allocate_partial_payment(
            bucket,
            bucket.total,
        )

        assert new_bucket.total == Decimal("0.00")
        assert new_bucket.current == Decimal("0.00")
        assert new_bucket.days_30 == Decimal("0.00")
        assert new_bucket.days_60 == Decimal("0.00")

    def test_overpayment_does_not_create_negative_balance(self):
        """Test that overpayment doesn't create negative balances."""
        bucket = ARCollectionsGenerator.create_aging_bucket(
            current=Decimal("100.00"),
        )

        # Overpay by $50
        new_bucket = ARCollectionsGenerator.allocate_partial_payment(
            bucket,
            Decimal("150.00"),
        )

        # Should not go negative
        assert new_bucket.current >= Decimal("0.00")
        assert new_bucket.total >= Decimal("0.00")


class TestPaymentPlans:
    """Tests for payment plan functionality."""

    def test_create_payment_plan(self):
        """Test creating a payment plan."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        plan = ARCollectionsGenerator.create_payment_plan(
            member_id=member.id,
            property_id=property.id,
            total_amount=Decimal("900.00"),
            down_payment=Decimal("150.00"),
            num_installments=6,
        )

        assert plan.total_amount == Decimal("900.00")
        assert plan.down_payment == Decimal("150.00")
        assert plan.num_installments == 6
        assert plan.status == PaymentPlanStatus.ACTIVE

        # Calculate installment amount
        remaining = Decimal("900.00") - Decimal("150.00")  # $750
        expected_installment = remaining / Decimal("6")  # $125/month
        assert plan.installment_amount == expected_installment

    def test_payment_plan_calculates_installments(self):
        """Test that payment plan calculates installments correctly."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        plan = ARCollectionsGenerator.create_payment_plan(
            member_id=member.id,
            property_id=property.id,
            total_amount=Decimal("600.00"),
            down_payment=Decimal("0.00"),
            num_installments=4,
        )

        # $600 / 4 = $150 per installment
        assert plan.installment_amount == Decimal("150.00")

    def test_payment_plan_with_zero_down_payment(self):
        """Test payment plan with no down payment."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        plan = ARCollectionsGenerator.create_payment_plan(
            member_id=member.id,
            property_id=property.id,
            total_amount=Decimal("600.00"),
            down_payment=Decimal("0.00"),
            num_installments=6,
        )

        assert plan.down_payment == Decimal("0.00")
        assert plan.remaining_balance == Decimal("600.00")

    def test_payment_plan_next_payment_date(self):
        """Test that payment plan sets next payment date."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        plan = ARCollectionsGenerator.create_payment_plan(
            member_id=member.id,
            property_id=property.id,
            total_amount=Decimal("600.00"),
            num_installments=6,
        )

        # Next payment should be 30 days from start
        expected_next = plan.start_date + timedelta(days=30)
        assert plan.next_payment_date == expected_next


class TestCollectionsWorkflow:
    """Tests for complete collections workflow."""

    def test_create_collections_workflow(self):
        """Test creating a complete collections workflow."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        workflow = ARCollectionsGenerator.create_collections_workflow(
            property_id=property.id,
            member_id=member.id,
            balance_owed=Decimal("900.00"),
        )

        assert workflow["member_id"] == member.id
        assert workflow["balance_owed"] == Decimal("900.00")
        assert len(workflow["collection_letters"]) == 3
        assert len(workflow["collection_calls"]) == 3
        assert workflow["payment_plan"] is not None

    def test_collections_workflow_escalation(self):
        """Test that collections workflow escalates properly."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        workflow = ARCollectionsGenerator.create_collections_workflow(
            property_id=property.id,
            member_id=member.id,
            balance_owed=Decimal("900.00"),
        )

        letters = workflow["collection_letters"]

        # Should escalate: friendly -> first notice -> final notice
        assert letters[0]["type"] == "friendly_reminder"
        assert letters[1]["type"] == "first_notice"
        assert letters[2]["type"] == "final_notice"

        # Days past due should increase
        assert letters[1]["days_past_due"] > letters[0]["days_past_due"]
        assert letters[2]["days_past_due"] > letters[1]["days_past_due"]

    def test_collections_workflow_offers_payment_plan(self):
        """Test that collections workflow offers payment plan."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        workflow = ARCollectionsGenerator.create_collections_workflow(
            property_id=property.id,
            member_id=member.id,
            balance_owed=Decimal("900.00"),
        )

        payment_plan = workflow["payment_plan"]

        assert payment_plan is not None
        assert payment_plan.status == PaymentPlanStatus.ACTIVE
        assert payment_plan.total_amount == Decimal("900.00")

    def test_collections_workflow_legal_action_threshold(self):
        """Test that legal action triggers for high balances."""
        property = PropertyGenerator.create()
        member = MemberGenerator.create(property_id=property.id)

        # High balance should trigger legal action
        workflow_high = ARCollectionsGenerator.create_collections_workflow(
            property_id=property.id,
            member_id=member.id,
            balance_owed=Decimal("1500.00"),
        )

        assert workflow_high["legal_action"] is True

        # Low balance should not trigger legal action
        workflow_low = ARCollectionsGenerator.create_collections_workflow(
            property_id=property.id,
            member_id=member.id,
            balance_owed=Decimal("500.00"),
        )

        assert workflow_low["legal_action"] is False
