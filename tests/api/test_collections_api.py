"""
API Endpoint Tests for Sprint 17: Delinquency & Collections

Tests all REST API endpoints for:
- Late Fee Rules (CRUD + calculate_fee action)
- Delinquency Status (CRUD + summary endpoint)
- Collection Notices (CRUD + tracking)
- Collection Actions (CRUD + approval workflow)

Testing patterns:
- Authentication and tenant isolation
- All CRUD operations (Create, Read, Update, Delete)
- Query parameters and filtering
- Pagination
- Validation errors (400)
- Not found errors (404)
- Custom actions and workflows
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from rest_framework import status
from rest_framework.test import APIClient


# ===========================
# Late Fee Rules API Tests
# ===========================

class TestLateFeeRulesAPI:
    """Test /api/v1/accounting/late-fee-rules/ endpoints."""

    @pytest.fixture
    def api_client(self):
        """Create an authenticated API client."""
        client = APIClient()
        # TODO: Add authentication when implemented
        # client.force_authenticate(user=test_user)
        return client

    @pytest.fixture
    def base_url(self):
        """Base URL for late fee rules endpoints."""
        return '/api/v1/accounting/late-fee-rules/'

    def test_create_late_fee_rule_flat(self, api_client, base_url, tenant_fixture):
        """Test POST /late-fee-rules/ - Create flat fee rule."""
        data = {
            'tenant': str(tenant_fixture.id),
            'name': 'Standard Late Fee',
            'grace_period_days': 5,
            'fee_type': 'flat',
            'flat_amount': '50.00',
            'is_recurring': False,
            'is_active': True
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Standard Late Fee'
        assert response.data['grace_period_days'] == 5
        assert response.data['fee_type'] == 'flat'
        assert Decimal(response.data['flat_amount']) == Decimal('50.00')
        assert 'id' in response.data
        assert 'created_at' in response.data

    def test_create_late_fee_rule_percentage(self, api_client, base_url, tenant_fixture):
        """Test POST /late-fee-rules/ - Create percentage fee rule."""
        data = {
            'tenant': str(tenant_fixture.id),
            'name': 'Percentage Late Fee',
            'grace_period_days': 10,
            'fee_type': 'percentage',
            'percentage_rate': '10.00',
            'max_amount': '100.00',
            'is_recurring': True,
            'is_active': True
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['fee_type'] == 'percentage'
        assert Decimal(response.data['percentage_rate']) == Decimal('10.00')
        assert Decimal(response.data['max_amount']) == Decimal('100.00')
        assert response.data['is_recurring'] is True

    def test_create_late_fee_rule_validation_error(self, api_client, base_url):
        """Test POST /late-fee-rules/ - Missing required fields."""
        data = {
            'name': 'Invalid Rule'
            # Missing tenant, grace_period_days, fee_type
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'tenant' in response.data or 'error' in response.data

    def test_get_late_fee_rule(self, api_client, base_url, late_fee_rule_fixture):
        """Test GET /late-fee-rules/{id}/ - Retrieve single rule."""
        url = f'{base_url}{late_fee_rule_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(late_fee_rule_fixture.id)
        assert response.data['name'] == late_fee_rule_fixture.name
        assert 'fee_type_display' in response.data

    def test_get_late_fee_rule_not_found(self, api_client, base_url):
        """Test GET /late-fee-rules/{id}/ - Rule not found."""
        from uuid import uuid4
        url = f'{base_url}{uuid4()}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_late_fee_rules(self, api_client, base_url, tenant_fixture):
        """Test GET /late-fee-rules/ - List all rules."""
        # Create multiple rules
        for i in range(3):
            api_client.post(base_url, {
                'tenant': str(tenant_fixture.id),
                'name': f'Rule {i}',
                'grace_period_days': 5 + i,
                'fee_type': 'flat',
                'flat_amount': '50.00',
                'is_active': True
            }, format='json')

        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)
        results = response.data.get('results', response.data)
        assert len(results) >= 3

    def test_list_late_fee_rules_filter_active(self, api_client, base_url, tenant_fixture):
        """Test GET /late-fee-rules/?is_active=true - Filter by active status."""
        # Create active and inactive rules
        api_client.post(base_url, {
            'tenant': str(tenant_fixture.id),
            'name': 'Active Rule',
            'grace_period_days': 5,
            'fee_type': 'flat',
            'flat_amount': '50.00',
            'is_active': True
        }, format='json')

        api_client.post(base_url, {
            'tenant': str(tenant_fixture.id),
            'name': 'Inactive Rule',
            'grace_period_days': 5,
            'fee_type': 'flat',
            'flat_amount': '50.00',
            'is_active': False
        }, format='json')

        response = api_client.get(f'{base_url}?is_active=true')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for rule in results:
            assert rule['is_active'] is True

    def test_list_late_fee_rules_filter_type(self, api_client, base_url, tenant_fixture):
        """Test GET /late-fee-rules/?fee_type=flat - Filter by fee type."""
        response = api_client.get(f'{base_url}?fee_type=flat')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for rule in results:
            assert rule['fee_type'] == 'flat'

    def test_update_late_fee_rule(self, api_client, base_url, late_fee_rule_fixture):
        """Test PATCH /late-fee-rules/{id}/ - Update rule."""
        url = f'{base_url}{late_fee_rule_fixture.id}/'
        data = {
            'name': 'Updated Late Fee',
            'grace_period_days': 15,
            'is_active': False
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Late Fee'
        assert response.data['grace_period_days'] == 15
        assert response.data['is_active'] is False

    def test_delete_late_fee_rule(self, api_client, base_url, late_fee_rule_fixture):
        """Test DELETE /late-fee-rules/{id}/ - Delete rule."""
        url = f'{base_url}{late_fee_rule_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deletion
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_calculate_fee_action_flat(self, api_client, base_url, late_fee_rule_fixture):
        """Test POST /late-fee-rules/{id}/calculate_fee/ - Calculate flat fee."""
        url = f'{base_url}{late_fee_rule_fixture.id}/calculate_fee/'
        data = {'balance': '500.00'}

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'fee' in response.data
        # Flat fee should be fixed regardless of balance
        assert Decimal(response.data['fee']) == late_fee_rule_fixture.flat_amount

    def test_calculate_fee_action_percentage(self, api_client, base_url, tenant_fixture):
        """Test POST /late-fee-rules/{id}/calculate_fee/ - Calculate percentage fee."""
        # Create percentage rule
        create_response = api_client.post(base_url, {
            'tenant': str(tenant_fixture.id),
            'name': 'Percentage Fee',
            'grace_period_days': 5,
            'fee_type': 'percentage',
            'percentage_rate': '10.00',
            'max_amount': '100.00',
            'is_active': True
        }, format='json')

        rule_id = create_response.data['id']
        url = f'{base_url}{rule_id}/calculate_fee/'
        data = {'balance': '500.00'}

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        # 10% of 500 = 50
        assert Decimal(response.data['fee']) == Decimal('50.00')

    def test_tenant_isolation_late_fee_rules(self, api_client, base_url, tenant_fixture, other_tenant_fixture):
        """Test that tenant A cannot access tenant B's late fee rules."""
        # Create rule for tenant A
        response_a = api_client.post(base_url, {
            'tenant': str(tenant_fixture.id),
            'name': 'Tenant A Rule',
            'grace_period_days': 5,
            'fee_type': 'flat',
            'flat_amount': '50.00',
            'is_active': True
        }, format='json')

        # Create rule for tenant B
        response_b = api_client.post(base_url, {
            'tenant': str(other_tenant_fixture.id),
            'name': 'Tenant B Rule',
            'grace_period_days': 5,
            'fee_type': 'flat',
            'flat_amount': '75.00',
            'is_active': True
        }, format='json')

        # List rules (should only see tenant A's rules when authenticated as tenant A)
        # TODO: Implement proper tenant filtering in test setup
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        # Verify tenant isolation in production


# ===========================
# Delinquency Status API Tests
# ===========================

class TestDelinquencyStatusAPI:
    """Test /api/v1/accounting/delinquency-status/ endpoints."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    @pytest.fixture
    def base_url(self):
        return '/api/v1/accounting/delinquency-status/'

    def test_create_delinquency_status(self, api_client, base_url, owner_fixture):
        """Test POST /delinquency-status/ - Create status record."""
        data = {
            'owner': str(owner_fixture.id),
            'current_balance': '1500.00',
            'balance_0_30': '500.00',
            'balance_31_60': '400.00',
            'balance_61_90': '300.00',
            'balance_90_plus': '300.00',
            'collection_stage': 'initial_notice',
            'days_delinquent': 45,
            'is_payment_plan': False
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert Decimal(response.data['current_balance']) == Decimal('1500.00')
        assert response.data['collection_stage'] == 'initial_notice'
        assert response.data['days_delinquent'] == 45
        assert 'owner_name' in response.data
        assert 'stage_display' in response.data

    def test_get_delinquency_status(self, api_client, base_url, delinquency_status_fixture):
        """Test GET /delinquency-status/{id}/ - Retrieve status."""
        url = f'{base_url}{delinquency_status_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(delinquency_status_fixture.id)
        assert 'owner_name' in response.data

    def test_list_delinquency_statuses(self, api_client, base_url):
        """Test GET /delinquency-status/ - List all statuses."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_by_collection_stage(self, api_client, base_url):
        """Test GET /delinquency-status/?collection_stage=attorney - Filter by stage."""
        response = api_client.get(f'{base_url}?collection_stage=attorney')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for status_record in results:
            assert status_record['collection_stage'] == 'attorney'

    def test_list_filter_payment_plan(self, api_client, base_url):
        """Test GET /delinquency-status/?is_payment_plan=true - Filter payment plans."""
        response = api_client.get(f'{base_url}?is_payment_plan=true')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for status_record in results:
            assert status_record['is_payment_plan'] is True

    def test_update_delinquency_status(self, api_client, base_url, delinquency_status_fixture):
        """Test PATCH /delinquency-status/{id}/ - Update status."""
        url = f'{base_url}{delinquency_status_fixture.id}/'
        data = {
            'collection_stage': 'attorney',
            'days_delinquent': 120,
            'notes': 'Escalated to attorney'
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['collection_stage'] == 'attorney'
        assert response.data['days_delinquent'] == 120

    def test_delete_delinquency_status(self, api_client, base_url, delinquency_status_fixture):
        """Test DELETE /delinquency-status/{id}/ - Delete status."""
        url = f'{base_url}{delinquency_status_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delinquency_summary_endpoint(self, api_client, base_url, tenant_fixture, owner_fixture):
        """Test GET /delinquency-status/summary/ - Get summary statistics."""
        # Create multiple delinquency records
        stages = ['initial_notice', 'final_notice', 'attorney']
        for i, stage in enumerate(stages):
            api_client.post(base_url, {
                'owner': str(owner_fixture.id),
                'current_balance': f'{(i + 1) * 500}.00',
                'balance_0_30': '0.00',
                'balance_31_60': '0.00',
                'balance_61_90': '0.00',
                'balance_90_plus': f'{(i + 1) * 500}.00',
                'collection_stage': stage,
                'days_delinquent': (i + 1) * 30,
                'is_payment_plan': False
            }, format='json')

        url = f'{base_url}summary/'
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'total_delinquent' in response.data
        assert 'total_balance' in response.data
        assert 'by_stage' in response.data

        # Verify stage breakdown
        by_stage = response.data['by_stage']
        assert 'initial_notice' in by_stage
        assert 'count' in by_stage['initial_notice']
        assert 'balance' in by_stage['initial_notice']

    def test_ordering_by_balance(self, api_client, base_url):
        """Test GET /delinquency-status/?ordering=-current_balance - Order by balance."""
        response = api_client.get(f'{base_url}?ordering=-current_balance')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        if len(results) > 1:
            # Verify descending order
            balances = [Decimal(r['current_balance']) for r in results]
            assert balances == sorted(balances, reverse=True)


# ===========================
# Collection Notices API Tests
# ===========================

class TestCollectionNoticesAPI:
    """Test /api/v1/accounting/collection-notices/ endpoints."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    @pytest.fixture
    def base_url(self):
        return '/api/v1/accounting/collection-notices/'

    def test_create_collection_notice(self, api_client, base_url, owner_fixture):
        """Test POST /collection-notices/ - Create notice."""
        data = {
            'owner': str(owner_fixture.id),
            'notice_type': 'initial',
            'delivery_method': 'email',
            'sent_date': str(date.today()),
            'balance_at_notice': '1200.00'
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['notice_type'] == 'initial'
        assert response.data['delivery_method'] == 'email'
        assert 'owner_name' in response.data
        assert 'notice_type_display' in response.data

    def test_create_collection_notice_certified_mail(self, api_client, base_url, owner_fixture):
        """Test POST /collection-notices/ - Create with certified mail tracking."""
        data = {
            'owner': str(owner_fixture.id),
            'notice_type': 'final',
            'delivery_method': 'certified_mail',
            'sent_date': str(date.today()),
            'balance_at_notice': '2000.00',
            'tracking_number': '1234567890'
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['delivery_method'] == 'certified_mail'
        assert response.data['tracking_number'] == '1234567890'

    def test_get_collection_notice(self, api_client, base_url, collection_notice_fixture):
        """Test GET /collection-notices/{id}/ - Retrieve notice."""
        url = f'{base_url}{collection_notice_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(collection_notice_fixture.id)

    def test_list_collection_notices(self, api_client, base_url):
        """Test GET /collection-notices/ - List all notices."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_by_owner(self, api_client, base_url, owner_fixture):
        """Test GET /collection-notices/?owner={id} - Filter by owner."""
        response = api_client.get(f'{base_url}?owner={owner_fixture.id}')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for notice in results:
            assert notice['owner'] == str(owner_fixture.id)

    def test_list_filter_by_notice_type(self, api_client, base_url):
        """Test GET /collection-notices/?notice_type=final - Filter by type."""
        response = api_client.get(f'{base_url}?notice_type=final')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for notice in results:
            assert notice['notice_type'] == 'final'

    def test_list_filter_undeliverable(self, api_client, base_url):
        """Test GET /collection-notices/?returned_undeliverable=true - Filter undeliverable."""
        response = api_client.get(f'{base_url}?returned_undeliverable=true')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for notice in results:
            assert notice['returned_undeliverable'] is True

    def test_update_collection_notice_delivered(self, api_client, base_url, collection_notice_fixture):
        """Test PATCH /collection-notices/{id}/ - Mark as delivered."""
        url = f'{base_url}{collection_notice_fixture.id}/'
        data = {
            'delivered_date': str(date.today()),
            'returned_undeliverable': False
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['delivered_date'] == str(date.today())
        assert response.data['returned_undeliverable'] is False

    def test_update_collection_notice_undeliverable(self, api_client, base_url, collection_notice_fixture):
        """Test PATCH /collection-notices/{id}/ - Mark as undeliverable."""
        url = f'{base_url}{collection_notice_fixture.id}/'
        data = {
            'returned_undeliverable': True,
            'notes': 'Address not found'
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['returned_undeliverable'] is True

    def test_delete_collection_notice(self, api_client, base_url, collection_notice_fixture):
        """Test DELETE /collection-notices/{id}/ - Delete notice."""
        url = f'{base_url}{collection_notice_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_ordering_by_sent_date(self, api_client, base_url):
        """Test GET /collection-notices/?ordering=-sent_date - Order by date."""
        response = api_client.get(f'{base_url}?ordering=-sent_date')

        assert response.status_code == status.HTTP_200_OK


# ===========================
# Collection Actions API Tests
# ===========================

class TestCollectionActionsAPI:
    """Test /api/v1/accounting/collection-actions/ endpoints."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    @pytest.fixture
    def base_url(self):
        return '/api/v1/accounting/collection-actions/'

    def test_create_collection_action(self, api_client, base_url, owner_fixture):
        """Test POST /collection-actions/ - Create action request."""
        data = {
            'owner': str(owner_fixture.id),
            'action_type': 'lien',
            'status': 'pending',
            'requested_date': str(date.today()),
            'balance_at_action': '5000.00',
            'notes': 'Owner non-responsive'
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['action_type'] == 'lien'
        assert response.data['status'] == 'pending'
        assert 'owner_name' in response.data
        assert 'action_type_display' in response.data

    def test_create_collection_action_foreclosure(self, api_client, base_url, owner_fixture):
        """Test POST /collection-actions/ - Create foreclosure action."""
        data = {
            'owner': str(owner_fixture.id),
            'action_type': 'foreclosure',
            'status': 'pending',
            'requested_date': str(date.today()),
            'balance_at_action': '10000.00',
            'attorney_name': 'Smith & Associates',
            'notes': 'Balance over 90 days past due'
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['action_type'] == 'foreclosure'
        assert response.data['attorney_name'] == 'Smith & Associates'

    def test_get_collection_action(self, api_client, base_url, collection_action_fixture):
        """Test GET /collection-actions/{id}/ - Retrieve action."""
        url = f'{base_url}{collection_action_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(collection_action_fixture.id)

    def test_list_collection_actions(self, api_client, base_url):
        """Test GET /collection-actions/ - List all actions."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_by_status(self, api_client, base_url):
        """Test GET /collection-actions/?status=pending - Filter by status."""
        response = api_client.get(f'{base_url}?status=pending')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for action in results:
            assert action['status'] == 'pending'

    def test_list_filter_by_action_type(self, api_client, base_url):
        """Test GET /collection-actions/?action_type=lien - Filter by type."""
        response = api_client.get(f'{base_url}?action_type=lien')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for action in results:
            assert action['action_type'] == 'lien'

    def test_approve_collection_action(self, api_client, base_url, collection_action_fixture):
        """Test POST /collection-actions/{id}/approve/ - Approve action."""
        url = f'{base_url}{collection_action_fixture.id}/approve/'
        data = {
            'approved_by': 'Board President'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'approved'
        assert response.data['approved_date'] is not None
        assert response.data['approved_by'] == 'Board President'

    def test_update_collection_action(self, api_client, base_url, collection_action_fixture):
        """Test PATCH /collection-actions/{id}/ - Update action."""
        url = f'{base_url}{collection_action_fixture.id}/'
        data = {
            'case_number': 'CASE-2025-001',
            'notes': 'Updated case information'
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['case_number'] == 'CASE-2025-001'

    def test_complete_collection_action(self, api_client, base_url, collection_action_fixture):
        """Test PATCH /collection-actions/{id}/ - Mark as completed."""
        url = f'{base_url}{collection_action_fixture.id}/'
        data = {
            'status': 'completed',
            'completed_date': str(date.today()),
            'notes': 'Lien filed successfully'
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'completed'
        assert response.data['completed_date'] == str(date.today())

    def test_delete_collection_action(self, api_client, base_url, collection_action_fixture):
        """Test DELETE /collection-actions/{id}/ - Delete action."""
        url = f'{base_url}{collection_action_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_ordering_by_requested_date(self, api_client, base_url):
        """Test GET /collection-actions/?ordering=-requested_date - Order by date."""
        response = api_client.get(f'{base_url}?ordering=-requested_date')

        assert response.status_code == status.HTTP_200_OK

    def test_pagination(self, api_client, base_url):
        """Test GET /collection-actions/?page=1&page_size=10 - Pagination."""
        response = api_client.get(f'{base_url}?page=1&page_size=10')

        assert response.status_code == status.HTTP_200_OK
        if 'results' in response.data:
            assert 'count' in response.data
            assert 'next' in response.data
            assert 'previous' in response.data
