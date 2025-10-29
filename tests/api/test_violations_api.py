"""
API Endpoint Tests for Sprint 19: Violation Tracking

Tests all REST API endpoints for:
- Violations (CRUD + summary statistics)
- Violation Photos (CRUD + photo evidence)
- Violation Notices (CRUD + notice workflow)
- Violation Hearings (CRUD + hearing management)

Testing patterns:
- Authentication and tenant isolation
- All CRUD operations
- Query parameters and filtering
- Pagination
- Validation errors (400)
- Not found errors (404)
- Custom actions (summary endpoint)
- Photo upload handling
- Hearing outcome tracking
"""

import pytest
from decimal import Decimal
from datetime import date, time, timedelta
from rest_framework import status
from rest_framework.test import APIClient


# ===========================
# Violations API Tests
# ===========================

class TestViolationsAPI:
    """Test /api/v1/accounting/violations/ endpoints."""

    @pytest.fixture
    def api_client(self):
        """Create an authenticated API client."""
        client = APIClient()
        # TODO: Add authentication when implemented
        return client

    @pytest.fixture
    def base_url(self):
        """Base URL for violations endpoints."""
        return '/api/v1/accounting/violations/'

    def test_create_violation_minor(self, api_client, base_url, tenant_fixture, owner_fixture):
        """Test POST /violations/ - Create minor violation."""
        data = {
            'tenant': str(tenant_fixture.id),
            'owner': str(owner_fixture.id),
            'violation_type': 'Landscaping',
            'severity': 'minor',
            'status': 'reported',
            'reported_date': str(date.today()),
            'description': 'Overgrown shrubs on front lawn',
            'fine_amount': '0.00',
            'is_paid': False
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['violation_type'] == 'Landscaping'
        assert response.data['severity'] == 'minor'
        assert response.data['status'] == 'reported'
        assert 'owner_name' in response.data
        assert 'severity_display' in response.data
        assert 'id' in response.data

    def test_create_violation_major_with_fine(self, api_client, base_url, tenant_fixture, owner_fixture):
        """Test POST /violations/ - Create major violation with fine."""
        data = {
            'tenant': str(tenant_fixture.id),
            'owner': str(owner_fixture.id),
            'violation_type': 'Unauthorized Construction',
            'severity': 'major',
            'status': 'notice_sent',
            'reported_date': str(date.today() - timedelta(days=7)),
            'first_notice_date': str(date.today() - timedelta(days=5)),
            'description': 'Deck built without architectural approval',
            'fine_amount': '500.00',
            'is_paid': False
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['severity'] == 'major'
        assert Decimal(response.data['fine_amount']) == Decimal('500.00')
        assert response.data['is_paid'] is False

    def test_create_violation_critical(self, api_client, base_url, tenant_fixture, owner_fixture):
        """Test POST /violations/ - Create critical violation."""
        data = {
            'tenant': str(tenant_fixture.id),
            'owner': str(owner_fixture.id),
            'violation_type': 'Safety Hazard',
            'severity': 'critical',
            'status': 'hearing_scheduled',
            'reported_date': str(date.today() - timedelta(days=14)),
            'first_notice_date': str(date.today() - timedelta(days=10)),
            'description': 'Dangerous structural issue threatening neighboring properties',
            'fine_amount': '1000.00',
            'is_paid': False
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['severity'] == 'critical'
        assert Decimal(response.data['fine_amount']) == Decimal('1000.00')

    def test_create_violation_validation_error(self, api_client, base_url):
        """Test POST /violations/ - Missing required fields."""
        data = {
            'violation_type': 'Parking'
            # Missing tenant, owner, severity, status, reported_date
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_violation(self, api_client, base_url, violation_fixture):
        """Test GET /violations/{id}/ - Retrieve single violation."""
        url = f'{base_url}{violation_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(violation_fixture.id)
        assert 'owner_name' in response.data
        assert 'property_address' in response.data
        assert 'photos' in response.data
        assert 'notices' in response.data
        assert 'hearings' in response.data

    def test_get_violation_not_found(self, api_client, base_url):
        """Test GET /violations/{id}/ - Violation not found."""
        from uuid import uuid4
        url = f'{base_url}{uuid4()}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_violations(self, api_client, base_url):
        """Test GET /violations/ - List all violations."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_by_owner(self, api_client, base_url, owner_fixture):
        """Test GET /violations/?owner={id} - Filter by owner."""
        response = api_client.get(f'{base_url}?owner={owner_fixture.id}')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for violation in results:
            assert violation['owner'] == str(owner_fixture.id)

    def test_list_filter_by_violation_type(self, api_client, base_url):
        """Test GET /violations/?violation_type=Parking - Filter by type."""
        response = api_client.get(f'{base_url}?violation_type=Parking')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for violation in results:
            assert violation['violation_type'] == 'Parking'

    def test_list_filter_by_severity(self, api_client, base_url):
        """Test GET /violations/?severity=major - Filter by severity."""
        response = api_client.get(f'{base_url}?severity=major')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for violation in results:
            assert violation['severity'] == 'major'

    def test_list_filter_by_status(self, api_client, base_url):
        """Test GET /violations/?status=open - Filter by status."""
        response = api_client.get(f'{base_url}?status=reported')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for violation in results:
            assert violation['status'] == 'reported'

    def test_list_filter_unpaid_fines(self, api_client, base_url):
        """Test GET /violations/?is_paid=false - Filter unpaid fines."""
        response = api_client.get(f'{base_url}?is_paid=false')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for violation in results:
            assert violation['is_paid'] is False

    def test_update_violation(self, api_client, base_url, violation_fixture):
        """Test PATCH /violations/{id}/ - Update violation."""
        url = f'{base_url}{violation_fixture.id}/'
        data = {
            'status': 'resolved',
            'compliance_date': str(date.today()),
            'resolution_notes': 'Owner corrected the issue'
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'resolved'
        assert response.data['compliance_date'] == str(date.today())

    def test_update_violation_mark_paid(self, api_client, base_url, violation_fixture):
        """Test PATCH /violations/{id}/ - Mark fine as paid."""
        url = f'{base_url}{violation_fixture.id}/'
        data = {
            'is_paid': True
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_paid'] is True

    def test_delete_violation(self, api_client, base_url, violation_fixture):
        """Test DELETE /violations/{id}/ - Delete violation."""
        url = f'{base_url}{violation_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deletion
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_violation_summary_endpoint(self, api_client, base_url):
        """Test GET /violations/summary/ - Get summary statistics."""
        url = f'{base_url}summary/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'total_violations' in response.data
        assert 'open_violations' in response.data
        assert 'total_fines' in response.data
        assert 'unpaid_fines' in response.data
        assert 'by_severity' in response.data

        # Verify severity breakdown
        by_severity = response.data['by_severity']
        assert 'minor' in by_severity
        assert 'major' in by_severity
        assert 'critical' in by_severity

    def test_ordering_by_reported_date(self, api_client, base_url):
        """Test GET /violations/?ordering=-reported_date - Order by date."""
        response = api_client.get(f'{base_url}?ordering=-reported_date')

        assert response.status_code == status.HTTP_200_OK

    def test_ordering_by_fine_amount(self, api_client, base_url):
        """Test GET /violations/?ordering=-fine_amount - Order by fine."""
        response = api_client.get(f'{base_url}?ordering=-fine_amount')

        assert response.status_code == status.HTTP_200_OK

    def test_tenant_isolation_violations(self, api_client, base_url, tenant_fixture, other_tenant_fixture, owner_fixture, other_owner_fixture):
        """Test that tenant A cannot access tenant B's violations."""
        # Create violation for tenant A
        api_client.post(base_url, {
            'tenant': str(tenant_fixture.id),
            'owner': str(owner_fixture.id),
            'violation_type': 'Tenant A Violation',
            'severity': 'minor',
            'status': 'reported',
            'reported_date': str(date.today()),
            'description': 'Test',
            'fine_amount': '0.00',
            'is_paid': False
        }, format='json')

        # Create violation for tenant B
        api_client.post(base_url, {
            'tenant': str(other_tenant_fixture.id),
            'owner': str(other_owner_fixture.id),
            'violation_type': 'Tenant B Violation',
            'severity': 'minor',
            'status': 'reported',
            'reported_date': str(date.today()),
            'description': 'Test',
            'fine_amount': '0.00',
            'is_paid': False
        }, format='json')

        # List violations (should only see tenant A's violations when authenticated as tenant A)
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        # TODO: Verify tenant isolation when auth is implemented


# ===========================
# Violation Photos API Tests
# ===========================

class TestViolationPhotosAPI:
    """Test /api/v1/accounting/violation-photos/ endpoints."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    @pytest.fixture
    def base_url(self):
        return '/api/v1/accounting/violation-photos/'

    def test_create_violation_photo(self, api_client, base_url, violation_fixture):
        """Test POST /violation-photos/ - Add photo to violation."""
        data = {
            'violation': str(violation_fixture.id),
            'photo_url': 'https://example.com/photos/violation-001.jpg',
            'caption': 'Front view of landscaping violation',
            'taken_date': str(date.today())
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['violation'] == str(violation_fixture.id)
        assert response.data['caption'] == 'Front view of landscaping violation'
        assert 'uploaded_at' in response.data
        assert 'id' in response.data

    def test_create_violation_photo_multiple(self, api_client, base_url, violation_fixture):
        """Test POST /violation-photos/ - Add multiple photos."""
        captions = ['Front view', 'Side view', 'Close-up']
        photo_ids = []

        for caption in captions:
            response = api_client.post(base_url, {
                'violation': str(violation_fixture.id),
                'photo_url': f'https://example.com/photos/{caption.replace(" ", "-")}.jpg',
                'caption': caption,
                'taken_date': str(date.today())
            }, format='json')

            assert response.status_code == status.HTTP_201_CREATED
            photo_ids.append(response.data['id'])

        # Verify all photos created
        assert len(photo_ids) == 3

    def test_get_violation_photo(self, api_client, base_url, violation_photo_fixture):
        """Test GET /violation-photos/{id}/ - Retrieve photo."""
        url = f'{base_url}{violation_photo_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(violation_photo_fixture.id)

    def test_list_violation_photos(self, api_client, base_url):
        """Test GET /violation-photos/ - List all photos."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_by_violation(self, api_client, base_url, violation_fixture):
        """Test GET /violation-photos/?violation={id} - Filter by violation."""
        response = api_client.get(f'{base_url}?violation={violation_fixture.id}')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for photo in results:
            assert photo['violation'] == str(violation_fixture.id)

    def test_update_violation_photo(self, api_client, base_url, violation_photo_fixture):
        """Test PATCH /violation-photos/{id}/ - Update photo caption."""
        url = f'{base_url}{violation_photo_fixture.id}/'
        data = {
            'caption': 'Updated caption with more details'
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['caption'] == 'Updated caption with more details'

    def test_delete_violation_photo(self, api_client, base_url, violation_photo_fixture):
        """Test DELETE /violation-photos/{id}/ - Delete photo."""
        url = f'{base_url}{violation_photo_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_ordering_by_taken_date(self, api_client, base_url):
        """Test GET /violation-photos/?ordering=-taken_date - Order by date."""
        response = api_client.get(f'{base_url}?ordering=-taken_date')

        assert response.status_code == status.HTTP_200_OK


# ===========================
# Violation Notices API Tests
# ===========================

class TestViolationNoticesAPI:
    """Test /api/v1/accounting/violation-notices/ endpoints."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    @pytest.fixture
    def base_url(self):
        return '/api/v1/accounting/violation-notices/'

    def test_create_violation_notice_initial(self, api_client, base_url, violation_fixture):
        """Test POST /violation-notices/ - Create initial notice."""
        data = {
            'violation': str(violation_fixture.id),
            'notice_type': 'initial',
            'delivery_method': 'email',
            'sent_date': str(date.today()),
            'cure_deadline': str(date.today() + timedelta(days=14)),
            'notes': 'Initial courtesy notice'
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['notice_type'] == 'initial'
        assert response.data['delivery_method'] == 'email'
        assert 'notice_type_display' in response.data
        assert 'method_display' in response.data
        assert 'id' in response.data

    def test_create_violation_notice_warning(self, api_client, base_url, violation_fixture):
        """Test POST /violation-notices/ - Create warning notice."""
        data = {
            'violation': str(violation_fixture.id),
            'notice_type': 'warning',
            'delivery_method': 'certified_mail',
            'sent_date': str(date.today()),
            'cure_deadline': str(date.today() + timedelta(days=7)),
            'tracking_number': '9876543210',
            'notes': 'Final warning before hearing'
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['notice_type'] == 'warning'
        assert response.data['delivery_method'] == 'certified_mail'
        assert response.data['tracking_number'] == '9876543210'

    def test_create_violation_notice_hearing(self, api_client, base_url, violation_fixture):
        """Test POST /violation-notices/ - Create hearing notice."""
        data = {
            'violation': str(violation_fixture.id),
            'notice_type': 'hearing',
            'delivery_method': 'certified_mail',
            'sent_date': str(date.today()),
            'tracking_number': '1234567890',
            'notes': 'Hearing scheduled for violation'
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['notice_type'] == 'hearing'

    def test_get_violation_notice(self, api_client, base_url, violation_notice_fixture):
        """Test GET /violation-notices/{id}/ - Retrieve notice."""
        url = f'{base_url}{violation_notice_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(violation_notice_fixture.id)

    def test_list_violation_notices(self, api_client, base_url):
        """Test GET /violation-notices/ - List all notices."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_by_violation(self, api_client, base_url, violation_fixture):
        """Test GET /violation-notices/?violation={id} - Filter by violation."""
        response = api_client.get(f'{base_url}?violation={violation_fixture.id}')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for notice in results:
            assert notice['violation'] == str(violation_fixture.id)

    def test_list_filter_by_notice_type(self, api_client, base_url):
        """Test GET /violation-notices/?notice_type=warning - Filter by type."""
        response = api_client.get(f'{base_url}?notice_type=warning')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for notice in results:
            assert notice['notice_type'] == 'warning'

    def test_update_violation_notice_delivered(self, api_client, base_url, violation_notice_fixture):
        """Test PATCH /violation-notices/{id}/ - Mark as delivered."""
        url = f'{base_url}{violation_notice_fixture.id}/'
        data = {
            'delivered_date': str(date.today())
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['delivered_date'] == str(date.today())

    def test_delete_violation_notice(self, api_client, base_url, violation_notice_fixture):
        """Test DELETE /violation-notices/{id}/ - Delete notice."""
        url = f'{base_url}{violation_notice_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_ordering_by_sent_date(self, api_client, base_url):
        """Test GET /violation-notices/?ordering=-sent_date - Order by date."""
        response = api_client.get(f'{base_url}?ordering=-sent_date')

        assert response.status_code == status.HTTP_200_OK


# ===========================
# Violation Hearings API Tests
# ===========================

class TestViolationHearingsAPI:
    """Test /api/v1/accounting/violation-hearings/ endpoints."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    @pytest.fixture
    def base_url(self):
        return '/api/v1/accounting/violation-hearings/'

    def test_create_violation_hearing(self, api_client, base_url, violation_fixture):
        """Test POST /violation-hearings/ - Schedule hearing."""
        data = {
            'violation': str(violation_fixture.id),
            'scheduled_date': str(date.today() + timedelta(days=14)),
            'scheduled_time': '18:00:00',
            'location': 'HOA Community Center',
            'attendees': 'Board members, property manager, homeowner'
        }

        response = api_client.post(base_url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['violation'] == str(violation_fixture.id)
        assert response.data['scheduled_time'] == '18:00:00'
        assert response.data['location'] == 'HOA Community Center'
        assert 'id' in response.data

    def test_get_violation_hearing(self, api_client, base_url, violation_hearing_fixture):
        """Test GET /violation-hearings/{id}/ - Retrieve hearing."""
        url = f'{base_url}{violation_hearing_fixture.id}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(violation_hearing_fixture.id)
        assert 'outcome_display' in response.data

    def test_list_violation_hearings(self, api_client, base_url):
        """Test GET /violation-hearings/ - List all hearings."""
        response = api_client.get(base_url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_filter_by_violation(self, api_client, base_url, violation_fixture):
        """Test GET /violation-hearings/?violation={id} - Filter by violation."""
        response = api_client.get(f'{base_url}?violation={violation_fixture.id}')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for hearing in results:
            assert hearing['violation'] == str(violation_fixture.id)

    def test_list_filter_by_outcome(self, api_client, base_url):
        """Test GET /violation-hearings/?outcome=upheld - Filter by outcome."""
        response = api_client.get(f'{base_url}?outcome=upheld')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        for hearing in results:
            assert hearing['outcome'] == 'upheld'

    def test_update_violation_hearing_outcome_upheld(self, api_client, base_url, violation_hearing_fixture):
        """Test PATCH /violation-hearings/{id}/ - Record upheld outcome."""
        url = f'{base_url}{violation_hearing_fixture.id}/'
        data = {
            'outcome': 'upheld',
            'fine_assessed': '500.00',
            'compliance_deadline': str(date.today() + timedelta(days=30)),
            'hearing_notes': 'Board voted 5-0 to uphold violation and fine'
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['outcome'] == 'upheld'
        assert Decimal(response.data['fine_assessed']) == Decimal('500.00')

    def test_update_violation_hearing_outcome_dismissed(self, api_client, base_url, violation_hearing_fixture):
        """Test PATCH /violation-hearings/{id}/ - Record dismissed outcome."""
        url = f'{base_url}{violation_hearing_fixture.id}/'
        data = {
            'outcome': 'dismissed',
            'fine_assessed': '0.00',
            'hearing_notes': 'Violation dismissed - owner provided evidence of approval'
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['outcome'] == 'dismissed'
        assert Decimal(response.data['fine_assessed']) == Decimal('0.00')

    def test_update_violation_hearing_outcome_reduced(self, api_client, base_url, violation_hearing_fixture):
        """Test PATCH /violation-hearings/{id}/ - Record reduced fine outcome."""
        url = f'{base_url}{violation_hearing_fixture.id}/'
        data = {
            'outcome': 'reduced',
            'fine_assessed': '250.00',
            'compliance_deadline': str(date.today() + timedelta(days=21)),
            'hearing_notes': 'Fine reduced due to owner cooperation'
        }

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['outcome'] == 'reduced'
        assert Decimal(response.data['fine_assessed']) == Decimal('250.00')

    def test_delete_violation_hearing(self, api_client, base_url, violation_hearing_fixture):
        """Test DELETE /violation-hearings/{id}/ - Delete hearing."""
        url = f'{base_url}{violation_hearing_fixture.id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_ordering_by_scheduled_date(self, api_client, base_url):
        """Test GET /violation-hearings/?ordering=-scheduled_date - Order by date."""
        response = api_client.get(f'{base_url}?ordering=-scheduled_date')

        assert response.status_code == status.HTTP_200_OK

    def test_pagination(self, api_client, base_url):
        """Test GET /violation-hearings/?page=1&page_size=10 - Pagination."""
        response = api_client.get(f'{base_url}?page=1&page_size=10')

        assert response.status_code == status.HTTP_200_OK
        if 'results' in response.data:
            assert 'count' in response.data
            assert 'next' in response.data
            assert 'previous' in response.data


# ===========================
# Integration Tests
# ===========================

class TestViolationWorkflow:
    """Test complete violation workflow integration."""

    @pytest.fixture
    def api_client(self):
        client = APIClient()
        return client

    def test_complete_violation_workflow(self, api_client, tenant_fixture, owner_fixture):
        """Test complete workflow: report violation -> add photos -> send notices -> schedule hearing -> resolve."""

        # Step 1: Report violation
        violation_response = api_client.post('/api/v1/accounting/violations/', {
            'tenant': str(tenant_fixture.id),
            'owner': str(owner_fixture.id),
            'violation_type': 'Unauthorized Modification',
            'severity': 'major',
            'status': 'reported',
            'reported_date': str(date.today()),
            'description': 'Fence installed without approval',
            'fine_amount': '0.00',
            'is_paid': False
        }, format='json')

        assert violation_response.status_code == status.HTTP_201_CREATED
        violation_id = violation_response.data['id']

        # Step 2: Add photos
        photo_response = api_client.post('/api/v1/accounting/violation-photos/', {
            'violation': violation_id,
            'photo_url': 'https://example.com/photos/fence.jpg',
            'caption': 'Unauthorized fence installation',
            'taken_date': str(date.today())
        }, format='json')

        assert photo_response.status_code == status.HTTP_201_CREATED

        # Step 3: Send initial notice
        notice_response = api_client.post('/api/v1/accounting/violation-notices/', {
            'violation': violation_id,
            'notice_type': 'initial',
            'delivery_method': 'email',
            'sent_date': str(date.today()),
            'cure_deadline': str(date.today() + timedelta(days=14))
        }, format='json')

        assert notice_response.status_code == status.HTTP_201_CREATED

        # Step 4: Update violation status
        api_client.patch(f'/api/v1/accounting/violations/{violation_id}/', {
            'status': 'notice_sent',
            'first_notice_date': str(date.today())
        }, format='json')

        # Step 5: Schedule hearing
        hearing_response = api_client.post('/api/v1/accounting/violation-hearings/', {
            'violation': violation_id,
            'scheduled_date': str(date.today() + timedelta(days=21)),
            'scheduled_time': '18:00:00',
            'location': 'HOA Community Center'
        }, format='json')

        assert hearing_response.status_code == status.HTTP_201_CREATED
        hearing_id = hearing_response.data['id']

        # Step 6: Record hearing outcome
        api_client.patch(f'/api/v1/accounting/violation-hearings/{hearing_id}/', {
            'outcome': 'upheld',
            'fine_assessed': '500.00',
            'compliance_deadline': str(date.today() + timedelta(days=30))
        }, format='json')

        # Step 7: Resolve violation
        resolve_response = api_client.patch(f'/api/v1/accounting/violations/{violation_id}/', {
            'status': 'resolved',
            'compliance_date': str(date.today() + timedelta(days=28)),
            'fine_amount': '500.00',
            'is_paid': True,
            'resolution_notes': 'Owner removed fence and paid fine'
        }, format='json')

        assert resolve_response.status_code == status.HTTP_200_OK
        assert resolve_response.data['status'] == 'resolved'
        assert resolve_response.data['is_paid'] is True
