"""
API Endpoint Tests for Sprint 18: Auto-Matching Engine

Tests all REST API endpoints for:
- Auto Match Rules (CRUD + learned patterns)
- Match Results (CRUD + accept action)
- Match Statistics (Read-only + performance tracking)

Testing patterns:
- Authentication and tenant isolation
- All CRUD operations
- Query parameters and filtering
- Pagination
- Validation errors (400)
- Not found errors (404)
- Custom actions (accept matches)
- Machine learning patterns (confidence scores, accuracy rates)
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from rest_framework import status
from rest_framework.test import APIClient


# ===========================
# Auto Match Rules API Tests
# ===========================

class TestAutoMatchRulesAPI:
    """Test /api/v1/accounting/auto-match-rules/ endpoints."""

    @pytest.fixture
    def api_client(self):
        """Create an authenticated API client."""
        client = APIClient()
        # TODO: Add authentication when implemented
        return client

    @pytest.fixture
    def base_url(self):
        """Base URL for auto match rules endpoints."""
        return '/api/v1/accounting/auto-match-rules/'

    def test_create_auto_match_rule_amount(self, api_client, base_url, tenant_fixture):
        """Test POST /auto-match-rules/ - Create amount-based rule."""
        data = {
            'tenant': str(tenant_fixture.id),
            'rule_type': 'amount',
            'pattern': {'tolerance': 0.01, 'match_type': 'exact'},
            'confidence_score': 95,
            'is_active': True
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['rule_type'] == 'amount'
        assert response.data['confidence_score'] == 95
        assert response.data['times_used'] == 0
        assert response.data['accuracy_rate'] == '0.00'
        assert 'id' in response.data

    def test_create_auto_match_rule_description(self, api_client, base_url, tenant_fixture):
        """Test POST /auto-match-rules/ - Create description pattern rule."""
        data = {
            'tenant': str(tenant_fixture.id),
            'rule_type': 'description',
            'pattern': {
                'keywords': ['HOA DUES', 'ASSESSMENT'],
                'match_strategy': 'fuzzy'
            },
            'confidence_score': 85,
            'is_active': True
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['rule_type'] == 'description'
        assert 'keywords' in response.data['pattern']

    def test_create_auto_match_rule_date(self, api_client, base_url, tenant_fixture):
        """Test POST /auto-match-rules/ - Create date-based rule."""
        data = {
            'tenant': str(tenant_fixture.id),
            'rule_type': 'date',
            'pattern': {'tolerance_days': 3, 'direction': 'both'},
            'confidence_score': 80,
            'is_active': True
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['rule_type'] == 'date'
        assert response.data['pattern']['tolerance_days'] == 3

    def test_create_auto_match_rule_combo(self, api_client, base_url, tenant_fixture):
        """Test POST /auto-match-rules/ - Create combination rule."""
        data = {
            'tenant': str(tenant_fixture.id),
            'rule_type': 'combo',
            'pattern': {
                'amount_tolerance': 0.01,
                'date_tolerance_days': 3,
                'description_weight': 0.3,
                'amount_weight': 0.5,
                'date_weight': 0.2
            },
            'confidence_score': 90,
            'is_active': True
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['rule_type'] == 'combo'

    def test_create_auto_match_rule_validation_error(self, api_client, base_url):
        """Test POST /auto-match-rules/ - Missing required fields."""
        data = {
            'rule_type': 'amount'
            # Missing tenant, pattern, confidence_score
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_auto_match_rule(self, api_client, base_url, auto_match_rule_fixture):
        """Test GET /auto-match-rules/{id}/ - Retrieve single rule."""
        url = f'{base_url}{auto_match_rule_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(auto_match_rule_fixture.id)
        assert 'rule_type_display' in response.data
        assert 'times_used' in response.data
        assert 'accuracy_rate' in response.data

    def test_get_auto_match_rule_not_found(self, api_client, base_url):
        """Test GET /auto-match-rules/{id}/ - Rule not found."""
        from uuid import uuid4
        url = f'{base_url}{uuid4()}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_auto_match_rules(self, api_client, base_url):
        """Test GET /auto-match-rules/ - List all rules."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_by_rule_type(self, api_client, base_url):
        """Test GET /auto-match-rules/?rule_type=amount - Filter by type."""
        response = api_client.get(f'{base_url}?rule_type=amount')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for rule in results:
            assert rule['rule_type'] == 'amount'

    def test_list_filter_active_only(self, api_client, base_url):
        """Test GET /auto-match-rules/?is_active=true - Filter active rules."""
        response = api_client.get(f'{base_url}?is_active=true')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for rule in results:
            assert rule['is_active'] is True

    def test_list_order_by_accuracy(self, api_client, base_url):
        """Test GET /auto-match-rules/?ordering=-accuracy_rate - Order by accuracy."""
        response = api_client.get(f'{base_url}?ordering=-accuracy_rate')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        if len(results) > 1:
            accuracies = [Decimal(r['accuracy_rate']) for r in results]
            assert accuracies == sorted(accuracies, reverse=True)

    def test_list_order_by_times_used(self, api_client, base_url):
        """Test GET /auto-match-rules/?ordering=-times_used - Order by usage."""
        response = api_client.get(f'{base_url}?ordering=-times_used')

        assert response.status_code == status.HTTP_200_OK

    def test_update_auto_match_rule(self, api_client, base_url, auto_match_rule_fixture):
        """Test PATCH /auto-match-rules/{id}/ - Update rule."""
        url = f'{base_url}{auto_match_rule_fixture.id}/'
        data = {
            'confidence_score': 92,
            'is_active': False,
            'pattern': {'updated': True}
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['confidence_score'] == 92
        assert response.data['is_active'] is False

    def test_delete_auto_match_rule(self, api_client, base_url, auto_match_rule_fixture):
        """Test DELETE /auto-match-rules/{id}/ - Delete rule."""
        url = f'{base_url}{auto_match_rule_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deletion
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_rule_statistics_readonly(self, api_client, base_url, auto_match_rule_fixture):
        """Test that times_used and accuracy_rate are read-only."""
        url = f'{base_url}{auto_match_rule_fixture.id}/'
        data = {
            'times_used': 999,
            'times_correct': 999,
            'accuracy_rate': '100.00'
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        # Statistics should not change (they're read-only)
        assert response.data['times_used'] == auto_match_rule_fixture.times_used
        assert response.data['times_correct'] == auto_match_rule_fixture.times_correct

    def test_tenant_isolation_auto_match_rules(self, api_client, base_url, tenant_fixture, other_tenant_fixture):
        """Test that tenant A cannot access tenant B's auto match rules."""
        # Create rule for tenant A
        api_client.post(base_url, {
            'tenant': str(tenant_fixture.id),
            'rule_type': 'amount',
            'pattern': {'tolerance': 0.01},
            'confidence_score': 90,
            'is_active': True
        }, format='json')

        # Create rule for tenant B
        api_client.post(base_url, {
            'tenant': str(other_tenant_fixture.id),
            'rule_type': 'amount',
            'pattern': {'tolerance': 0.01},
            'confidence_score': 85,
            'is_active': True
        }, format='json')

        # List rules (should only see tenant A's rules when authenticated as tenant A)
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        # TODO: Verify tenant isolation when auth is implemented


# ===========================
# Match Results API Tests
# ===========================

class TestMatchResultsAPI:
    """Test /api/v1/accounting/match-results/ endpoints."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    @pytest.fixture
    def base_url(self):
        return '/api/v1/accounting/match-results/'

    def test_create_match_result(self, api_client, base_url, tenant_fixture, bank_transaction_fixture, journal_entry_fixture, auto_match_rule_fixture):
        """Test POST /match-results/ - Create match result."""
        data = {
            'tenant': str(tenant_fixture.id),
            'bank_transaction': str(bank_transaction_fixture.id),
            'matched_entry': str(journal_entry_fixture.id),
            'confidence_score': 92,
            'match_explanation': 'Exact amount and date match',
            'matched_by_rule': str(auto_match_rule_fixture.id),
            'was_accepted': False
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['confidence_score'] == 92
        assert response.data['was_accepted'] is False
        assert 'bank_transaction_description' in response.data
        assert 'matched_entry_reference' in response.data
        assert 'id' in response.data

    def test_create_match_result_manual(self, api_client, base_url, tenant_fixture, bank_transaction_fixture, journal_entry_fixture):
        """Test POST /match-results/ - Create manual match (no rule)."""
        data = {
            'tenant': str(tenant_fixture.id),
            'bank_transaction': str(bank_transaction_fixture.id),
            'matched_entry': str(journal_entry_fixture.id),
            'confidence_score': 100,
            'match_explanation': 'Manual match by user',
            'was_accepted': True
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['confidence_score'] == 100
        assert response.data['matched_by_rule'] is None

    def test_get_match_result(self, api_client, base_url, match_result_fixture):
        """Test GET /match-results/{id}/ - Retrieve match result."""
        url = f'{base_url}{match_result_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(match_result_fixture.id)

    def test_list_match_results(self, api_client, base_url):
        """Test GET /match-results/ - List all match results."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_by_bank_transaction(self, api_client, base_url, bank_transaction_fixture):
        """Test GET /match-results/?bank_transaction={id} - Filter by transaction."""
        response = api_client.get(f'{base_url}?bank_transaction={bank_transaction_fixture.id}')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for match in results:
            assert match['bank_transaction'] == str(bank_transaction_fixture.id)

    def test_list_filter_by_matched_entry(self, api_client, base_url, journal_entry_fixture):
        """Test GET /match-results/?matched_entry={id} - Filter by journal entry."""
        response = api_client.get(f'{base_url}?matched_entry={journal_entry_fixture.id}')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for match in results:
            assert match['matched_entry'] == str(journal_entry_fixture.id)

    def test_list_filter_accepted_only(self, api_client, base_url):
        """Test GET /match-results/?was_accepted=true - Filter accepted matches."""
        response = api_client.get(f'{base_url}?was_accepted=true')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for match in results:
            assert match['was_accepted'] is True

    def test_list_order_by_confidence(self, api_client, base_url):
        """Test GET /match-results/?ordering=-confidence_score - Order by confidence."""
        response = api_client.get(f'{base_url}?ordering=-confidence_score')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        if len(results) > 1:
            scores = [r['confidence_score'] for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_accept_match_result(self, api_client, base_url, match_result_fixture):
        """Test POST /match-results/{id}/accept/ - Accept a match."""
        url = f'{base_url}{match_result_fixture.id}/accept/'

        response = api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['was_accepted'] is True

    def test_accept_match_updates_rule_statistics(self, api_client, base_url, tenant_fixture, bank_transaction_fixture, journal_entry_fixture, auto_match_rule_fixture):
        """Test that accepting a match updates the rule's statistics."""
        # Create match result with rule
        create_response = api_client.post(base_url, {
            'tenant': str(tenant_fixture.id),
            'bank_transaction': str(bank_transaction_fixture.id),
            'matched_entry': str(journal_entry_fixture.id),
            'confidence_score': 90,
            'match_explanation': 'Auto-matched',
            'matched_by_rule': str(auto_match_rule_fixture.id),
            'was_accepted': False
        }, format='json')

        match_id = create_response.data['id']

        # Get initial rule statistics
        rule_url = f'/api/v1/accounting/auto-match-rules/{auto_match_rule_fixture.id}/'
        initial_rule = api_client.get(rule_url).data
        initial_times_used = initial_rule['times_used']
        initial_times_correct = initial_rule['times_correct']

        # Accept the match
        accept_url = f'{base_url}{match_id}/accept/'
        api_client.post(accept_url, {}, format='json')

        # Verify rule statistics updated
        updated_rule = api_client.get(rule_url).data
        assert updated_rule['times_used'] == initial_times_used + 1
        assert updated_rule['times_correct'] == initial_times_correct + 1
        # Accuracy rate should be recalculated

    def test_update_match_result(self, api_client, base_url, match_result_fixture):
        """Test PATCH /match-results/{id}/ - Update match result."""
        url = f'{base_url}{match_result_fixture.id}/'
        data = {
            'match_explanation': 'Updated explanation'
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['match_explanation'] == 'Updated explanation'

    def test_delete_match_result(self, api_client, base_url, match_result_fixture):
        """Test DELETE /match-results/{id}/ - Delete match result."""
        url = f'{base_url}{match_result_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_pagination(self, api_client, base_url):
        """Test GET /match-results/?page=1&page_size=10 - Pagination."""
        response = api_client.get(f'{base_url}?page=1&page_size=10')

        assert response.status_code == status.HTTP_200_OK
        if 'results' in response.data:
            assert 'count' in response.data
            assert 'next' in response.data
            assert 'previous' in response.data


# ===========================
# Match Statistics API Tests
# ===========================

class TestMatchStatisticsAPI:
    """Test /api/v1/accounting/match-statistics/ endpoints (Read-only)."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    @pytest.fixture
    def base_url(self):
        return '/api/v1/accounting/match-statistics/'

    def test_create_match_statistics_not_allowed(self, api_client, base_url):
        """Test POST /match-statistics/ - Should not be allowed (read-only)."""
        data = {
            'period_start': str(date.today() - timedelta(days=30)),
            'period_end': str(date.today()),
            'total_transactions': 100
        }

        response = api_client.post(base_url, data, format='json')

        # Should be 405 Method Not Allowed for read-only viewset
        assert response.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN]

    def test_get_match_statistics(self, api_client, base_url, match_statistics_fixture):
        """Test GET /match-statistics/{id}/ - Retrieve statistics."""
        url = f'{base_url}{match_statistics_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(match_statistics_fixture.id)
        assert 'total_transactions' in response.data
        assert 'auto_matched' in response.data
        assert 'manually_matched' in response.data
        assert 'unmatched' in response.data
        assert 'auto_match_rate' in response.data
        assert 'average_confidence' in response.data
        assert 'false_positive_rate' in response.data

    def test_list_match_statistics(self, api_client, base_url):
        """Test GET /match-statistics/ - List all statistics."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_by_period(self, api_client, base_url):
        """Test GET /match-statistics/?period_start=2025-01-01 - Filter by period."""
        period_start = '2025-01-01'
        response = api_client.get(f'{base_url}?period_start={period_start}')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for stat in results:
            assert stat['period_start'] >= period_start

    def test_list_order_by_auto_match_rate(self, api_client, base_url):
        """Test GET /match-statistics/?ordering=-auto_match_rate - Order by rate."""
        response = api_client.get(f'{base_url}?ordering=-auto_match_rate')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        if len(results) > 1:
            rates = [Decimal(r['auto_match_rate']) for r in results]
            assert rates == sorted(rates, reverse=True)

    def test_list_order_by_period_start(self, api_client, base_url):
        """Test GET /match-statistics/?ordering=-period_start - Order by date."""
        response = api_client.get(f'{base_url}?ordering=-period_start')

        assert response.status_code == status.HTTP_200_OK

    def test_update_match_statistics_not_allowed(self, api_client, base_url, match_statistics_fixture):
        """Test PATCH /match-statistics/{id}/ - Should not be allowed."""
        url = f'{base_url}{match_statistics_fixture.id}/'
        data = {'total_transactions': 999}

        response = api_client.patch(url, data, format='json')

        # Should be 405 Method Not Allowed for read-only viewset
        assert response.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN]

    def test_delete_match_statistics_not_allowed(self, api_client, base_url, match_statistics_fixture):
        """Test DELETE /match-statistics/{id}/ - Should not be allowed."""
        url = f'{base_url}{match_statistics_fixture.id}/'

        response = api_client.delete(url)

        # Should be 405 Method Not Allowed for read-only viewset
        assert response.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN]

    def test_statistics_calculation_accuracy(self, api_client, base_url, match_statistics_fixture):
        """Test that statistics calculations are accurate."""
        url = f'{base_url}{match_statistics_fixture.id}/'
        response = api_client.get(url)

        stats = response.data
        total = stats['total_transactions']
        auto = stats['auto_matched']
        manual = stats['manually_matched']
        unmatched = stats['unmatched']

        # Total should equal sum of auto + manual + unmatched
        assert total == auto + manual + unmatched

        # Auto match rate should be correct
        if total > 0:
            expected_rate = Decimal(auto) / Decimal(total) * 100
            assert abs(Decimal(stats['auto_match_rate']) - expected_rate) < Decimal('0.01')

    def test_tenant_isolation_match_statistics(self, api_client, base_url, tenant_fixture):
        """Test tenant isolation for match statistics."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        # TODO: Verify tenant isolation when auth is implemented


# ===========================
# Integration Tests
# ===========================

class TestMatchingWorkflow:
    """Test complete matching workflow integration."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    def test_complete_matching_workflow(self, api_client, tenant_fixture, bank_transaction_fixture, journal_entry_fixture):
        """Test complete workflow: create rule -> create match -> accept match -> verify statistics."""

        # Step 1: Create auto-match rule
        rule_response = api_client.post('/api/v1/accounting/auto-match-rules/', {
            'tenant': str(tenant_fixture.id),
            'rule_type': 'amount',
            'pattern': {'tolerance': 0.01},
            'confidence_score': 90,
            'is_active': True
        }, format='json')

        assert rule_response.status_code == status.HTTP_201_CREATED
        rule_id = rule_response.data['id']

        # Step 2: Create match result using the rule
        match_response = api_client.post('/api/v1/accounting/match-results/', {
            'tenant': str(tenant_fixture.id),
            'bank_transaction': str(bank_transaction_fixture.id),
            'matched_entry': str(journal_entry_fixture.id),
            'confidence_score': 90,
            'match_explanation': 'Amount match',
            'matched_by_rule': rule_id,
            'was_accepted': False
        }, format='json')

        assert match_response.status_code == status.HTTP_201_CREATED
        match_id = match_response.data['id']

        # Step 3: Accept the match
        accept_response = api_client.post(f'/api/v1/accounting/match-results/{match_id}/accept/', {}, format='json')

        assert accept_response.status_code == status.HTTP_200_OK
        assert accept_response.data['was_accepted'] is True

        # Step 4: Verify rule statistics updated
        rule_check = api_client.get(f'/api/v1/accounting/auto-match-rules/{rule_id}/')
        assert rule_check.data['times_used'] == 1
        assert rule_check.data['times_correct'] == 1
        assert Decimal(rule_check.data['accuracy_rate']) == Decimal('100.00')

    def test_rejected_match_workflow(self, api_client, tenant_fixture, bank_transaction_fixture, journal_entry_fixture):
        """Test workflow where match is NOT accepted (rule accuracy should not improve)."""

        # Create rule
        rule_response = api_client.post('/api/v1/accounting/auto-match-rules/', {
            'tenant': str(tenant_fixture.id),
            'rule_type': 'description',
            'pattern': {'keywords': ['TEST']},
            'confidence_score': 70,
            'is_active': True
        }, format='json')

        rule_id = rule_response.data['id']

        # Create match but don't accept it
        match_response = api_client.post('/api/v1/accounting/match-results/', {
            'tenant': str(tenant_fixture.id),
            'bank_transaction': str(bank_transaction_fixture.id),
            'matched_entry': str(journal_entry_fixture.id),
            'confidence_score': 70,
            'match_explanation': 'Description match',
            'matched_by_rule': rule_id,
            'was_accepted': False
        }, format='json')

        assert match_response.status_code == status.HTTP_201_CREATED

        # Rule statistics should not change (match not accepted)
        rule_check = api_client.get(f'/api/v1/accounting/auto-match-rules/{rule_id}/')
        assert rule_check.data['times_used'] == 0
        assert rule_check.data['times_correct'] == 0
