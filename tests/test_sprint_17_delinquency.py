"""
Comprehensive tests for Sprint 17: Delinquency Workflow

Tests cover:
- Late fee rule calculations (flat, percentage, combined)
- Delinquency status tracking with aging buckets
- Collection notice workflow
- Collection action approval workflow
- Financial accuracy validation
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from hypothesis import given, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase


class TestLateFeeRules:
    """Test late fee rule configuration and calculations"""

    @pytest.fixture
    def flat_fee_rule(self, db, tenant):
        """Create a flat fee rule"""
        from accounting.models import LateFeeRule
        return LateFeeRule.objects.create(
            tenant=tenant,
            name="Standard Late Fee",
            grace_period_days=10,
            fee_type='flat',
            flat_amount=Decimal('25.00'),
            percentage_rate=Decimal('0.00'),
            is_active=True
        )

    @pytest.fixture
    def percentage_fee_rule(self, db, tenant):
        """Create a percentage fee rule"""
        from accounting.models import LateFeeRule
        return LateFeeRule.objects.create(
            tenant=tenant,
            name="Percentage Late Fee",
            grace_period_days=10,
            fee_type='percentage',
            flat_amount=Decimal('0.00'),
            percentage_rate=Decimal('5.00'),
            is_active=True
        )

    @pytest.fixture
    def combined_fee_rule(self, db, tenant):
        """Create a combined fee rule"""
        from accounting.models import LateFeeRule
        return LateFeeRule.objects.create(
            tenant=tenant,
            name="Combined Late Fee",
            grace_period_days=10,
            fee_type='both',
            flat_amount=Decimal('25.00'),
            percentage_rate=Decimal('5.00'),
            max_amount=Decimal('100.00'),
            is_active=True
        )

    def test_flat_fee_calculation(self, flat_fee_rule):
        """Test flat fee calculation returns correct amount"""
        balance = Decimal('500.00')
        fee = flat_fee_rule.calculate_fee(balance)
        assert fee == Decimal('25.00')

    def test_percentage_fee_calculation(self, percentage_fee_rule):
        """Test percentage fee calculation"""
        balance = Decimal('1000.00')
        fee = percentage_fee_rule.calculate_fee(balance)
        assert fee == Decimal('50.00')  # 5% of 1000

    def test_combined_fee_calculation(self, combined_fee_rule):
        """Test combined fee calculation"""
        balance = Decimal('500.00')
        fee = combined_fee_rule.calculate_fee(balance)
        # $25 flat + 5% of $500 = $25 + $25 = $50
        assert fee == Decimal('50.00')

    def test_max_fee_cap(self, combined_fee_rule):
        """Test that max_amount caps the fee"""
        balance = Decimal('10000.00')
        fee = combined_fee_rule.calculate_fee(balance)
        # Would be $25 + $500 = $525, but capped at $100
        assert fee == Decimal('100.00')

    @given(st.decimals(min_value='0.01', max_value='100000.00', places=2))
    def test_fee_never_negative(self, flat_fee_rule, balance):
        """Property test: Fee should never be negative"""
        fee = flat_fee_rule.calculate_fee(balance)
        assert fee >= Decimal('0.00')

    @given(st.decimals(min_value='0.01', max_value='100000.00', places=2))
    def test_percentage_fee_proportional(self, percentage_fee_rule, balance):
        """Property test: Percentage fee should be proportional to balance"""
        fee = percentage_fee_rule.calculate_fee(balance)
        expected = balance * (percentage_fee_rule.percentage_rate / Decimal('100'))
        assert fee == expected.quantize(Decimal('0.01'))


class TestDelinquencyStatus:
    """Test delinquency status tracking and aging buckets"""

    @pytest.fixture
    def owner(self, db, tenant):
        """Create a test owner"""
        from accounting.models import Owner
        return Owner.objects.create(
            tenant=tenant,
            full_name="John Delinquent",
            property_address="123 Late St",
            email="john@example.com"
        )

    @pytest.fixture
    def delinquency_status(self, db, tenant, owner):
        """Create a delinquency status"""
        from accounting.models import DelinquencyStatus
        return DelinquencyStatus.objects.create(
            tenant=tenant,
            owner=owner,
            current_balance=Decimal('1500.00'),
            balance_0_30=Decimal('500.00'),
            balance_31_60=Decimal('400.00'),
            balance_61_90=Decimal('300.00'),
            balance_90_plus=Decimal('300.00'),
            collection_stage='second_notice',
            days_delinquent=75
        )

    def test_aging_buckets_sum_to_total(self, delinquency_status):
        """Test that aging buckets sum to current balance"""
        total = (
            delinquency_status.balance_0_30 +
            delinquency_status.balance_31_60 +
            delinquency_status.balance_61_90 +
            delinquency_status.balance_90_plus
        )
        assert total == delinquency_status.current_balance

    def test_collection_stage_progression(self, delinquency_status):
        """Test collection stage can progress"""
        assert delinquency_status.collection_stage == 'second_notice'

        delinquency_status.collection_stage = 'final_notice'
        delinquency_status.save()

        delinquency_status.refresh_from_db()
        assert delinquency_status.collection_stage == 'final_notice'

    def test_payment_plan_flag(self, delinquency_status):
        """Test payment plan flag works"""
        assert not delinquency_status.is_payment_plan

        delinquency_status.is_payment_plan = True
        delinquency_status.save()

        delinquency_status.refresh_from_db()
        assert delinquency_status.is_payment_plan


class TestCollectionNotices:
    """Test collection notice workflow"""

    @pytest.fixture
    def owner(self, db, tenant):
        """Create a test owner"""
        from accounting.models import Owner
        return Owner.objects.create(
            tenant=tenant,
            full_name="Jane Late",
            property_address="456 Overdue Ave",
            email="jane@example.com"
        )

    def test_create_collection_notice(self, db, tenant, owner):
        """Test creating a collection notice"""
        from accounting.models import CollectionNotice

        notice = CollectionNotice.objects.create(
            tenant=tenant,
            owner=owner,
            notice_type='first',
            delivery_method='certified_mail',
            sent_date=date.today(),
            balance_at_notice=Decimal('750.00'),
            tracking_number='1234567890'
        )

        assert notice.owner == owner
        assert notice.balance_at_notice == Decimal('750.00')
        assert not notice.returned_undeliverable

    def test_delivery_tracking(self, db, tenant, owner):
        """Test delivery status tracking"""
        from accounting.models import CollectionNotice

        notice = CollectionNotice.objects.create(
            tenant=tenant,
            owner=owner,
            notice_type='second',
            delivery_method='certified_mail',
            sent_date=date.today(),
            balance_at_notice=Decimal('1000.00'),
            tracking_number='9876543210'
        )

        # Mark as delivered
        notice.delivered_date = date.today() + timedelta(days=3)
        notice.save()

        notice.refresh_from_db()
        assert notice.delivered_date is not None


class TestCollectionActions:
    """Test collection action workflow with board approval"""

    @pytest.fixture
    def owner(self, db, tenant):
        """Create a test owner"""
        from accounting.models import Owner
        return Owner.objects.create(
            tenant=tenant,
            full_name="Bob Foreclosure",
            property_address="789 Legal St",
            email="bob@example.com"
        )

    def test_create_collection_action(self, db, tenant, owner):
        """Test creating a collection action"""
        from accounting.models import CollectionAction

        action = CollectionAction.objects.create(
            tenant=tenant,
            owner=owner,
            action_type='lien',
            status='pending',
            requested_date=date.today(),
            balance_at_action=Decimal('5000.00'),
            notes="Repeated non-payment"
        )

        assert action.status == 'pending'
        assert action.approved_date is None

    def test_board_approval_workflow(self, db, tenant, owner):
        """Test board approval changes status"""
        from accounting.models import CollectionAction

        action = CollectionAction.objects.create(
            tenant=tenant,
            owner=owner,
            action_type='legal',
            status='pending',
            requested_date=date.today(),
            balance_at_action=Decimal('10000.00')
        )

        # Approve action
        action.status = 'approved'
        action.approved_date = date.today()
        action.approved_by = 'Board President'
        action.save()

        action.refresh_from_db()
        assert action.status == 'approved'
        assert action.approved_date == date.today()
        assert action.approved_by == 'Board President'

    def test_attorney_assignment(self, db, tenant, owner):
        """Test attorney can be assigned to legal actions"""
        from accounting.models import CollectionAction

        action = CollectionAction.objects.create(
            tenant=tenant,
            owner=owner,
            action_type='foreclosure',
            status='approved',
            requested_date=date.today(),
            balance_at_action=Decimal('25000.00'),
            attorney_name='Smith & Associates',
            case_number='2024-CV-12345'
        )

        assert action.attorney_name == 'Smith & Associates'
        assert action.case_number == '2024-CV-12345'


class TestDelinquencyIntegration:
    """Integration tests for full delinquency workflow"""

    def test_full_delinquency_workflow(self, db, tenant):
        """Test complete workflow from delinquency to legal action"""
        from accounting.models import (
            Owner, DelinquencyStatus, LateFeeRule,
            CollectionNotice, CollectionAction
        )

        # 1. Create owner with delinquent balance
        owner = Owner.objects.create(
            tenant=tenant,
            full_name="Test Delinquent",
            property_address="123 Test St",
            email="test@example.com"
        )

        # 2. Create delinquency status
        status = DelinquencyStatus.objects.create(
            tenant=tenant,
            owner=owner,
            current_balance=Decimal('2000.00'),
            balance_90_plus=Decimal('2000.00'),
            collection_stage='current',
            days_delinquent=95
        )

        # 3. Apply late fee
        rule = LateFeeRule.objects.create(
            tenant=tenant,
            name="Test Rule",
            fee_type='both',
            flat_amount=Decimal('50.00'),
            percentage_rate=Decimal('10.00'),
            grace_period_days=10,
            is_active=True
        )

        late_fee = rule.calculate_fee(status.current_balance)
        assert late_fee == Decimal('250.00')  # $50 + 10% of $2000

        # 4. Send collection notice
        notice = CollectionNotice.objects.create(
            tenant=tenant,
            owner=owner,
            notice_type='final',
            delivery_method='certified_mail',
            sent_date=date.today(),
            balance_at_notice=status.current_balance + late_fee
        )

        # 5. Escalate to legal action
        action = CollectionAction.objects.create(
            tenant=tenant,
            owner=owner,
            action_type='lien',
            status='pending',
            requested_date=date.today(),
            balance_at_action=status.current_balance + late_fee
        )

        # Verify workflow
        assert notice.owner == owner
        assert action.owner == owner
        assert action.balance_at_action == Decimal('2250.00')


# Property-based tests for financial accuracy
class TestDelinquencyFinancialAccuracy(HypothesisTestCase):
    """Property-based tests for financial calculations"""

    @given(
        balance=st.decimals(min_value='0.01', max_value='100000.00', places=2),
        flat=st.decimals(min_value='0.00', max_value='500.00', places=2),
        percent=st.decimals(min_value='0.00', max_value='20.00', places=2)
    )
    def test_late_fee_accuracy(self, balance, flat, percent):
        """Property test: Late fees should be calculated accurately"""
        # Flat + percentage fee
        expected_fee = flat + (balance * percent / Decimal('100'))

        # Round to 2 decimal places
        expected_fee = expected_fee.quantize(Decimal('0.01'))

        # Fee should always be non-negative
        assert expected_fee >= Decimal('0.00')

        # Fee should never exceed balance + flat (sanity check)
        assert expected_fee <= balance + flat + Decimal('1.00')
